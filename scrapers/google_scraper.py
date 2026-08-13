"""
Google Image Search scraper using Playwright browser automation.
"""
import os
import time
import logging
import hashlib
import urllib.parse

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GoogleImageScraper(BaseScraper):
    """Scrape and download images from Google Image Search using Playwright."""

    def __init__(self, delay: int = 2, headless: bool = True):
        super().__init__()
        self.delay = delay
        self.headless = headless

    @property
    def source_name(self) -> str:
        return "Google Images"

    def scrape(self, query: str, output_dir: str, num_images: int) -> list[str]:
        """
        Search Google Images for the query and download results.
        """
        if self.is_stopped():
            return []

        downloaded_files = []

        try:
            from playwright.sync_api import sync_playwright

            logger.info(f"[Google] Searching for '{query}' — target: {num_images} images")
            self._progress["message"] = f"[Google] Launching browser for: {query}"

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
                page = context.new_page()

                # Navigate to Google Images
                encoded_query = urllib.parse.quote(query)
                search_url = f"https://www.google.com/search?q={encoded_query}&tbm=isch&hl=en"
                page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)

                # Accept cookies if dialog appears
                try:
                    accept_btn = page.query_selector('button:has-text("Accept all")')
                    if accept_btn:
                        accept_btn.click()
                        time.sleep(1)
                except Exception:
                    pass

                image_urls = set()
                scroll_count = 0
                max_scrolls = max(num_images // 10, 10)

                self._progress["message"] = f"[Google] Collecting image URLs for: {query}"

                # Scroll to load more images
                while len(image_urls) < num_images and scroll_count < max_scrolls:
                    if self.is_stopped():
                        break

                    # Collect thumbnail image elements
                    thumbnails = page.query_selector_all('img[data-src], img.YQ4gaf, img.Q4LuWd, img[jsname]')

                    for thumb in thumbnails:
                        if len(image_urls) >= num_images:
                            break

                        try:
                            # Try clicking the thumbnail to get full-size URL
                            src = thumb.get_attribute("data-src") or thumb.get_attribute("src")
                            if src and src.startswith("http") and "gstatic" not in src and "google" not in src:
                                image_urls.add(src)
                        except Exception:
                            continue

                    # Try to get higher-resolution images by clicking thumbnails
                    if len(image_urls) < num_images:
                        try:
                            # Find clickable thumbnail containers
                            thumb_containers = page.query_selector_all('div[jscontroller] a[jsname]')
                            for container in thumb_containers:
                                if len(image_urls) >= num_images or self.is_stopped():
                                    break
                                try:
                                    container.click(timeout=2000)
                                    time.sleep(0.5)

                                    # Look for the large image in the side panel
                                    large_imgs = page.query_selector_all('img[jsname="kn3ccd"], img.sFlh5c, img.iPVvYb')
                                    for img in large_imgs:
                                        src = img.get_attribute("src")
                                        if src and src.startswith("http") and "gstatic" not in src and "encrypted" not in src:
                                            image_urls.add(src)
                                            break
                                except Exception:
                                    continue
                        except Exception:
                            pass

                    # Scroll down to load more
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1.5)

                    # Check for "Show more results" button
                    try:
                        show_more = page.query_selector('input[value="Show more results"]')
                        if show_more:
                            show_more.click()
                            time.sleep(2)
                    except Exception:
                        pass

                    scroll_count += 1
                    self._progress["message"] = f"[Google] Found {len(image_urls)} URLs (scroll {scroll_count}): {query}"

                browser.close()

            # Download collected images
            logger.info(f"[Google] Collected {len(image_urls)} URLs for '{query}', downloading...")
            self._progress["message"] = f"[Google] Downloading {len(image_urls)} images for: {query}"

            for idx, url in enumerate(list(image_urls)[:num_images]):
                if self.is_stopped():
                    break

                self._progress["current_image"] = idx + 1
                self._progress["message"] = f"[Google] Downloading {idx + 1}/{min(len(image_urls), num_images)}: {query}"

                try:
                    file_path = self._download_image(url, output_dir, idx + 1)
                    if file_path:
                        downloaded_files.append(file_path)
                except Exception as e:
                    logger.error(f"[Google] Download failed for image {idx + 1}: {e}")
                    continue

                if self.delay > 0:
                    time.sleep(self.delay * 0.3)

        except ImportError:
            logger.error("[Google] Playwright not installed. Run: pip install playwright && playwright install chromium")
            self._progress["message"] = "Error: Playwright not installed"
            raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install chromium")

        except Exception as e:
            logger.error(f"[Google] Error scraping '{query}': {e}")
            self._progress["message"] = f"[Google] Error: {str(e)}"

        # Delay between position searches
        if self.delay > 0:
            time.sleep(self.delay)

        logger.info(f"[Google] Downloaded {len(downloaded_files)} images for '{query}'")
        return downloaded_files

    @staticmethod
    def _download_image(url: str, output_dir: str, index: int) -> str | None:
        """Download a single image from URL."""
        import requests

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.google.com/",
            }
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()

            # Determine file extension
            content_type = response.headers.get("content-type", "image/jpeg")
            ext_map = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/gif": ".gif",
                "image/webp": ".webp",
                "image/svg+xml": ".svg",
            }
            ext = ext_map.get(content_type.split(";")[0].strip(), ".jpg")

            file_name = f"{index:03d}{ext}"
            file_path = os.path.join(output_dir, file_name)

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Validate it's a real image (at least 1KB)
            if os.path.getsize(file_path) < 1024:
                os.remove(file_path)
                return None

            return file_path

        except Exception as e:
            logger.error(f"[Google] Download failed for {url}: {e}")
            return None
