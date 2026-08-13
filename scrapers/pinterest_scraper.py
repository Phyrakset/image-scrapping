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

    def scrape(self, query: str, output_dir: str, num_images: int, start_offset: int = 0) -> List[str]:
        """
        Search Pinterest for images matching the query and download them into output_dir.
        """
        if self.is_stopped():
            return []

        downloaded_files = []

        try:
            from pinterest_dl import PinterestDL

            logger.info(f"[Pinterest] Searching for '{query}' — target: {num_images} images")
            self._progress["message"] = f"[Pinterest] Searching: {query}"
            self._progress["total_images"] = num_images
            self._progress["current_image"] = 0

            pdl = PinterestDL.with_api()

            def on_progress(media):
                if self.is_stopped():
                    return
                self._progress["current_image"] = min(self._progress["current_image"] + 1, num_images)
                self._progress["message"] = f"[Pinterest] Found {self._progress['current_image']}/{num_images} for '{query}'"

            # Download using pinterest-dl search_and_download
            pdl.search_and_download(
                query=query,
                output_dir=output_dir,
                num=num_images,
                min_resolution=(0, 0),
                delay=self.delay,
                on_progress=on_progress
            )

            # Get downloaded files and standardize/sort sequential filenames if needed
            if os.path.exists(output_dir):
                raw_files = [
                    f for f in os.listdir(output_dir)
                    if os.path.isfile(os.path.join(output_dir, f)) and not f.startswith('.')
                ]
                
                # Sort files by creation time or name to maintain order
                raw_files.sort(key=lambda f: os.path.getmtime(os.path.join(output_dir, f)))

                renamed_files = []
                for idx, fname in enumerate(raw_files, start=1):
                    ext = os.path.splitext(fname)[1].lower()
                    if not ext:
                        ext = ".jpg"
                    
                    new_name = f"{idx:03d}{ext}"
                    old_path = os.path.join(output_dir, fname)
                    new_path = os.path.join(output_dir, new_name)
                    
                    if old_path != new_path:
                        # Avoid overwrite conflicts
                        temp_path = os.path.join(output_dir, f"temp_{idx}{ext}")
                        os.rename(old_path, temp_path)
                        if os.path.exists(new_path):
                            os.remove(new_path)
                        os.rename(temp_path, new_path)
                        renamed_files.append(new_path)
                    else:
                        renamed_files.append(new_path)

                downloaded_files = renamed_files

        except ImportError:
            logger.error("[Pinterest] pinterest-dl not installed. Run: pip install pinterest-dl")
            self._progress["message"] = "Error: pinterest-dl not installed"
            raise RuntimeError("pinterest-dl library not installed")

        except Exception as e:
            logger.error(f"[Pinterest] Error scraping '{query}': {e}")
            self._progress["message"] = f"[Pinterest] Error: {str(e)}"

        logger.info(f"[Pinterest] Completed download of {len(downloaded_files)} images for '{query}'")
        return downloaded_files

