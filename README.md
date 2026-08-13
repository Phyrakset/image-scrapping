# TverKar Image Scrapping Platform

A powerful web-based image scraping and AI generation platform designed to download position-specific images from multiple sources (**Pinterest**, **Google Images**, **Google Gemini Imagen**, and **OpenAI DALL-E**).

Built with Python, Flask, Playwright, `pinterest-dl`, and a dark glassmorphism Admin Dashboard UI.

---

## 🌟 Key Features

- 📌 **Pinterest Scraper**: High-speed image extraction using `pinterest-dl` with API and browser fallbacks.
- 🔍 **Google Images Scraper**: Automated browser scraping via Playwright (Chromium).
- ✨ **AI Image Generation**: Support for Google Gemini (Imagen 3) & OpenAI (DALL-E 3).
- 🏷️ **Search Query Modifier**: Automatically appends search terms (e.g. `"Single Person Asian"`) to position queries while storing images cleanly in position-named folders.
- 🔢 **Sequential Image Ordering**: Saves downloaded images in order (`001.jpg`, `002.jpg`, `003.jpg`, ...).
- 📋 **Position Manager**: Manage job positions directly from `position.text` (Search, Select, Add, Delete).
- 📈 **Real-time Progress Monitoring**: Live progress bars and event logs using Server-Sent Events (SSE).
- 🖼️ **Built-in Gallery**: View downloaded images by position folder with lightbox preview.

---

## 📁 Directory & Output Structure

Downloaded images are organized into dedicated folders by position title:

```
d:\WorkingNa\TverKar-ImageScrapping\
├── app.py                      # Flask API backend server
├── config.py                   # Configuration loader
├── requirements.txt            # Python package dependencies
├── position.text               # Position titles list
├── scrapers/
│   ├── base_scraper.py         # Abstract base scraper class
│   ├── pinterest_scraper.py    # Pinterest scraper (pinterest-dl)
│   ├── google_scraper.py       # Google Images scraper (Playwright)
│   └── ai_generator.py         # AI image generator (Gemini / OpenAI)
├── templates/
│   └── index.html              # Admin Dashboard UI
├── static/
│   ├── css/style.css           # Dark theme glassmorphism stylesheet
│   └── js/app.js               # Frontend JavaScript
└── downloads/                  # Output directory (gitignored)
    ├── Production-line Worker/
    │   ├── 001.jpg
    │   ├── 002.jpg
    │   └── ...
    ├── Machine Operator/
    └── ...
```

---

## 🚀 Quick Start Guide

### Prerequisites
- Python **3.10+** (Tested on Python 3.12)
- Git

### Installation Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Phyrakset/image-scrapping.git
   cd image-scrapping
   ```

2. **Create and activate a virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate
     ```
   - **Linux / macOS**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright Chromium browser**:
   ```bash
   playwright install chromium
   ```

5. **Set up environment variables**:
   - Copy `.env.example` to `.env`:
     ```bash
     copy .env.example .env
     ```
   - (Optional) Edit `.env` to add your **Gemini API Key** or **OpenAI API Key** if you plan to use AI image generation:
     ```env
     GEMINI_API_KEY=your_gemini_api_key_here
     OPENAI_API_KEY=your_openai_api_key_here
     IMAGES_PER_POSITION=30
     SEARCH_SUFFIX=Single Person Asian
     DOWNLOAD_DELAY=2
     ```

---

## 🏃 Running the Application

1. **Start the Flask backend server**:
   ```bash
   python app.py
   ```

2. **Open the Web Admin Dashboard**:
   Navigate to **http://localhost:5000** in your browser.

---

## 📖 User Guide

### 1. Position Management (`/positions`)
- The app preloads position titles from `position.text`.
- Search for specific positions or select individual positions using checkboxes.
- Add new positions or delete existing ones directly from the UI.

### 2. Scraping Images (`/scrape`)
1. Select a download source:
   - **📌 Pinterest**: Direct search & download via API.
   - **🔍 Google Images**: Playwright browser search & high-res download.
   - **✨ AI Gemini**: Generate images using Google Imagen 3.
   - **🤖 AI OpenAI**: Generate images using OpenAI DALL-E 3.
2. Configure settings:
   - **Images per Position**: Set desired count (Default: `30`).
   - **Search Query Suffix**: Set keyword modifier (Default: `Single Person Asian`).
     - Example query: `"Production-line Worker Single Person Asian"`
3. Click **▶️ Start Scraping**.
4. Track live downloading progress and event logs.

### 3. Gallery & Preview (`/gallery`)
- Browse downloaded images grouped into position folders.
- Click any image to view it full-screen in a lightbox preview.

---

## ⚠️ Notes & Disclaimer

- **Anti-Bot & Rate Limits**: Automated web scraping must comply with platform Terms of Service. Use reasonable download delays to avoid rate limits or IP blocks.
- **Educational / Personal Use**: This tool is created for educational and internal dataset collection purposes.

---

## 📄 License

MIT License.
