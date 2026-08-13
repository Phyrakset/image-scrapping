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
    """Generate and download images using AI (Gemini Imagen or OpenAI DALL-E)."""

    def __init__(self, provider: str = "gemini", api_key: str = "", delay: int = 3):
        """
        Args:
            provider: "gemini" or "openai"
            api_key: API key for the selected provider
            delay: Seconds to wait between generation requests
        """
        super().__init__()
        self.provider = provider.lower()
        self.api_key = api_key
        self.delay = delay

    @property
    def source_name(self) -> str:
        return f"AI ({self.provider.capitalize()})"

    def scrape(self, query: str, output_dir: str, num_images: int) -> list[str]:
        """
        Generate images for the given position query using AI.
        """
        if self.is_stopped():
            return []

        if not self.api_key:
            msg = f"No API key provided for {self.provider}"
            logger.error(f"[AI] {msg}")
            self._progress["message"] = f"[AI] Error: {msg}"
            raise RuntimeError(msg)

        if self.provider == "gemini":
            return self._generate_gemini(query, output_dir, num_images)
        elif self.provider == "openai":
            return self._generate_openai(query, output_dir, num_images)
        else:
            raise ValueError(f"Unknown AI provider: {self.provider}")

    def _generate_gemini(self, query: str, output_dir: str, num_images: int) -> list[str]:
        """Generate images using Google Gemini."""
        downloaded_files = []

        try:
            from google import genai
            from google.genai import types

            logger.info(f"[AI/Gemini] Generating images for '{query}' — target: {num_images}")
            self._progress["message"] = f"[AI/Gemini] Generating images for: {query}"

            client = genai.Client(api_key=self.api_key)

            for idx in range(num_images):
                if self.is_stopped():
                    break

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
                            file_name = f"{idx + 1:03d}.png"
                            file_path = os.path.join(output_dir, file_name)

                            image = img_data.image
                            if hasattr(image, "image_bytes"):
                                with open(file_path, "wb") as f:
                                    f.write(image.image_bytes)
                            elif hasattr(image, "data"):
                                with open(file_path, "wb") as f:
                                    f.write(image.data)

                            downloaded_files.append(file_path)
                            logger.info(f"[AI/Gemini] Generated image {idx + 1}: {file_path}")
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

    def _generate_openai(self, query: str, output_dir: str, num_images: int) -> list[str]:
        """Generate images using OpenAI DALL-E."""
        downloaded_files = []

        try:
            from openai import OpenAI

            logger.info(f"[AI/OpenAI] Generating images for '{query}' — target: {num_images}")
            self._progress["message"] = f"[AI/OpenAI] Generating images for: {query}"

            client = OpenAI(api_key=self.api_key)

            for idx in range(num_images):
                if self.is_stopped():
                    break

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

                        file_name = f"{idx + 1:03d}.png"
                        file_path = os.path.join(output_dir, file_name)

                        with open(file_path, "wb") as f:
                            f.write(img_bytes)

                        downloaded_files.append(file_path)
                        logger.info(f"[AI/OpenAI] Generated image {idx + 1}: {file_path}")

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
