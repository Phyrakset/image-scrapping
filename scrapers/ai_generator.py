"""
AI Image Generator using Google Gemini (Imagen) and OpenAI (DALL-E).
"""
import os
import io
import time
import base64
import logging

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class AIImageGenerator(BaseScraper):
    """Generate and download images using AI (Local Stable Diffusion, Gemini Imagen, or OpenAI DALL-E)."""

    def __init__(self, provider: str = "gemini", api_key: str = "", delay: int = 3, local_sd_url: str = "http://127.0.0.1:7860"):
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
            payload = {
                "prompt": f"{prompt}, masterpiece, 8k resolution, photorealistic, cinematic lighting, sharp focus",
                "negative_prompt": "blurry, low quality, deformed, disfigured, distorted face, bad anatomy, bad hands, extra limbs, watermark, text",
                "steps": 25,
                "width": 512,
                "height": 512,
                "cfg_scale": 7.0,
                "sampler_name": "Euler a",
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
        """Create a varied prompt for AI image generation."""
        variations = [
            f"Professional photograph of a {position} at work in their typical workplace, realistic, high quality, candid shot",
            f"A {position} performing their daily tasks, professional environment, natural lighting, editorial photography",
            f"Portrait of a {position} in action at their workplace, professional quality, realistic style",
            f"Documentary-style photo of a {position} working on the job, authentic workplace setting, high resolution",
            f"A skilled {position} in their work environment, showing typical equipment and setting, professional photo",
            f"Real workplace photo of a {position}, showing the job in action, natural and authentic, professional quality",
            f"Candid photo of a {position} during a regular workday, realistic workplace, professional photography",
            f"A {position} demonstrating their craft at work, professional setting, high-quality realistic image",
        ]
        return variations[variation_index % len(variations)]

