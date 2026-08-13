"""
Base scraper interface for all image download sources.
"""
import os
import threading
from abc import ABC, abstractmethod


class BaseScraper(ABC):
    """Abstract base class for all image scrapers."""

    def __init__(self):
        self._progress = {
            "status": "idle",        # idle, running, completed, error, stopped
            "current_position": "",
            "current_image": 0,
            "total_images": 0,
            "downloaded": 0,
            "failed": 0,
            "message": "",
            "positions_done": 0,
            "positions_total": 0,
        }
        self._stop_event = threading.Event()

    @property
    def source_name(self) -> str:
        """Return the name of this scraper source."""
        return self.__class__.__name__

    @abstractmethod
    def scrape(self, query: str, output_dir: str, num_images: int) -> list[str]:
        """
        Scrape/download images for a given query.

        Args:
            query: The search query (position title).
            output_dir: Directory to save images.
            num_images: Number of images to download.

        Returns:
            List of downloaded file paths.
        """
        pass

    def scrape_positions(self, positions: list[str], base_dir: str, num_images: int, search_suffix: str = "Single Person Asian") -> dict:
        """
        Scrape images for multiple positions sequentially.

        Args:
            positions: List of position titles.
            base_dir: Base directory for downloads.
            num_images: Number of images per position.
            search_suffix: Suffix to append to search query (e.g. "Single Person Asian").

        Returns:
            Summary dict with results per position.
        """
        self._stop_event.clear()
        self._progress["status"] = "running"
        self._progress["positions_total"] = len(positions)
        self._progress["positions_done"] = 0

        results = {}

        for i, position in enumerate(positions):
            if self._stop_event.is_set():
                self._progress["status"] = "stopped"
                self._progress["message"] = f"Stopped after {i} positions"
                break

            # Sanitize folder name (uses ONLY the position name)
            folder_name = self._sanitize_folder_name(position)
            output_dir = os.path.join(base_dir, folder_name)
            os.makedirs(output_dir, exist_ok=True)

            # Build full search query (position + search suffix)
            search_query = f"{position} {search_suffix}".strip() if search_suffix else position

            self._progress["current_position"] = position
            self._progress["current_image"] = 0
            self._progress["total_images"] = num_images
            self._progress["message"] = f"Scraping: '{search_query}' -> folder '{folder_name}'"

            try:
                downloaded = self.scrape(search_query, output_dir, num_images)
                results[position] = {
                    "status": "success",
                    "count": len(downloaded),
                    "files": downloaded,
                    "folder": output_dir,
                    "search_query": search_query,
                }
                self._progress["downloaded"] += len(downloaded)
            except Exception as e:
                results[position] = {
                    "status": "error",
                    "error": str(e),
                    "folder": output_dir,
                    "search_query": search_query,
                }
                self._progress["failed"] += 1
                self._progress["message"] = f"Error on {position}: {str(e)}"

            self._progress["positions_done"] = i + 1

        if not self._stop_event.is_set():
            self._progress["status"] = "completed"
            self._progress["message"] = f"Completed all {len(positions)} positions"

        return results


    def get_progress(self) -> dict:
        """Return current progress status."""
        return self._progress.copy()

    def stop(self):
        """Signal the scraper to stop."""
        self._stop_event.set()
        self._progress["status"] = "stopping"
        self._progress["message"] = "Stop requested..."

    def is_stopped(self) -> bool:
        """Check if stop was requested."""
        return self._stop_event.is_set()

    @staticmethod
    def _sanitize_folder_name(name: str) -> str:
        """Sanitize position name for use as a folder name."""
        # Replace characters that are invalid in Windows folder names
        invalid_chars = '<>:"/\\|?*'
        sanitized = name.strip()
        for char in invalid_chars:
            sanitized = sanitized.replace(char, "-")
        # Replace multiple spaces/dashes with single
        while "  " in sanitized:
            sanitized = sanitized.replace("  ", " ")
        return sanitized.strip()
