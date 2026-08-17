"""
Unified High-Quality Local Image Generation API Server.
Supports dynamic on-demand model loading and hot-swapping in GPU memory.
Models: MajicMIX Realistic (Asian), FLUX.1 [schnell] (SOTA 12B), RealVisXL, Juggernaut XL, Realistic Vision v6.0, EpiCRealism.
Compatible with Automatic1111 / WebUI API (/sdapi/v1/txt2img).
"""
import io
import os
import gc
import base64
import argparse
import torch
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from diffusers import (
    AutoPipelineForText2Image,
    StableDiffusionPipeline,
    DPMSolverMultistepScheduler,
)
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Unified Local Image Generation API")

pipe = None
CURRENT_MODEL_KEY = ""
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float16 if torch.cuda.is_available() else torch.float32

# Comprehensive Model Registry
AVAILABLE_MODELS = {
    "majicmix": {
        "name": "🌸 MajicMIX Realistic v7 (Asian Realism Specialist)",
        "id": "digiplay/majicMIX_realistic_v7",
        "type": "sd15",
        "description": "Top specialized model for photorealistic Asian personas, workers, and authentic skin textures.",
        "default_width": 512,
        "default_height": 512,
        "default_steps": 25,
        "cfg": 7.0,
    },
    "flux_schnell": {
        "name": "👑 FLUX.1 [schnell] (12B SOTA — Next-Gen Realism)",
        "id": "black-forest-labs/FLUX.1-schnell",
        "type": "flux",
        "description": "World #1 open-source image model. Flawless hands, lifelike anatomy, and DSLR realism.",
        "default_width": 1024,
        "default_height": 1024,
        "default_steps": 4,
        "cfg": 0.0,
    },
    "realvisxl": {
        "name": "🌟 RealVisXL v4.0 (SDXL 1024x1024)",
        "id": "SG161222/RealVisXL_V4.0",
        "type": "sdxl",
        "description": "Gold standard for photorealistic human portraits and studio lighting.",
        "default_width": 1024,
        "default_height": 1024,
        "default_steps": 25,
        "cfg": 6.5,
    },
    "juggernaut": {
        "name": "🏢 Juggernaut XL v9 (SDXL 1024x1024)",
        "id": "RunDiffusion/Juggernaut-XL-v9",
        "type": "sdxl",
        "description": "Specialist for workplace settings, uniforms, tools, and industrial environments.",
        "default_width": 1024,
        "default_height": 1024,
        "default_steps": 25,
        "cfg": 6.5,
    },
    "realistic_vision": {
        "name": "⚡ Realistic Vision v6.0 (SD 1.5 - Fast 3s)",
        "id": "SG161222/Realistic_Vision_V6.0_B1_noVAE",
        "type": "sd15",
        "description": "High-speed photorealistic portrait generation (2-4 seconds).",
        "default_width": 512,
        "default_height": 512,
        "default_steps": 20,
        "cfg": 7.0,
    },
    "epicrealism": {
        "name": "📷 EpiCRealism (SD 1.5 - Candid)",
        "id": "emilianJR/epiCRealism",
        "type": "sd15",
        "description": "Candid, documentary-style photography with authentic natural lighting.",
        "default_width": 512,
        "default_height": 512,
        "default_steps": 20,
        "cfg": 7.0,
    },
}

class Txt2ImgRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = ""
    steps: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    cfg_scale: Optional[float] = None
    sampler_name: Optional[str] = "DPM++ 2M Karras"
    model: Optional[str] = None
    batch_size: Optional[int] = 1
    n_iter: Optional[int] = 1

class SwitchModelRequest(BaseModel):
    model: str


def load_model(model_key_or_id: str):
    global pipe, CURRENT_MODEL_KEY
    
    key = model_key_or_id.lower().strip()
    config = AVAILABLE_MODELS.get(key)
    
    if config:
        model_id = config["id"]
        model_key = key
    else:
        model_id = model_key_or_id
        model_key = key
        for k, v in AVAILABLE_MODELS.items():
            if v["id"].lower() == model_id.lower():
                model_key = k
                config = v
                break

    if pipe is not None and CURRENT_MODEL_KEY == model_key:
        return  # Already loaded

    print(f"[*] Switching model from '{CURRENT_MODEL_KEY}' to '{model_key}' ({model_id})...")
    
    # 1. Clean previous VRAM
    if pipe is not None:
        del pipe
        pipe = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        gc.collect()

    # 2. Load newly selected model
    model_type = config.get("type", "sdxl") if config else "sdxl"
    
    try:
        if model_type == "flux" or "flux" in model_key:
            from diffusers import FluxPipeline
            flux_dtype = torch.bfloat16 if (torch.cuda.is_available() and torch.cuda.is_bf16_supported()) else torch.float16
            pipe = FluxPipeline.from_pretrained(
                model_id,
                torch_dtype=flux_dtype,
            )
            pipe.enable_model_cpu_offload()
        elif "realistic_vision" in model_key or "Realistic_Vision" in model_id:
            pipe = StableDiffusionPipeline.from_single_file(
                "https://huggingface.co/SG161222/Realistic_Vision_V6.0_B1_noVAE/blob/main/Realistic_Vision_V6.0_NV_B1_fp16.safetensors",
                torch_dtype=DTYPE,
                safety_checker=None,
            )
            pipe.to(DEVICE)
            if DEVICE == "cuda":
                pipe.enable_attention_slicing()
        else:
            pipe = AutoPipelineForText2Image.from_pretrained(
                model_id,
                torch_dtype=DTYPE,
                variant="fp16" if ("xl" in model_key or "xl" in model_id.lower() or "realvis" in model_key) else None,
                use_safetensors=True,
            )
            try:
                pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)
            except Exception:
                pass
            pipe.to(DEVICE)
            if DEVICE == "cuda":
                pipe.enable_attention_slicing()

    except Exception as e:
        print(f"[*] Standard load fallback ({e}). Attempting generic loader...")
        try:
            pipe = StableDiffusionPipeline.from_pretrained(
                model_id,
                torch_dtype=DTYPE,
                safety_checker=None,
            )
            pipe.to(DEVICE)
            if DEVICE == "cuda":
                pipe.enable_attention_slicing()
        except Exception:
            pipe = AutoPipelineForText2Image.from_single_file(
                model_id,
                torch_dtype=DTYPE,
            )
            pipe.to(DEVICE)
            if DEVICE == "cuda":
                pipe.enable_attention_slicing()

    CURRENT_MODEL_KEY = model_key
    print(f"[✓] Model '{model_key}' successfully loaded and ready on {DEVICE}!")


@app.get("/sdapi/v1/models")
async def get_models():
    """Return all available models and current active model."""
    return {
        "current_model": CURRENT_MODEL_KEY,
        "models": AVAILABLE_MODELS
    }


@app.get("/sdapi/v1/options")
async def get_options():
    """Healthcheck endpoint required by scrapers/ai_generator.py"""
    return {
        "sd_model_checkpoint": CURRENT_MODEL_KEY or "majicmix",
        "status": "ready"
    }


@app.post("/sdapi/v1/switch_model")
async def switch_model_endpoint(req: SwitchModelRequest):
    """Switch active model on-demand."""
    load_model(req.model)
    return {"status": "success", "active_model": CURRENT_MODEL_KEY}


@app.post("/sdapi/v1/txt2img")
async def txt2img(req: Txt2ImgRequest):
    """Generate high-quality image with on-demand model selection."""
    target_model = req.model or CURRENT_MODEL_KEY or "majicmix"
    
    if CURRENT_MODEL_KEY != target_model or pipe is None:
        load_model(target_model)

    config = AVAILABLE_MODELS.get(CURRENT_MODEL_KEY, {})
    model_type = config.get("type", "sdxl")
    is_flux = model_type == "flux"
    is_sdxl = model_type == "sdxl"
    
    target_width = req.width or config.get("default_width", 1024 if (is_sdxl or is_flux) else 512)
    target_height = req.height or config.get("default_height", 1024 if (is_sdxl or is_flux) else 512)
    target_steps = req.steps or config.get("default_steps", 4 if is_flux else (25 if is_sdxl else 20))
    target_cfg = req.cfg_scale if req.cfg_scale is not None else config.get("cfg", 0.0 if is_flux else 7.0)

    clean_prompt = req.prompt
    negative = req.negative_prompt or "ugly, deformed, disfigured, poor anatomy, bad hands, cartoon, 3d, anime, airbrushed, plastic skin, bad lighting, watermark"

    print(f"[*] Generating with [{CURRENT_MODEL_KEY}] ({target_width}x{target_height}): '{clean_prompt[:50]}...' (steps={target_steps})")
    
    with torch.inference_mode():
        if is_flux:
            result = pipe(
                prompt=clean_prompt,
                num_inference_steps=target_steps,
                guidance_scale=target_cfg,
                width=target_width,
                height=target_height,
            )
        else:
            result = pipe(
                prompt=clean_prompt,
                negative_prompt=negative,
                num_inference_steps=target_steps,
                guidance_scale=target_cfg,
                width=target_width,
                height=target_height,
            )

    images_b64 = []
    for img in result.images:
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        images_b64.append(img_b64)

    return {"images": images_b64, "model": CURRENT_MODEL_KEY}


if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--default-model", type=str, default="majicmix")
    args = parser.parse_args()

    load_model(args.default_model)
    uvicorn.run(app, host=args.host, port=args.port)
