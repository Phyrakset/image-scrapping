/**
 * TverKar Image Scrapping — Admin Dashboard Frontend
 */

// ============================================================
// State
// ============================================================
const state = {
    currentPage: 'dashboard',
    positions: [],
    selectedPositions: new Set(),
    selectedSource: 'pinterest',
    stats: {},
    scrapeStatus: null,
    eventSource: null,
    galleryPosition: null,
    logs: [],
};

// ============================================================
// API
// ============================================================
const API = {
    async get(url) {
        const res = await fetch(url);
        return res.json();
    },
    async post(url, data) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return res.json();
    },
    async del(url) {
        const res = await fetch(url, { method: 'DELETE' });
        return res.json();
    },

    getPositions: () => API.get('/api/positions'),
    addPosition: (name) => API.post('/api/positions', { name }),
    deletePosition: (id) => API.del(`/api/positions/${id}`),
    getStats: () => API.get('/api/stats'),
    getSettings: () => API.get('/api/settings'),
    updateSettings: (data) => API.post('/api/settings', data),
    startScrape: (data) => API.post('/api/scrape/start', data),
    stopScrape: () => API.post('/api/scrape/stop'),
    getScrapeStatus: () => API.get('/api/scrape/status'),
    getImages: () => API.get('/api/images'),
    getImagesForPosition: (pos) => API.get(`/api/images/${encodeURIComponent(pos)}`),
};

// ============================================================
// Navigation
// ============================================================
function navigateTo(page) {
    state.currentPage = page;

    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.page === page);
    });

    // Show correct section
    document.querySelectorAll('.page-section').forEach(section => {
        section.classList.toggle('active', section.id === `page-${page}`);
    });

    // Load page data
    switch (page) {
        case 'dashboard': loadDashboard(); break;
        case 'positions': loadPositions(); break;
        case 'scrape': loadScrapePanel(); break;
        case 'gallery': loadGallery(); break;
        case 'settings': loadSettings(); break;
    }
}

// ============================================================
// Dashboard
// ============================================================
async function loadDashboard() {
    try {
        const stats = await API.getStats();
        state.stats = stats;

        document.getElementById('stat-positions').textContent = stats.total_positions || 0;
        document.getElementById('stat-images').textContent = stats.total_images || 0;
        document.getElementById('stat-folders').textContent = stats.positions_with_images || 0;

        const statusEl = document.getElementById('stat-status');
        statusEl.textContent = (stats.scraper_status || 'idle').toUpperCase();

        updateStatusBadge(stats.scraper_status || 'idle');
    } catch (err) {
        console.error('Dashboard load error:', err);
    }
}

function updateStatusBadge(status) {
    const badge = document.getElementById('global-status');
    if (!badge) return;
    badge.className = `status-badge ${status}`;
    badge.querySelector('.status-text').textContent = status.toUpperCase();
}

// ============================================================
// Positions
// ============================================================
async function loadPositions() {
    try {
        const data = await API.getPositions();
        state.positions = data.positions || [];
        renderPositions();
    } catch (err) {
        console.error('Positions load error:', err);
    }
}

function renderPositions(filter = '') {
    const list = document.getElementById('position-list');
    if (!list) return;

    const filtered = filter
        ? state.positions.filter(p => p.name.toLowerCase().includes(filter.toLowerCase()))
        : state.positions;

    if (filtered.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <p>${filter ? 'No positions match your search' : 'No positions found'}</p>
            </div>`;
        return;
    }

    list.innerHTML = filtered.map(pos => `
        <div class="position-item" data-id="${pos.id}">
            <input type="checkbox" ${state.selectedPositions.has(pos.id) ? 'checked' : ''}
                   onchange="togglePosition(${pos.id})" />
            <span class="pos-name">${escapeHtml(pos.name)}</span>
            <span class="pos-count ${pos.images_downloaded > 0 ? 'has-images' : ''}">
                ${pos.images_downloaded > 0 ? `📷 ${pos.images_downloaded}` : '0 images'}
            </span>
            <button class="pos-delete" onclick="deletePosition(${pos.id}, '${escapeHtml(pos.name)}')" title="Delete">
                🗑️
            </button>
        </div>
    `).join('');

    updateSelectCount();
}

function togglePosition(id) {
    if (state.selectedPositions.has(id)) {
        state.selectedPositions.delete(id);
    } else {
        state.selectedPositions.add(id);
    }
    updateSelectCount();
}

function selectAllPositions() {
    const filter = document.getElementById('position-search')?.value || '';
    const filtered = filter
        ? state.positions.filter(p => p.name.toLowerCase().includes(filter.toLowerCase()))
        : state.positions;
    filtered.forEach(p => state.selectedPositions.add(p.id));
    renderPositions(filter);
}

function deselectAllPositions() {
    state.selectedPositions.clear();
    const filter = document.getElementById('position-search')?.value || '';
    renderPositions(filter);
}

function updateSelectCount() {
    const countEl = document.getElementById('select-count');
    if (countEl) {
        countEl.textContent = `${state.selectedPositions.size} of ${state.positions.length} selected`;
    }
}

async function addPosition() {
    const input = document.getElementById('new-position-input');
    const name = input?.value?.trim();
    if (!name) return;

    try {
        const result = await API.addPosition(name);
        if (result.error) {
            showToast(result.error, 'error');
        } else {
            showToast(`Added: ${name}`, 'success');
            input.value = '';
            loadPositions();
        }
    } catch (err) {
        showToast('Failed to add position', 'error');
    }
}

async function deletePosition(id, name) {
    if (!confirm(`Delete position "${name}"?`)) return;

    try {
        await API.deletePosition(id);
        showToast(`Deleted: ${name}`, 'success');
        state.selectedPositions.delete(id);
        loadPositions();
    } catch (err) {
        showToast('Failed to delete position', 'error');
    }
}

// ============================================================
// Scraping
// ============================================================
async function loadScrapePanel() {
    if (state.positions.length === 0) {
        const data = await API.getPositions();
        state.positions = data.positions || [];
    }
    updateScrapeUI();
    checkScrapeStatus();
}

function selectSource(source) {
    state.selectedSource = source;
    document.querySelectorAll('.source-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.source === source);
    });
}

async function startScrape() {
    const count = parseInt(document.getElementById('scrape-count')?.value || '30');
    const searchSuffix = document.getElementById('scrape-suffix')?.value?.trim() ?? 'Single Person Asian';
    const positionIds = state.selectedPositions.size > 0
        ? Array.from(state.selectedPositions)
        : state.positions.map(p => p.id);

    if (positionIds.length === 0) {
        showToast('No positions selected. Select positions first.', 'error');
        return;
    }

    try {
        const result = await API.startScrape({
            source: state.selectedSource,
            positions: positionIds,
            count: count,
            search_suffix: searchSuffix,
        });

        if (result.error) {
            showToast(result.error, 'error');
            return;
        }

        showToast(`Started scraping ${positionIds.length} positions via ${state.selectedSource}`, 'success');
        addLog(`Started ${state.selectedSource} scraping for ${positionIds.length} positions with suffix '${searchSuffix}'`, 'info');
        startProgressStream();
    } catch (err) {
        showToast('Failed to start scraping', 'error');
    }
}


async function stopScrape() {
    try {
        await API.stopScrape();
        showToast('Stop signal sent', 'info');
        addLog('Stop requested', 'error');
    } catch (err) {
        showToast('Failed to stop scraping', 'error');
    }
}

function startProgressStream() {
    // Close existing stream
    if (state.eventSource) {
        state.eventSource.close();
    }

    state.eventSource = new EventSource('/api/scrape/stream');

    state.eventSource.onmessage = (event) => {
        const progress = JSON.parse(event.data);
        state.scrapeStatus = progress;
        updateProgressUI(progress);

        if (['completed', 'error', 'stopped'].includes(progress.status)) {
            state.eventSource.close();
            state.eventSource = null;
            addLog(`Scraping ${progress.status}: ${progress.message}`, progress.status === 'completed' ? 'success' : 'error');
            loadDashboard();
        }
    };

    state.eventSource.onerror = () => {
        state.eventSource.close();
        state.eventSource = null;
    };
}

async function checkScrapeStatus() {
    try {
        const status = await API.getScrapeStatus();
        state.scrapeStatus = status;
        updateProgressUI(status);

        if (status.status === 'running') {
            startProgressStream();
        }
    } catch (err) {
        console.error('Status check error:', err);
    }
}

function updateProgressUI(progress) {
    updateStatusBadge(progress.status);

    const container = document.getElementById('progress-section');
    if (!container) return;

    const isRunning = progress.status === 'running';
    const posPercent = progress.positions_total > 0
        ? Math.round((progress.positions_done / progress.positions_total) * 100) : 0;
    const imgPercent = progress.total_images > 0
        ? Math.round((progress.current_image / progress.total_images) * 100) : 0;

    document.getElementById('btn-start').disabled = isRunning;
    document.getElementById('btn-stop').disabled = !isRunning;

    container.innerHTML = `
        <div class="progress-container">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                <span style="font-weight:600;font-size:0.9rem;">Positions Progress</span>
                <span style="color:var(--accent-cyan);font-weight:600;">${progress.positions_done}/${progress.positions_total}</span>
            </div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: ${posPercent}%"></div>
            </div>
        </div>
        ${progress.current_position ? `
        <div class="progress-container" style="margin-top:12px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                <span style="font-weight:500;font-size:0.85rem;">Current: ${escapeHtml(progress.current_position)}</span>
                <span style="color:var(--text-secondary);font-size:0.85rem;">${progress.current_image}/${progress.total_images}</span>
            </div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: ${imgPercent}%"></div>
            </div>
        </div>` : ''}
        <div class="progress-info">
            <span>✅ Downloaded: ${progress.downloaded}</span>
            <span>❌ Failed: ${progress.failed}</span>
            <span>Status: ${progress.status.toUpperCase()}</span>
        </div>
        ${progress.message ? `<div class="progress-message">${escapeHtml(progress.message)}</div>` : ''}
    `;
}

function updateScrapeUI() {
    const posInfo = document.getElementById('scrape-pos-info');
    if (posInfo) {
        const count = state.selectedPositions.size || state.positions.length;
        posInfo.textContent = state.selectedPositions.size > 0
            ? `${count} positions selected`
            : `All ${count} positions (none selected)`;
    }
}

// ============================================================
// Gallery
// ============================================================
async function loadGallery() {
    const container = document.getElementById('gallery-content');
    if (!container) return;

    if (state.galleryPosition) {
        await loadGalleryImages(state.galleryPosition);
        return;
    }

    try {
        const images = await API.getImages();
        const folders = Object.entries(images);

        if (folders.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🖼️</div>
                    <p>No images downloaded yet. Go to Scrape to start downloading!</p>
                </div>`;
            return;
        }

        container.innerHTML = `
            <div class="folder-grid">
                ${folders.map(([name, info]) => `
                    <div class="folder-card" onclick="openFolder('${escapeAttr(name)}')">
                        <div class="folder-icon">📁</div>
                        <div class="folder-name">${escapeHtml(name)}</div>
                        <div class="folder-count">${info.count} images</div>
                    </div>
                `).join('')}
            </div>`;
    } catch (err) {
        console.error('Gallery load error:', err);
        container.innerHTML = '<div class="empty-state"><p>Failed to load gallery</p></div>';
    }
}

async function openFolder(position) {
    state.galleryPosition = position;

    const container = document.getElementById('gallery-content');
    const header = document.getElementById('gallery-header');
    if (!container) return;

    header.innerHTML = `
        <h3>
            <span class="icon">🖼️</span>
            <button class="btn btn-sm btn-secondary" onclick="backToGallery()" style="margin-right:8px;">← Back</button>
            ${escapeHtml(position)}
        </h3>
    `;

    try {
        const data = await API.getImagesForPosition(position);

        if (!data.images || data.images.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>No images in this folder</p></div>';
            return;
        }

        container.innerHTML = `
            <div class="gallery-grid">
                ${data.images.map(img => `
                    <div class="gallery-item" onclick="openLightbox('${escapeAttr(img.url)}')">
                        <img src="${img.url}" alt="${escapeAttr(img.name)}" loading="lazy" />
                        <div class="overlay">${escapeHtml(img.name)}</div>
                    </div>
                `).join('')}
            </div>`;
    } catch (err) {
        container.innerHTML = '<div class="empty-state"><p>Failed to load images</p></div>';
    }
}

function backToGallery() {
    state.galleryPosition = null;
    document.getElementById('gallery-header').innerHTML = '<h3><span class="icon">🖼️</span> Image Gallery</h3>';
    loadGallery();
}

function openLightbox(url) {
    const lightbox = document.getElementById('lightbox');
    const img = document.getElementById('lightbox-img');
    img.src = url;
    lightbox.classList.add('show');
}

function closeLightbox() {
    document.getElementById('lightbox').classList.remove('show');
}

// ============================================================
// Settings
// ============================================================
async function loadSettings() {
    try {
        const settings = await API.getSettings();
        document.getElementById('setting-gemini-key').value = settings.gemini_api_key || '';
        document.getElementById('setting-openai-key').value = settings.openai_api_key || '';
        document.getElementById('setting-images-count').value = settings.images_per_position || 30;
        if (document.getElementById('setting-suffix')) {
            document.getElementById('setting-suffix').value = settings.search_suffix || 'Single Person Asian';
        }
        document.getElementById('setting-delay').value = settings.download_delay || 2;
    } catch (err) {
        console.error('Settings load error:', err);
    }
}

async function saveSettings() {
    const data = {
        gemini_api_key: document.getElementById('setting-gemini-key').value,
        openai_api_key: document.getElementById('setting-openai-key').value,
        images_per_position: parseInt(document.getElementById('setting-images-count').value),
        search_suffix: document.getElementById('setting-suffix')?.value || 'Single Person Asian',
        download_delay: parseInt(document.getElementById('setting-delay').value),
    };

    try {
        await API.updateSettings(data);
        showToast('Settings saved!', 'success');
    } catch (err) {
        showToast('Failed to save settings', 'error');
    }
}


// ============================================================
// Logs
// ============================================================
function addLog(message, type = 'info') {
    const now = new Date().toLocaleTimeString();
    state.logs.unshift({ time: now, message, type });
    if (state.logs.length > 100) state.logs.pop();
    renderLogs();
}

function renderLogs() {
    const panel = document.getElementById('log-panel');
    if (!panel) return;

    panel.innerHTML = state.logs.map(log => `
        <div class="log-line">
            <span class="log-time">[${log.time}]</span>
            <span class="log-text ${log.type}">${escapeHtml(log.message)}</span>
        </div>
    `).join('');
}

// ============================================================
// Toast
// ============================================================
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
        <span>${escapeHtml(message)}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ============================================================
// Utilities
// ============================================================
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function escapeAttr(str) {
    return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

// ============================================================
// Init
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    // Nav click handlers
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => navigateTo(item.dataset.page));
    });

    // Lightbox close
    document.getElementById('lightbox')?.addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeLightbox();
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeLightbox();
    });

    // Initial load
    navigateTo('dashboard');
    addLog('Dashboard loaded', 'success');
});
