# 📸 TverKar Image Scrapping & Photorealistic AI Generation Platform

A full-stack, enterprise-grade automated image dataset collection and photorealistic AI generation platform designed for assembling curated workplace, persona, and job-position image datasets.

Supports **OpenRouter Multi-Key Cloud Generation** (*Gemini 2.5/3.1 Flash Image*, *OpenAI GPT-5 Image*), **Local GPU Diffusion Hot-Swapping** (*Juggernaut XL*, *RealVisXL*, *MajicMIX*, *EpiCRealism*, *Realistic Vision*), **Google Images (Playwright Headless)**, **Pinterest Scraper**, **Google Gemini Imagen**, and **OpenAI DALL-E 3**.

---

## 🌟 Key Features

### 🌐 1. Cloud AI Image Generation via OpenRouter (Multi-Key Profiles)
- **Unified Multi-Account Key Pool:** Switch seamlessly between multiple OpenRouter accounts (`sophy_coder`, `aht50712`, `asp25035`, `openrouter_default`, `sophyset2016`) directly from the Web UI to bypass rate limits and distribute usage.
- **Multimodal State-of-the-Art Models:**
  - 🌟 **Google Gemini 2.5 Flash Image** (`google/gemini-2.5-flash-image`): Google's premier multimodal model for hyper-realistic visual fidelity.
  - ⚡ **Google Gemini 3.1 Flash Image** (`google/gemini-3.1-flash-image`): Next-gen ultra-fast cloud generation.
  - 🤖 **OpenAI GPT-5 Image / Mini** (`openai/gpt-5-image`, `openai/gpt-5-image-mini`): High-resolution detailed realistic worker scenarios.
- **Token & Credit Optimization:** Auto-configured with constrained `max_tokens` (256) to ensure 100% compliance with free-tier token reservation policies.
- **Multi-Format Image Extraction:** Parses both embedded base64 data URIs and external CDN URLs automatically.

### 🎨 2. Unified Local Photorealistic AI Engine (`sd_server.py`)
- Standalone FastAPI microservice wrapping HuggingFace Diffusers with CUDA acceleration.
- **Zero VRAM Conflict Hot-Swapping:** Switch models dynamically from the Web UI with automated VRAM cache garbage collection.
- **100% Open & Un-gated Models (No HF token required):**
  - 🏢 **Juggernaut XL v9 (SDXL 1024×1024):** Factory uniforms, industrial equipment, safety gear, and warehouse tools.
  - 🌟 **RealVisXL v4.0 (SDXL 1024×1024):** High-resolution DSLR human skin textures, realistic pores, and authentic Asian portraits.
  - 🌸 **MajicMIX Realistic v7 (SD 1.5):** Specialized East/Southeast Asian persona and worker portraits.
  - 📷 **EpiCRealism (SD 1.5):** Unposed, natural daylight documentary photography.
  - ⚡ **Realistic Vision v6.0 (SD 1.5):** Ultra-fast generation (2–4s per image).

### 📸 3. Pro DSLR Documentary Prompt Engine
- Automatically constructs authentic prompts tailored for documentary photography (35mm lens, natural daytime window lighting, genuine human skin texture, real work uniforms, natural postures).
- Comprehensive negative prompting strictly filtering out CGI, plastic/airbrushed skin, anime, 3D renders, and studio lighting artifacts.

### 🤖 4. AI-Generated Person Filter (Vision Classification)
- Built-in 2D Fourier Spectrum (FFT) texture analyzer + local Ollama, Gemini Flash, or OpenAI GPT-4o-mini Vision detection to filter out real humans when synthetic-only persona data is required.

### 📦 5. Interactive Dashboard, Instant Gallery & 1-Click ZIP Downloads
- **Live SSE Progress Stream:** Real-time updates on active scraping/generation jobs, image counters, and error logs.
- **Gallery Quick-View & Direct ZIP:** 1-click download of all images for any position as a compressed `.zip` archive.
- **Smart Filtering:** Sort by *"Recently Generated"* (with `✨ Recent` badges), sort by name/count, and filter with instant search.

---

## 🏗️ Architecture Overview

```mermaid
graph TD
    UI[Web Browser / Glassmorphism Dashboard] -->|HTTP REST / SSE Stream| Flask[Flask Backend App :5000]
    Flask -->|Queue & Job Dispatcher| Scrapers[Scraper & Generator Engine]
    
    subgraph Scraping & Generation Sources
        Scrapers -->|OpenRouter Cloud API| OpenRouter[OpenRouter Multi-Key Pool\n(Gemini 2.5/3.1, GPT-5)]
        Scrapers -->|Direct Cloud API| DirectCloud[Gemini Imagen / OpenAI DALL-E 3]
        Scrapers -->|Chromium Headless| Playwright[Google Images Playwright]
        Scrapers -->|HTTP API / Browser| Pinterest[Pinterest Scraper]
        Scrapers -->|HTTP REST :7860| SDServer[Unified SD FastAPI Server]
    end

    SDServer -->|Dynamic FP16 Hot-Swap| GPU[(NVIDIA GPU VRAM / CUDA)]
    Flask -->|Organized File Output| Storage[(downloads/<Position_Name>/001.png ...)]
```

---

## 🚀 Quick Start Guide

### System Requirements
* **OS:** Linux (Ubuntu 20.04+, Debian, WSL2) or macOS / Windows
* **Python:** 3.10 to 3.12 (Tested on Python 3.12)
* **GPU (For Local AI Generation):** NVIDIA GPU with 6 GB+ VRAM (Tesla T4, RTX 3060/4060 or higher). CUDA 12.x+.
* **Disk Space:** 20 GB+ for local model weights and downloaded image datasets.

---

### 1. Installation

```bash
# 1. Clone the repository
git clone https://github.com/Phyrakset/image-scrapping.git
cd image-scrapping

# 2. Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate       # Linux/macOS
# .\venv\Scripts\Activate      # Windows PowerShell

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Playwright Chromium browser binary
playwright install chromium
```

---

### 2. Environment Configuration

Copy `.env.example` to `.env` and configure your API keys and parameters:

```bash
cp .env.example .env
```

Edit `.env`:
```env
# Flask Server Settings
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=True

# OpenRouter Multi-Profile API Keys
OPENROUTER_KEY_SOPHY_CODER=sk-or-v1-xxxxxxxx
OPENROUTER_KEY_AHT50712=sk-or-v1-xxxxxxxx
OPENROUTER_KEY_ASP25035=sk-or-v1-xxxxxxxx
OPENROUTER_KEY_DEFAULT=sk-or-v1-xxxxxxxx
OPENROUTER_KEY_SOPHYSET2016=sk-or-v1-xxxxxxxx
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx

# Direct AI Cloud Providers (Optional)
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Local Stable Diffusion Microservice
LOCAL_SD_URL=http://127.0.0.1:7860

# Scraping Settings
IMAGES_PER_POSITION=40
SEARCH_SUFFIX=Single Person Asian
ONLY_AI_PERSON=false
DOWNLOAD_DELAY=2
BASE_DOWNLOAD_DIR=downloads
POSITION_FILE=position.text
```

---

### 3. Running the Services

#### Option A: Running with OpenRouter (Cloud Mode — No Local GPU Required)
```bash
source venv/bin/activate
python app.py
```
> Open `http://localhost:5000` in your browser, switch to the **OpenRouter (Cloud)** tab, select your account profile and model, and begin generating.

#### Option B: Running with Local GPU Diffusion (Local SD Mode)
Open two terminal tabs:

**Terminal 1 — Local Diffusion Engine (Port 7860):**
```bash
source venv/bin/activate
python sd_server.py --port 7860
```

**Terminal 2 — Flask Web Dashboard (Port 5000):**
```bash
source venv/bin/activate
python app.py
```

#### Option C: Remote Access via Cloudflare Tunnel (Remote GCP/AWS VM)
```bash
npx cloudflared tunnel --url http://localhost:5000
```
Open the printed `https://<unique-id>.trycloudflare.com` URL in your browser.

---

## 📖 User Guide

### 1. Generating via OpenRouter Cloud Models
1. Navigate to **Scrape Images** on the sidebar.
2. Select the **🌐 OpenRouter (Cloud)** tab.
3. Choose your **OpenRouter Account Key** from the profile dropdown (e.g., `Sophy Coder`, `aht50712`, etc.).
4. Select your **Cloud Model** (`Google Gemini 2.5 Flash Image`, `Gemini 3.1 Flash Image`, or `OpenAI GPT-5 Image`).
5. Choose positions or check **Target Incomplete Positions Only**.
6. Click **▶️ Start Scraping**.

### 2. Generating via Local GPU Diffusion
1. Select the **🖥️ Local SD (Free)** tab.
2. Select your desired local model (`Juggernaut XL v9`, `RealVisXL v4.0`, `MajicMIX Realistic v7`, `EpiCRealism`, `Realistic Vision v6.0`).
3. Set your target image count and click **▶️ Start Scraping**.

### 3. Managing Position Lists
- Go to the **Positions** tab on the sidebar.
- Add new job titles or positions one by one.
- View per-position image counts, completion percentages, and missing counts.
- Delete obsolete positions.

### 4. Viewing & Exporting Datasets
- Go to the **Gallery** tab.
- Click **⬇️ Download ZIP** on any position card to download all images as a `.zip` archive.
- Click **📋 Copy Path** to copy the exact server directory path for model training scripts.

---

## 💻 Developer & API Reference

### Project Directory Structure

```
image-scrapping/
├── app.py                      # Flask API server, routes, SSE streaming, & gallery endpoints
├── sd_server.py                # Standalone FastAPI Diffusion Microservice (Hugging Face diffusers)
├── config.py                   # Environment config loader, OpenRouter profile registry
├── requirements.txt            # Python dependencies
├── position.text               # Preloaded newline-delimited job titles list
├── .env.example                # Example environment configuration template
├── scrapers/
│   ├── base_scraper.py         # Abstract BaseScraper class with progress tracking & stopping
│   ├── ai_generator.py         # AI generation engine (OpenRouter, Local SD, Gemini, OpenAI)
│   ├── ai_detector.py          # Vision classifier & FFT texture analysis for AI vs Real person
│   ├── pinterest_scraper.py    # Pinterest scraper (pinterest-dl with Playwright fallback)
│   └── google_scraper.py       # Google Images Playwright headless browser scraper
├── templates/
│   └── index.html              # Dark glassmorphism dashboard UI
├── static/
│   ├── css/style.css           # Styling, animations, layout tokens
│   └── js/app.js               # Frontend application state, SSE listener, gallery controller
└── downloads/                  # Output directory partitioned by position names
```

---

### REST API Endpoints

#### Flask Backend (`http://localhost:5000`)

| Method | Endpoint | Description | Request / Query Params |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/stats` | Overall dataset stats (positions, total images, status) | None |
| `GET` | `/api/positions` | Position list with downloaded/missing stats | `?target=40` |
| `POST` | `/api/positions` | Add a new position | `{"name": "Civil Engineer"}` |
| `DELETE` | `/api/positions/<id>` | Delete position by index ID | None |
| `POST` | `/api/scrape/start` | Start scraping or AI generation job | `{"source": "ai_openrouter", "openrouter_profile": "sophy_coder", "openrouter_model": "google/gemini-2.5-flash-image", "count": 40}` |
| `POST` | `/api/scrape/stop` | Gracefully stop the current active job | None |
| `GET` | `/api/scrape/status` | Current scraper status and progress counters | None |
| `GET` | `/api/scrape/stream` | Server-Sent Events (SSE) stream for live UI progress | None |
| `GET` | `/api/images` | Overview of all folders with previews and counts | None |
| `GET` | `/api/images/<path:position>` | List all image file URLs for a specific position | None |
| `GET` | `/api/download_zip/<path:position>` | Stream zip archive of all images in that folder | None |
| `GET` | `/api/settings` | Read current runtime configuration (masked keys) | None |
| `POST` | `/api/settings` | Update runtime settings | `{"images_per_position": 40, ...}` |
| `GET` | `/api/local_sd/status` | Health check for local SD FastAPI microservice | None |

#### Local Diffusion Microservice (`http://localhost:7860`)

| Method | Endpoint | Description | Payload |
| :--- | :--- | :--- | :--- |
| `GET` | `/sdapi/v1/models` | List all available and active GPU models | None |
| `GET` | `/sdapi/v1/options` | Healthcheck and current loaded checkpoint | None |
| `POST` | `/sdapi/v1/switch_model` | Hot-swap active model in VRAM | `{"model": "juggernaut"}` |
| `POST` | `/sdapi/v1/txt2img` | Generate images via Automatic1111-compatible API | `{"prompt": "...", "model": "realvisxl", "width": 1024, "height": 1024, "steps": 25}` |

---

### Adding a New Model to `sd_server.py`

To register a new Hugging Face diffusion model:

1. Open [`sd_server.py`](file:///home/jupyter/WORKINGNA/image-scrapping/sd_server.py).
2. Add the model definition to `AVAILABLE_MODELS`:
```python
AVAILABLE_MODELS = {
    "my_custom_model": {
        "name": "✨ My Custom Model (SDXL 1024x1024)",
        "id": "Author/Model-Repo-Name",
        "type": "sdxl",   # "sdxl" or "sd15"
        "description": "Photorealistic worker portrait model.",
        "default_width": 1024,
        "default_height": 1024,
        "default_steps": 25,
        "cfg": 6.5,
    },
}
```
3. Add the corresponding `<option>` tag in [`templates/index.html`](file:///home/jupyter/WORKINGNA/image-scrapping/templates/index.html):
```html
<option value="my_custom_model">✨ My Custom Model (SDXL 1024×1024)</option>
```

---

## 🛠️ Troubleshooting & FAQ

### 1. OpenRouter Credit / Token Reservation Error
* **Symptom:** `HTTP 402 / 400: Your account does not have enough credits to generate max_tokens`.
* **Fix:** The codebase automatically sets `"max_tokens": 256` in [`scrapers/ai_generator.py`](file:///home/jupyter/WORKINGNA/image-scrapping/scrapers/ai_generator.py#L240), preventing large upfront token reservations on free/low-balance keys.

### 2. Local SD Microservice Connection Refused
* **Symptom:** `Cannot connect to Local Stable Diffusion on http://127.0.0.1:7860`.
* **Fix:** Ensure `python sd_server.py --port 7860` is running in an active terminal with CUDA available. Verify with `curl http://127.0.0.1:7860/sdapi/v1/options`.

### 3. CUDA Out of Memory (OOM) on Low-VRAM GPUs
* **Fix:** When running SDXL models on GPUs with < 8GB VRAM, the engine uses `torch.float16` and enables attention slicing (`pipe.enable_attention_slicing()`). Alternatively, select SD 1.5 models (`MajicMIX`, `Realistic Vision`, or `EpiCRealism`) which only consume ~3.2 GB VRAM.

### 4. Playwright Browser Not Found
* **Symptom:** `playwright._impl._errors.Error: Executable doesn't exist`.
* **Fix:** Run `playwright install chromium` inside your virtual environment.

---

## 📄 License

MIT License. Developed for automated AI dataset generation and visual research.
