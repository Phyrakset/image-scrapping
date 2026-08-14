"""
Pinterest image scraper using the pinterest-dl library.
"""
import os
import time
import logging
from typing import List

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class PinterestScraper(BaseScraper):
    """Scrape and download images from Pinterest search results."""

    def __init__(self, delay: float = 0.5):
        super().__init__()
        self.delay = delay

    @property
    def source_name(self) -> str:
        return "Pinterest"

    def scrape(
        self,
        query: str,
        output_dir: str,
        num_images: int,
        start_offset: int = 0,
        only_ai_person: bool = False,
        detector=None,
    ) -> List[str]:
        """
        Search Pinterest for images matching the query and download them into output_dir.
        Optionally filters to only keep AI-generated person images.
        """
        if self.is_stopped():
            return []

        downloaded_files = []
        effective_query = query
        if only_ai_person:
            ai_keywords = ["AI generated", "AI art", "Midjourney", "AI portrait"]
            if not any(kw.lower() in query.lower() for kw in ai_keywords):
                effective_query = f"{query} AI generated person Midjourney"

        try:
            from pinterest_dl import PinterestDL

            logger.info(f"[Pinterest] Searching for '{effective_query}' — target: {num_images} images (offset {start_offset}, only_ai={only_ai_person})")
            self._progress["message"] = f"[Pinterest] Searching: {effective_query}"
            self._progress["total_images"] = num_images
            self._progress["current_image"] = 0

            pdl = PinterestDL.with_api()

            # If filtering, we fetch more candidates to account for rejected real photos
            fetch_count = num_images * 3 if only_ai_person else num_images

            def on_progress(media):
                if self.is_stopped():
                    return
                self._progress["current_image"] = min(self._progress["current_image"] + 1, num_images)
                self._progress["message"] = f"[Pinterest] Downloaded {self._progress['current_image']}/{num_images} for '{query}'"

            # Download using pinterest-dl search_and_download
            pdl.search_and_download(
                query=effective_query,
                output_dir=output_dir,
                num=fetch_count,
                min_resolution=(0, 0),
                delay=self.delay,
                on_progress=on_progress
            )

            # Get downloaded files and standardize/sort
            if os.path.exists(output_dir):
                raw_files = [
                    os.path.join(output_dir, f)
                    for f in os.listdir(output_dir)
                    if os.path.isfile(os.path.join(output_dir, f)) and not f.startswith('.') and not f.startswith('temp_')
                ]
                raw_files.sort(key=lambda f: os.path.getmtime(f))

                valid_files = []
                for fpath in raw_files:
                    if len(valid_files) >= num_images or self.is_stopped():
                        # Remove extra excess candidates if over target
                        if len(valid_files) >= num_images and not fpath.startswith("temp_"):
                            try:
                                os.remove(fpath)
                            except Exception:
                                pass
                        continue

                    # AI Person Filter
                    if only_ai_person and detector:
                        self._progress["message"] = f"[Pinterest AI Filter] Inspecting image {len(valid_files) + 1}/{num_images}..."
                        is_ai, reason = detector.is_ai_person(fpath)
                        if not is_ai:
                            logger.info(f"[Pinterest AI Filter] {reason}")
                            try:
                                os.remove(fpath)
                            except Exception:
                                pass
                            self._progress["filtered"] = self._progress.get("filtered", 0) + 1
                            self._progress["message"] = f"[AI Filter] Excluded real person ({self._progress['filtered']} rejected, {len(valid_files)}/{num_images} kept)"
                            continue
                        else:
                            logger.info(f"[Pinterest AI Filter] {reason}")

                    valid_files.append(fpath)

                # Renumber valid surviving files sequentially
                renamed_files = []
                for idx, fpath in enumerate(valid_files, start=start_offset + 1):
                    ext = os.path.splitext(fpath)[1].lower()
                    if not ext:
                        ext = ".jpg"
                    
                    new_name = f"{idx:03d}{ext}"
                    new_path = os.path.join(output_dir, new_name)
                    
                    if fpath != new_path:
                        temp_path = os.path.join(output_dir, f"temp_{idx}{ext}")
                        os.rename(fpath, temp_path)
                        if os.path.exists(new_path):
                            os.remove(new_path)
                        os.rename(temp_path, new_path)
                        renamed_files.append(new_path)
                    else:
                        renamed_files.append(new_path)

                downloaded_files = renamed_files
                self._progress["current_image"] = len(downloaded_files)

        except ImportError:
            logger.error("[Pinterest] pinterest-dl not installed. Run: pip install pinterest-dl")
            self._progress["message"] = "Error: pinterest-dl not installed"
            raise RuntimeError("pinterest-dl library not installed")

        except Exception as e:
            logger.error(f"[Pinterest] Error scraping '{query}': {e}")
            self._progress["message"] = f"[Pinterest] Error: {str(e)}"

        logger.info(f"[Pinterest] Completed download of {len(downloaded_files)} images for '{query}'")
        return downloaded_files

