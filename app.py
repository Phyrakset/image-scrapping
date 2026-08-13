"""
TverKar Image Scrapping — Flask Backend API Server
"""
import os
import json
import time
import logging
import threading
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from flask_cors import CORS

import config
from scrapers.pinterest_scraper import PinterestScraper
from scrapers.google_scraper import GoogleImageScraper
from scrapers.ai_generator import AIImageGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
CORS(app)

# Global state
active_scraper = None
scrape_thread = None
scrape_results = {}
settings = {
    "gemini_api_key": config.GEMINI_API_KEY,
    "openai_api_key": config.OPENAI_API_KEY,
    "images_per_position": config.IMAGES_PER_POSITION,
    "search_suffix": config.SEARCH_SUFFIX,
    "download_delay": config.DOWNLOAD_DELAY,
    "base_download_dir": config.BASE_DOWNLOAD_DIR,
}


# -------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------

def load_positions() -> list[str]:
    """Load unique positions from position.text file (skip header line)."""
    positions = []
    seen = set()
    try:
        with open(config.POSITION_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[1:]:  # Skip header
            pos = line.strip()
            if pos and pos not in seen:
                positions.append(pos)
                seen.add(pos)
    except FileNotFoundError:
        logger.error(f"Position file not found: {config.POSITION_FILE}")
    return positions


def save_positions(positions: list[str]):
    """Save positions to position.text file."""
    with open(config.POSITION_FILE, "w", encoding="utf-8") as f:
        f.write("Position Title \n")
        for pos in positions:
            f.write(f"{pos}\n")


def get_folder_stats(base_dir: str) -> dict:
    """Get image counts per position folder."""
    stats = {}
    if not os.path.exists(base_dir):
        return stats
    for folder_name in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder_name)
        if os.path.isdir(folder_path):
            image_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
            images = [
                f for f in os.listdir(folder_path)
                if os.path.splitext(f)[1].lower() in image_exts
            ]
            stats[folder_name] = {
                "count": len(images),
                "folder": folder_path,
            }
    return stats


# -------------------------------------------------------------------
# Page Routes
# -------------------------------------------------------------------

@app.route("/")
def index():
    """Serve admin dashboard."""
    return render_template("index.html")


@app.route("/downloads/<path:filepath>")
def serve_download(filepath):
    """Serve downloaded images for gallery preview."""
    return send_from_directory(settings["base_download_dir"], filepath)


# -------------------------------------------------------------------
# API: Positions
# -------------------------------------------------------------------

@app.route("/api/positions", methods=["GET"])
def api_get_positions():
    """Return all positions with image counts and missing image details."""
    positions = load_positions()
    folder_stats = get_folder_stats(settings["base_download_dir"])
    target_count = request.args.get("target", settings["images_per_position"], type=int)

    result = []
    incomplete_count = 0
    total_missing = 0

    for idx, pos in enumerate(positions):
        sanitized = pos.strip()
        for char in '<>:"/\\|?*':
            sanitized = sanitized.replace(char, "-")
        count = folder_stats.get(sanitized, {}).get("count", 0)
        missing = max(0, target_count - count)
        is_incomplete = count < target_count

        if is_incomplete:
            incomplete_count += 1
            total_missing += missing

        result.append({
            "id": idx,
            "name": pos,
            "folder_name": sanitized,
            "images_downloaded": count,
            "target_images": target_count,
            "missing_images": missing,
            "is_incomplete": is_incomplete,
        })

    return jsonify({
        "positions": result,
        "total": len(result),
        "target_per_position": target_count,
        "incomplete_total": incomplete_count,
        "complete_total": len(result) - incomplete_count,
        "total_missing_images": total_missing,
    })


@app.route("/api/positions", methods=["POST"])
def api_add_position():
    """Add a new position."""
    data = request.get_json()
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Position name is required"}), 400

    positions = load_positions()
    if name in positions:
        return jsonify({"error": "Position already exists"}), 409

    positions.append(name)
    save_positions(positions)
    return jsonify({"message": f"Added: {name}", "total": len(positions)})


@app.route("/api/positions/<int:pos_id>", methods=["DELETE"])
def api_delete_position(pos_id):
    """Delete a position by ID."""
    positions = load_positions()
    if pos_id < 0 or pos_id >= len(positions):
        return jsonify({"error": "Invalid position ID"}), 404

    removed = positions.pop(pos_id)
    save_positions(positions)
    return jsonify({"message": f"Removed: {removed}", "total": len(positions)})


# -------------------------------------------------------------------
# API: Scraping
# -------------------------------------------------------------------

@app.route("/api/scrape/start", methods=["POST"])
def api_scrape_start():
    """Start a scraping job."""
    global active_scraper, scrape_thread, scrape_results

    if active_scraper and active_scraper.get_progress().get("status") == "running":
        return jsonify({"error": "A scraping job is already running"}), 409

    data = request.get_json() or {}
    source = data.get("source", "pinterest")
    position_ids = data.get("positions", [])
    count = data.get("count", settings["images_per_position"])
    search_suffix = data.get("search_suffix", settings["search_suffix"])
    top_up = data.get("top_up", True)
    only_incomplete = data.get("only_incomplete", False)

    all_positions = load_positions()
    folder_stats = get_folder_stats(settings["base_download_dir"])

    # Resolve position IDs to names
    if position_ids:
        selected = [all_positions[i] for i in position_ids if 0 <= i < len(all_positions)]
    else:
        selected = all_positions

    # Filter only incomplete positions if requested
    if only_incomplete:
        filtered_selected = []
        for pos in selected:
            sanitized = pos.strip()
            for char in '<>:"/\\|?*':
                sanitized = sanitized.replace(char, "-")
            cur_count = folder_stats.get(sanitized, {}).get("count", 0)
            if cur_count < count:
                filtered_selected.append(pos)
        selected = filtered_selected

    if not selected:
        return jsonify({"error": "No positions selected or all selected positions are already complete"}), 400

    # Create scraper
    delay = settings["download_delay"]
    if source == "pinterest":
        active_scraper = PinterestScraper(delay=delay)
    elif source == "google":
        active_scraper = GoogleImageScraper(delay=delay, headless=True)
    elif source == "ai_gemini":
        active_scraper = AIImageGenerator(
            provider="gemini",
            api_key=settings["gemini_api_key"],
            delay=max(delay, 3),
        )
    elif source == "ai_openai":
        active_scraper = AIImageGenerator(
            provider="openai",
            api_key=settings["openai_api_key"],
            delay=max(delay, 3),
        )
    else:
        return jsonify({"error": f"Unknown source: {source}"}), 400

    # Start scraping in background thread
    def run_scrape():
        global scrape_results
        base_dir = settings["base_download_dir"]
        os.makedirs(base_dir, exist_ok=True)
        scrape_results = active_scraper.scrape_positions(
            selected,
            base_dir,
            count,
            search_suffix=search_suffix,
            top_up=top_up,
        )

    scrape_thread = threading.Thread(target=run_scrape, daemon=True)
    scrape_thread.start()

    return jsonify({
        "message": f"Started {source} scraping for {len(selected)} positions (top_up={top_up})",
        "source": source,
        "positions_count": len(selected),
        "images_per_position": count,
        "search_suffix": search_suffix,
        "top_up": top_up,
    })



@app.route("/api/scrape/stop", methods=["POST"])
def api_scrape_stop():
    """Stop the running scrape job."""
    global active_scraper
    if active_scraper:
        active_scraper.stop()
        return jsonify({"message": "Stop signal sent"})
    return jsonify({"error": "No active scraping job"}), 404


@app.route("/api/scrape/status", methods=["GET"])
def api_scrape_status():
    """Get current scraping status."""
    if active_scraper:
        return jsonify(active_scraper.get_progress())
    return jsonify({
        "status": "idle",
        "message": "No active job",
        "current_position": "",
        "current_image": 0,
        "total_images": 0,
        "downloaded": 0,
        "failed": 0,
        "positions_done": 0,
        "positions_total": 0,
    })


@app.route("/api/scrape/stream")
def api_scrape_stream():
    """Server-Sent Events stream for real-time progress updates."""
    def event_stream():
        while True:
            if active_scraper:
                progress = active_scraper.get_progress()
            else:
                progress = {"status": "idle", "message": "No active job"}

            yield f"data: {json.dumps(progress)}\n\n"

            if progress.get("status") in ("completed", "error", "stopped", "idle"):
                # Send a few more updates then stop
                time.sleep(1)
                yield f"data: {json.dumps(progress)}\n\n"
                break

            time.sleep(1)

    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/api/scrape/results", methods=["GET"])
def api_scrape_results():
    """Get results from the last scraping job."""
    return jsonify(scrape_results if scrape_results else {})


# -------------------------------------------------------------------
# API: Images / Gallery
# -------------------------------------------------------------------

@app.route("/api/images", methods=["GET"])
def api_images_overview():
    """List all position folders with image counts."""
    stats = get_folder_stats(settings["base_download_dir"])
    return jsonify(stats)


@app.route("/api/images/<path:position>", methods=["GET"])
def api_images_for_position(position):
    """Get list of images in a specific position folder."""
    folder_path = os.path.join(settings["base_download_dir"], position)
    if not os.path.exists(folder_path):
        return jsonify({"error": f"Folder not found: {position}"}), 404

    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
    images = []
    for f in sorted(os.listdir(folder_path)):
        if os.path.splitext(f)[1].lower() in image_exts:
            images.append({
                "name": f,
                "url": f"/downloads/{position}/{f}",
                "size": os.path.getsize(os.path.join(folder_path, f)),
            })

    return jsonify({
        "position": position,
        "count": len(images),
        "images": images,
    })


# -------------------------------------------------------------------
# API: Settings
# -------------------------------------------------------------------

@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    """Get current settings (mask API keys)."""
    masked = settings.copy()
    if masked["gemini_api_key"]:
        masked["gemini_api_key"] = masked["gemini_api_key"][:8] + "..." + masked["gemini_api_key"][-4:]
    if masked["openai_api_key"]:
        masked["openai_api_key"] = masked["openai_api_key"][:8] + "..." + masked["openai_api_key"][-4:]
    return jsonify(masked)


@app.route("/api/settings", methods=["POST"])
def api_update_settings():
    """Update settings."""
    data = request.get_json()

    if "gemini_api_key" in data and data["gemini_api_key"] and "..." not in data["gemini_api_key"]:
        settings["gemini_api_key"] = data["gemini_api_key"]
    if "openai_api_key" in data and data["openai_api_key"] and "..." not in data["openai_api_key"]:
        settings["openai_api_key"] = data["openai_api_key"]
    if "images_per_position" in data:
        settings["images_per_position"] = int(data["images_per_position"])
    if "search_suffix" in data:
        settings["search_suffix"] = str(data["search_suffix"]).strip()
    if "download_delay" in data:
        settings["download_delay"] = int(data["download_delay"])


    return jsonify({"message": "Settings updated", "settings": api_get_settings().get_json()})


# -------------------------------------------------------------------
# API: Dashboard Stats
# -------------------------------------------------------------------

@app.route("/api/stats", methods=["GET"])
def api_stats():
    """Get dashboard statistics."""
    positions = load_positions()
    stats = get_folder_stats(settings["base_download_dir"])
    total_images = sum(s["count"] for s in stats.values())
    folders_with_images = len([s for s in stats.values() if s["count"] > 0])

    scraper_status = "idle"
    if active_scraper:
        scraper_status = active_scraper.get_progress().get("status", "idle")

    return jsonify({
        "total_positions": len(positions),
        "total_images": total_images,
        "positions_with_images": folders_with_images,
        "scraper_status": scraper_status,
    })


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(config.BASE_DOWNLOAD_DIR, exist_ok=True)
    logger.info(f"Starting TverKar Image Scrapping server on http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    logger.info(f"Download directory: {config.BASE_DOWNLOAD_DIR}")
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG, threaded=True)
