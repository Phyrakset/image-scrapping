"""
Google Image Search scraper using Playwright and fallback web search.
"""
import os
import re
import time
import base64
import logging
import urllib.parse
from typing import List

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GoogleImageScraper(BaseScraper):
    """Scrape and download images from Google & Web Image Search."""

    def __init__(self, delay: float = 2.0, headless: bool = True):
        super().__init__()
        self.delay = delay
        self.headless = headless

    @property
    def source_name(self) -> str:
        return "Google Images"

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
        Search Google/Web Images for the query and download results into output_dir.
        Optionally filters to only keep AI-generated person images and reject real person photos.
        """
        if self.is_stopped():
            return []

        downloaded_files = []
        image_urls = []

        # Enhance query if only_ai_person is enabled
        effective_query = query
        if only_ai_person:
            ai_keywords = ["AI generated", "AI art", "Midjourney", "AI portrait"]
            if not any(kw.lower() in query.lower() for kw in ai_keywords):
                effective_query = f"{query} AI generated person Midjourney"

        # Multiplier for candidates when filtering is active
        url_fetch_target = num_images * 6 if only_ai_person else num_images * 2

        try:
            logger.info(f"[Google] Searching for '{effective_query}' — target: {num_images} images (offset {start_offset}, only_ai={only_ai_person})")
            self._progress["message"] = f"[Google] Searching for: {effective_query}"
            self._progress["total_images"] = num_images
            self._progress["current_image"] = 0

            # Step 1: Try Playwright extraction on Google Images
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=self.headless,
                        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
                    )
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        viewport={"width": 1920, "height": 1080},
                    )
                    page = context.new_page()
                    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                    encoded_query = urllib.parse.quote(effective_query)
                    search_url = f"https://www.google.com/search?q={encoded_query}&tbm=isch&hl=en"
                    page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                    time.sleep(1.5)

                    if "sorry/index" not in page.url:
                        # Extract img src attributes
                        imgs = page.query_selector_all('img')
                        for img in imgs:
                            src = img.get_attribute("src") or img.get_attribute("data-src") or img.get_attribute("data-iurl")
                            if src and (src.startswith("http") or src.startswith("data:image/")):
                                if src not in image_urls:
                                    image_urls.append(src)

                        # Regex extract image URLs from scripts
                        html_content = page.content()
                        found_urls = re.findall(r'\["(https?://[^"]+\.(?:jpg|jpeg|png|webp))",\s*\d+,\s*\d+\]', html_content)
                        for u in found_urls:
                            if "gstatic" not in u and "google" not in u and u not in image_urls:
                                image_urls.append(u)

                    browser.close()
            except Exception as e:
                logger.warning(f"[Google] Playwright search notice: {e}")

            # Step 2: Fallback to Web Image Search engine if Playwright produced insufficient URLs
            if len(image_urls) < url_fetch_target:
                logger.info(f"[Google] Using web image engine for '{effective_query}'...")
                fallback_urls = self._search_web_images(effective_query, url_fetch_target)
                for u in fallback_urls:
                    if u not in image_urls:
                        image_urls.append(u)

            logger.info(f"[Google] Collected {len(image_urls)} URLs for '{effective_query}', processing...")
            self._progress["message"] = f"[Google] Downloading candidates for: {effective_query}"

            # Step 3: Download & classify collected images
            os.makedirs(output_dir, exist_ok=True)
            for idx, url in enumerate(image_urls):
                if len(downloaded_files) >= num_images or self.is_stopped():
                    break

                target_file_idx = start_offset + len(downloaded_files) + 1
                # Download to a temporary index first
                temp_idx = 90000 + idx
                temp_path = self._download_image(url, output_dir, temp_idx)
                if not temp_path or not os.path.exists(temp_path):
                    continue

                # Run AI Person Filter if enabled
                if only_ai_person and detector:
                    self._progress["message"] = f"[Google AI Filter] Inspecting image {len(downloaded_files) + 1}/{num_images}..."
                    is_ai, reason = detector.is_ai_person(temp_path)
                    if not is_ai:
                        logger.info(f"[Google AI Filter] {reason}")
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass
                        self._progress["filtered"] = self._progress.get("filtered", 0) + 1
                        self._progress["message"] = f"[AI Filter] Excluded real person ({self._progress['filtered']} rejected, {len(downloaded_files)}/{num_images} kept)"
                        continue
                    else:
                        logger.info(f"[Google AI Filter] {reason}")

                # Image is approved: rename to sequential index
                ext = os.path.splitext(temp_path)[1].lower()
                final_name = f"{target_file_idx:03d}{ext}"
                final_path = os.path.join(output_dir, final_name)
                if os.path.exists(final_path):
                    os.remove(final_path)
                os.rename(temp_path, final_path)

                downloaded_files.append(final_path)
                self._progress["current_image"] = len(downloaded_files)
                self._progress["message"] = f"[Google] Downloaded {len(downloaded_files)}/{num_images} for '{query}'"

                if self.delay > 0:
                    time.sleep(self.delay * 0.2)

        except Exception as e:
            logger.error(f"[Google] Error scraping '{query}': {e}")
            self._progress["message"] = f"[Google] Error: {str(e)}"

        if self.delay > 0:
            time.sleep(self.delay)

        logger.info(f"[Google] Downloaded {len(downloaded_files)} images for '{query}'")
        return downloaded_files

    @staticmethod
    def _search_web_images(query: str, max_urls: int = 30) -> List[str]:
        """Fetch image URLs via web image search engine."""
        import requests
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.bing.com/images/search?q={encoded_query}&form=HDRSC2&first=1"
        urls = []
        try:
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code == 200:
                murls = re.findall(r'murl&quot;:&quot;(https?://[^&]+)&quot;', r.text)
                seen = set()
                for u in murls:
                    u = u.replace("\\/", "/")
                    if u not in seen:
                        seen.add(u)
                        urls.append(u)
                    if len(urls) >= max_urls:
                        break
        except Exception as e:
            logger.error(f"[Google] Fallback search error: {e}")
        return urls

    @staticmethod
    def _download_image(url: str, output_dir: str, index: int) -> str | None:
        """Download a single image from HTTP URL or base64 data URI."""
        import requests

        try:
            # Handle Base64 Data URI
            if url.startswith("data:image/"):
                header, data = url.split(",", 1)
                mime_type = header.split(";")[0].replace("data:", "")
                ext_map = {
                    "image/jpeg": ".jpg",
                    "image/png": ".png",
                    "image/gif": ".gif",
                    "image/webp": ".webp",
                }
                ext = ext_map.get(mime_type, ".jpg")
                file_name = f"{index:03d}{ext}"
                file_path = os.path.join(output_dir, file_name)

                img_data = base64.b64decode(data)
                with open(file_path, "wb") as f:
                    f.write(img_data)

                if os.path.getsize(file_path) > 500:
                    return file_path
                else:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return None

            # Handle HTTP/HTTPS URL
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": "https://www.google.com/",
            }
            response = requests.get(url, headers=headers, timeout=20, stream=True)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "image/jpeg")
            ext_map = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/gif": ".gif",
                "image/webp": ".webp",
                "image/svg+xml": ".svg",
            }
            ext = ext_map.get(content_type.split(";")[0].strip().lower(), ".jpg")

            file_name = f"{index:03d}{ext}"
            file_path = os.path.join(output_dir, file_name)

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            if os.path.getsize(file_path) < 1024:
                if os.path.exists(file_path):
                    os.remove(file_path)
                return None

            return file_path

        except Exception as e:
            logger.error(f"[Google] Download failed for {url[:60]}: {e}")
            return None

