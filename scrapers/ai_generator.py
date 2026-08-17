"""
AI Image Generator using Google Gemini (Imagen) and OpenAI (DALL-E).
"""
import os
import io
import time
import base64
import logging
import requests

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class AIImageGenerator(BaseScraper):
    """Generate and download images using AI (Local Stable Diffusion, Gemini Imagen, or OpenAI DALL-E)."""

    def __init__(
        self,
        provider: str = "gemini",
        api_key: str = "",
        delay: int = 3,
        local_sd_url: str = "http://127.0.0.1:7860",
        local_sd_model: str = "realvisxl",
        openrouter_model: str = "google/gemini-2.5-flash-image",
    ):
        self.local_sd_model = local_sd_model
        self.openrouter_model = openrouter_model
        """
        Args:
            provider: "local_sd", "gemini", or "openai"
            api_key: API key for cloud providers
            delay: Seconds to wait between generation requests
            local_sd_url: URL for local Stable Diffusion WebUI API (e.g. http://127.0.0.1:7860)
        """
        super().__init__()
        self.provider = provider.lower()
        self.api_key = api_key
        self.delay = delay
        self.local_sd_url = local_sd_url.rstrip("/")

    @property
    def source_name(self) -> str:
        if self.provider in ("local_sd", "local", "stable_diffusion"):
            return "Local Stable Diffusion"
        return f"AI ({self.provider.capitalize()})"

    def scrape(
        self,
        query: str,
        output_dir: str,
        num_images: int,
        start_offset: int = 0,
        only_ai_person: bool = False,
        detector=None,
    ) -> list[str]:
        """
        Generate images for the given position query using AI.
        """
        if self.is_stopped():
            return []

        if self.provider in ("local_sd", "local", "stable_diffusion"):
            return self._generate_local_sd(query, output_dir, num_images, start_offset=start_offset)

        if not self.api_key:
            msg = f"No API key provided for {self.provider}"
            logger.error(f"[AI] {msg}")
            self._progress["message"] = f"[AI] Error: {msg}"
            raise RuntimeError(msg)

        if self.provider == "gemini":
            return self._generate_gemini(query, output_dir, num_images, start_offset=start_offset)
        elif self.provider == "openai":
            return self._generate_openai(query, output_dir, num_images, start_offset=start_offset)
        elif self.provider == "openrouter":
            return self._generate_openrouter(query, output_dir, num_images, start_offset=start_offset)
        else:
            raise ValueError(f"Unknown AI provider: {self.provider}")


    def _generate_gemini(self, query: str, output_dir: str, num_images: int, start_offset: int = 0) -> list[str]:
        """Generate images using Google Gemini."""
        downloaded_files = []

        try:
            from google import genai
            from google.genai import types

            logger.info(f"[AI/Gemini] Generating images for '{query}' — target: {num_images} (offset {start_offset})")
            self._progress["message"] = f"[AI/Gemini] Generating images for: {query}"

            client = genai.Client(api_key=self.api_key)

            for idx in range(num_images):
                if self.is_stopped():
                    break

                file_idx = start_offset + idx + 1
                self._progress["current_image"] = idx + 1
                self._progress["message"] = f"[AI/Gemini] Generating {idx + 1}/{num_images}: {query}"

                try:
                    # Create a detailed prompt for the position
                    prompt = self._create_prompt(query, idx)

                    response = client.models.generate_images(
                        model="imagen-3.0-generate-002",
                        prompt=prompt,
                        config=types.GenerateImagesConfig(
                            number_of_images=1,
                            aspect_ratio="1:1",
                            safety_filter_level="BLOCK_MEDIUM_AND_ABOVE",
                        ),
                    )

                    if response.generated_images:
                        for img_data in response.generated_images:
                            file_name = f"{file_idx:03d}.png"
                            file_path = os.path.join(output_dir, file_name)

                            image = img_data.image
                            if hasattr(image, "image_bytes"):
                                with open(file_path, "wb") as f:
                                    f.write(image.image_bytes)
                            elif hasattr(image, "data"):
                                with open(file_path, "wb") as f:
                                    f.write(image.data)

                            downloaded_files.append(file_path)
                            logger.info(f"[AI/Gemini] Generated image {file_idx}: {file_path}")
                    else:
                        logger.warning(f"[AI/Gemini] No image generated for prompt {idx + 1}")

                except Exception as e:
                    logger.error(f"[AI/Gemini] Error generating image {idx + 1}: {e}")
                    self._progress["failed"] += 1
                    continue

                # Rate limiting delay
                if self.delay > 0 and idx < num_images - 1:
                    time.sleep(self.delay)

        except ImportError:
            raise RuntimeError("google-generativeai not installed. Run: pip install google-generativeai")

        logger.info(f"[AI/Gemini] Generated {len(downloaded_files)} images for '{query}'")
        return downloaded_files

    def _generate_openai(self, query: str, output_dir: str, num_images: int, start_offset: int = 0) -> list[str]:
        """Generate images using OpenAI DALL-E."""
        downloaded_files = []

        try:
            from openai import OpenAI

            logger.info(f"[AI/OpenAI] Generating images for '{query}' — target: {num_images} (offset {start_offset})")
            self._progress["message"] = f"[AI/OpenAI] Generating images for: {query}"

            client = OpenAI(api_key=self.api_key)

            for idx in range(num_images):
                if self.is_stopped():
                    break

                file_idx = start_offset + idx + 1
                self._progress["current_image"] = idx + 1
                self._progress["message"] = f"[AI/OpenAI] Generating {idx + 1}/{num_images}: {query}"

                try:
                    prompt = self._create_prompt(query, idx)

                    response = client.images.generate(
                        model="dall-e-3",
                        prompt=prompt,
                        size="1024x1024",
                        quality="standard",
                        n=1,
                        response_format="b64_json",
                    )

                    if response.data:
                        img_b64 = response.data[0].b64_json
                        img_bytes = base64.b64decode(img_b64)

                        file_name = f"{file_idx:03d}.png"
                        file_path = os.path.join(output_dir, file_name)

                        with open(file_path, "wb") as f:
                            f.write(img_bytes)

                        downloaded_files.append(file_path)
                        logger.info(f"[AI/OpenAI] Generated image {file_idx}: {file_path}")

                except Exception as e:
                    logger.error(f"[AI/OpenAI] Error generating image {idx + 1}: {e}")
                    self._progress["failed"] += 1
                    continue

                # Rate limiting delay
                if self.delay > 0 and idx < num_images - 1:
                    time.sleep(self.delay)

        except ImportError:
            raise RuntimeError("openai not installed. Run: pip install openai")

        logger.info(f"[AI/OpenAI] Generated {len(downloaded_files)} images for '{query}'")
        return downloaded_files

    def _generate_openrouter(self, query: str, output_dir: str, num_images: int, start_offset: int = 0) -> list[str]:
        """Generate images using OpenRouter unified multimodal models (Gemini & OpenAI)."""
        downloaded_files = []
        logger.info(f"[AI/OpenRouter] Generating images for '{query}' with model '{self.openrouter_model}' — target: {num_images}")
        self._progress["message"] = f"[AI/OpenRouter] Generating images for: {query}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "TverKar Image Scrapping Platform",
            "Content-Type": "application/json",
        }

        for idx in range(num_images):
            if self.is_stopped():
                break

            file_idx = start_offset + idx + 1
            self._progress["current_image"] = idx + 1
            self._progress["message"] = f"[AI/OpenRouter] Generating {idx + 1}/{num_images}: {query} ({self.openrouter_model})"

            try:
                prompt = self._create_prompt(query, idx)
                payload = {
                    "model": self.openrouter_model,
                    "messages": [
                        {"role": "user", "content": f"Generate a realistic high-resolution photograph: {prompt}"}
                    ],
                }

                resp = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=90)
                if resp.status_code == 200:
                    data = resp.json()
                    choice = data.get("choices", [{}])[0]
                    msg = choice.get("message", {})
                    images = msg.get("images", [])

                    saved = False
                    if images and isinstance(images, list):
                        for img_item in images:
                            if isinstance(img_item, dict):
                                img_url = img_item.get("image_url", {}).get("url", "")
                                if img_url.startswith("data:image"):
                                    b64_data = img_url.split(",", 1)[-1]
                                    img_bytes = base64.b64decode(b64_data)
                                    file_name = f"{file_idx:03d}.png"
                                    file_path = os.path.join(output_dir, file_name)
                                    with open(file_path, "wb") as f:
                                        f.write(img_bytes)
                                    downloaded_files.append(file_path)
                                    logger.info(f"[AI/OpenRouter] Generated image {file_idx}: {file_path}")
                                    saved = True
                                    break
                                elif img_url.startswith("http"):
                                    img_resp = requests.get(img_url, timeout=30)
                                    if img_resp.status_code == 200:
                                        file_name = f"{file_idx:03d}.png"
                                        file_path = os.path.join(output_dir, file_name)
                                        with open(file_path, "wb") as f:
                                            f.write(img_resp.content)
                                        downloaded_files.append(file_path)
                                        logger.info(f"[AI/OpenRouter] Downloaded image {file_idx}: {file_path}")
                                        saved = True
                                        break
                    if not saved:
                        logger.warning(f"[AI/OpenRouter] No image returned in message payload for {query}: {msg.get('content')}")
                        self._progress["failed"] += 1
                else:
                    logger.error(f"[AI/OpenRouter] HTTP {resp.status_code}: {resp.text[:200]}")
                    self._progress["failed"] += 1
            except Exception as e:
                logger.error(f"[AI/OpenRouter] Generation error on {query}: {e}")
                self._progress["failed"] += 1
                continue

            if self.delay > 0 and idx < num_images - 1:
                time.sleep(self.delay)

        logger.info(f"[AI/OpenRouter] Completed generation of {len(downloaded_files)} images for '{query}'")
        return downloaded_files

    def _generate_local_sd(self, query: str, output_dir: str, num_images: int, start_offset: int = 0) -> list[str]:
        """Generate images using Local Stable Diffusion WebUI API (Automatic1111 / Fooocus / ComfyUI)."""
        import requests

        downloaded_files = []
        logger.info(f"[AI/LocalSD] Generating {num_images} images for '{query}' via {self.local_sd_url}")
        self._progress["message"] = f"[AI/LocalSD] Connecting to {self.local_sd_url} for '{query}'..."

        # Test connection
        try:
            test_resp = requests.get(f"{self.local_sd_url}/sdapi/v1/options", timeout=3)
        except Exception as conn_err:
            msg = (
                f"Cannot connect to Local Stable Diffusion on {self.local_sd_url}. "
                "Make sure Stable Diffusion WebUI is running with '--api' enabled (e.g. webui-user.bat --api)."
            )
            logger.error(f"[AI/LocalSD] {msg}")
            self._progress["message"] = f"Error: {msg}"
            raise RuntimeError(msg)

        for idx in range(num_images):
            if self.is_stopped():
                break

            file_idx = start_offset + idx + 1
            self._progress["current_image"] = idx + 1
            self._progress["message"] = f"[AI/LocalSD] Generating {idx + 1}/{num_images}: {query}"

            prompt = self._create_prompt(query, idx)
            negative_prompt = (
                "3d render, cgi, digital art, illustration, cartoon, anime, airbrushed, plastic skin, "
                "smooth skin, porcelain face, doll, dramatic studio lighting, dark moody room, spotlight on face, "
                "glamor portrait, heavy makeup, fake, oversaturated, video game character, watermark, text, "
                "disfigured, bad hands, extra limbs, deformed fingers"
            )
            payload = {
                "model": self.local_sd_model,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "steps": 25,
                "width": 512,
                "height": 512,
                "cfg_scale": 6.5,
                "sampler_name": "DPM++ 2M Karras",
                "batch_size": 1,
                "n_iter": 1,
            }

            try:
                resp = requests.post(f"{self.local_sd_url}/sdapi/v1/txt2img", json=payload, timeout=180)
                if resp.status_code == 200:
                    data = resp.json()
                    images_b64 = data.get("images", [])
                    if images_b64:
                        img_bytes = base64.b64decode(images_b64[0].split(",", 1)[-1])
                        file_name = f"{file_idx:03d}.png"
                        file_path = os.path.join(output_dir, file_name)

                        with open(file_path, "wb") as f:
                            f.write(img_bytes)

                        downloaded_files.append(file_path)
                        logger.info(f"[AI/LocalSD] Generated image {file_idx}: {file_path}")
                    else:
                        logger.warning(f"[AI/LocalSD] No image returned for {query}")
                else:
                    logger.error(f"[AI/LocalSD] HTTP {resp.status_code}: {resp.text[:100]}")
                    self._progress["failed"] += 1
            except Exception as e:
                logger.error(f"[AI/LocalSD] Generation error on {query}: {e}")
                self._progress["failed"] += 1
                continue

            if self.delay > 0 and idx < num_images - 1:
                time.sleep(self.delay)

        logger.info(f"[AI/LocalSD] Completed generation of {len(downloaded_files)} images for '{query}'")
        return downloaded_files

    @staticmethod
    def _create_prompt(position: str, variation_index: int) -> str:
        """Create a varied, ultra-realistic documentary photography prompt for realistic human workers."""
        variations = [
            f"Raw candid documentary photograph of an Asian {position} actively working on tasks in a bright well-lit workplace, holding real work tools, natural posture, authentic work attire, captured on 35mm lens, natural daytime ambient lighting, real human skin texture with subtle pores, unedited photo",
            f"Authentic workplace color photo of a skilled Asian {position} on a regular workday, realistic environment with authentic background equipment, natural window daylight, candid shot, lifelike facial expression, realistic clothing fabric folds",
            f"Candid editorial photo of an Asian {position} performing job duties in an authentic facility, natural ambient light, genuine human skin texture, sharp details, realistic everyday work uniform, documentary photography style",
            f"Realistic documentary action shot of an Asian {position} focused on their craft, real equipment in background, bright natural lighting, authentic skin pores and texture, candid work scene, shot on professional camera",
            f"Authentic on-site photo of an Asian {position} inspecting work progress, natural daytime lighting, realistic workplace setting, candid and natural, unposed documentary photography, true to life colors",
            f"Candid photo of an Asian {position} at their workstation during a normal shift, well-lit room, natural ambient light, genuine work gear, authentic human features and skin texture",
        ]
        return variations[variation_index % len(variations)]

