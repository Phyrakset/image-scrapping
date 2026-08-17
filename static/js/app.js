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
    posFilter: 'all', // 'all', 'complete', 'incomplete'
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

    getPositions: (target = 40) => API.get(`/api/positions?target=${target}`),
    addPosition: (name) => API.post('/api/positions', { name }),
    deletePosition: (id) => API.del(`/api/positions/${id}`),
    getStats: () => API.get('/api/stats'),
    getSettings: () => API.get('/api/settings'),
    updateSettings: (data) => API.post('/api/settings', data),
    startScrape: (data) => API.post('/api/scrape/start', data),
    stopScrape: () => API.post('/api/scrape/stop'),
    getScrapeStatus: () => API.get('/api/scrape/status'),
    getDetectorStatus: () => API.get('/api/detector/status'),
    getLocalSDStatus: () => API.get('/api/local_sd/status'),
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
        const target = parseInt(document.getElementById('scrape-count')?.value || '40');
        const data = await API.getPositions(target);
        state.positions = data.positions || [];

        // Update counts in tabs
        const completeCnt = data.complete_total || 0;
        const incompleteCnt = data.incomplete_total || 0;

        if (document.getElementById('cnt-filter-all')) document.getElementById('cnt-filter-all').textContent = state.positions.length;
        if (document.getElementById('cnt-filter-complete')) document.getElementById('cnt-filter-complete').textContent = completeCnt;
        if (document.getElementById('cnt-filter-incomplete')) document.getElementById('cnt-filter-incomplete').textContent = incompleteCnt;

        renderPositions();
    } catch (err) {
        console.error('Positions load error:', err);
    }
}

function setPosFilter(filter) {
    state.posFilter = filter;
    ['all', 'complete', 'incomplete'].forEach(f => {
        const btn = document.getElementById(`tab-filter-${f}`);
        if (btn) btn.classList.toggle('active', f === filter);
    });
    renderPositions();
}

function renderPositions(searchFilter = '') {
    const list = document.getElementById('position-list');
    if (!list) return;

    const targetCount = parseInt(document.getElementById('scrape-count')?.value || '40');

    let filtered = state.positions;

    // Apply search filter
    if (searchFilter) {
        filtered = filtered.filter(p => p.name.toLowerCase().includes(searchFilter.toLowerCase()));
    }

    // Apply tab filter
    if (state.posFilter === 'complete') {
        filtered = filtered.filter(p => p.images_downloaded >= targetCount);
    } else if (state.posFilter === 'incomplete') {
        filtered = filtered.filter(p => p.images_downloaded < targetCount);
    }

    if (filtered.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <p>${searchFilter ? 'No positions match your search' : 'No positions found for this filter'}</p>
            </div>`;
        return;
    }

    list.innerHTML = filtered.map(pos => {
        const count = pos.images_downloaded || 0;
        const isInc = count < targetCount;
        const missing = Math.max(0, targetCount - count);

        return `
        <div class="position-item ${isInc ? 'is-incomplete' : ''}" data-id="${pos.id}">
            <input type="checkbox" ${state.selectedPositions.has(pos.id) ? 'checked' : ''}
                   onchange="togglePosition(${pos.id})" />
            <span class="pos-name">${escapeHtml(pos.name)}</span>
            <span class="pos-count ${count > 0 ? (isInc ? 'has-images incomplete-badge' : 'has-images') : ''}">
                ${count > 0 ? `📷 ${count}/${targetCount}` : `0/${targetCount}`}
                ${isInc ? ` <span style="color:#f59e0b;font-weight:bold;margin-left:4px;">(Missing ${missing})</span>` : ''}
            </span>
            <button class="pos-delete" onclick="deletePosition(${pos.id}, '${escapeHtml(pos.name)}')" title="Delete">
                🗑️
            </button>
        </div>
    `;
    }).join('');

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
    const searchFilter = document.getElementById('position-search')?.value || '';
    const targetCount = parseInt(document.getElementById('scrape-count')?.value || '40');

    let filtered = state.positions;
    if (searchFilter) {
        filtered = filtered.filter(p => p.name.toLowerCase().includes(searchFilter.toLowerCase()));
    }
    if (state.posFilter === 'complete') {
        filtered = filtered.filter(p => p.images_downloaded >= targetCount);
    } else if (state.posFilter === 'incomplete') {
        filtered = filtered.filter(p => p.images_downloaded < targetCount);
    }

    filtered.forEach(p => state.selectedPositions.add(p.id));
    renderPositions(searchFilter);
}

function selectIncompletePositions() {
    const targetCount = parseInt(document.getElementById('scrape-count')?.value || '40');
    state.selectedPositions.clear();

    const incomplete = state.positions.filter(p => (p.images_downloaded || 0) < targetCount);
    incomplete.forEach(p => state.selectedPositions.add(p.id));

    setPosFilter('incomplete');
    showToast(`Selected ${incomplete.length} positions with < ${targetCount} images`, 'info');
}

function selectIncompleteForScrape() {
    selectIncompletePositions();
    navigateTo('scrape');
}

function deselectAllPositions() {
    state.selectedPositions.clear();
    const searchFilter = document.getElementById('position-search')?.value || '';
    renderPositions(searchFilter);
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
    const target = parseInt(document.getElementById('scrape-count')?.value || '40');
    const data = await API.getPositions(target);
    state.positions = data.positions || [];

    // Load active detector status
    try {
        const detector = await API.getDetectorStatus();
        const badge = document.getElementById('lbl-active-vision-engine');
        if (badge) {
            badge.textContent = detector.active_engine || 'Free Vision (Auto)';
        }
        if (document.getElementById('scrape-only-ai') && typeof detector.only_ai_person === 'boolean') {
            document.getElementById('scrape-only-ai').checked = detector.only_ai_person;
        }
    } catch (e) {
        console.error('Detector status error:', e);
    }

    updateScrapeUI();
    checkScrapeStatus();
}

function onScrapeCountChange() {
    const count = parseInt(document.getElementById('scrape-count')?.value || '40');
    document.querySelectorAll('.lbl-target-count').forEach(el => el.textContent = count);
    loadPositions();
    updateScrapeUI();
}

function selectSource(source) {
    state.selectedSource = source;
    document.querySelectorAll('.source-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.source === source);
    });

    // Toggle Local SD Model Selector
    const modelGroup = document.getElementById('local-sd-model-group');
    if (modelGroup) {
        modelGroup.style.display = (source === 'ai_local_sd') ? 'block' : 'none';
    }
}

const modelDescriptions = {
    'majicmix': '💡 <b>MajicMIX Realistic v7:</b> Top specialized model for natural Asian skin, authentic facial features, and realistic worker uniforms.',
    'flux_schnell': '💡 <b>FLUX.1 [schnell]:</b> 12B Flow Transformer (World #1). Flawless hands, lifelike anatomy, and DSLR realism.',
    'realvisxl': '💡 <b>RealVisXL:</b> Gold standard for studio lighting and DSLR portraits (1024x1024).',
    'juggernaut': '💡 <b>Juggernaut XL:</b> Specialist for workplace settings, uniforms, factory/office environments, and tools (1024x1024).',
    'realistic_vision': '💡 <b>Realistic Vision v6.0:</b> Ultra-fast photorealism generating crisp portraits in just 2–4 seconds (512x512).',
    'epicrealism': '💡 <b>EpiCRealism:</b> Candid documentary-style workplace photography with authentic natural lighting.'
};

function onModelSelectChange() {
    const val = document.getElementById('local-sd-model')?.value || 'realvisxl';
    const descEl = document.getElementById('model-desc-text');
    if (descEl && modelDescriptions[val]) {
        descEl.innerHTML = modelDescriptions[val];
    }
}

async function startScrape() {
    const count = parseInt(document.getElementById('scrape-count')?.value || '40');
    const searchSuffix = document.getElementById('scrape-suffix')?.value?.trim() ?? 'Single Person Asian';
    const topUp = document.getElementById('scrape-top-up')?.checked ?? true;
    const onlyAiPerson = document.getElementById('scrape-only-ai')?.checked ?? true;

    const positionIds = state.selectedPositions.size > 0
        ? Array.from(state.selectedPositions)
        : state.positions.map(p => p.id);

    if (positionIds.length === 0) {
        showToast('No positions selected. Select positions first.', 'error');
        return;
    }

    try {
        const localSdModel = document.getElementById('local-sd-model')?.value || 'realvisxl';
        const result = await API.startScrape({
            source: state.selectedSource,
            local_sd_model: localSdModel,
            positions: positionIds,
            count: count,
            search_suffix: searchSuffix,
            top_up: topUp,
            only_ai_person: onlyAiPerson,
        });

        if (result.error) {
            showToast(result.error, 'error');
            return;
        }

        const filterNotice = onlyAiPerson ? ' [🤖 AI Person Filter ON]' : '';
        showToast(`Started scraping ${result.positions_count} positions via ${state.selectedSource}${filterNotice}`, 'success');
        addLog(`Started ${state.selectedSource} scraping for ${result.positions_count} positions (top_up=${topUp}, only_ai_person=${onlyAiPerson})`, 'info');
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
            ${progress.filtered ? `<span style="color:#c084fc;font-weight:600;">🤖 Real Photos Filtered: ${progress.filtered}</span>` : ''}
            <span>Status: ${progress.status.toUpperCase()}</span>
        </div>
        ${progress.message ? `<div class="progress-message">${escapeHtml(progress.message)}</div>` : ''}
    `;
}

function updateScrapeUI() {
    const posInfo = document.getElementById('scrape-pos-info');
    if (!posInfo) return;

    const targetCount = parseInt(document.getElementById('scrape-count')?.value || '40');
    const selectedList = state.selectedPositions.size > 0
        ? state.positions.filter(p => state.selectedPositions.has(p.id))
        : state.positions;

    const incompleteList = selectedList.filter(p => (p.images_downloaded || 0) < targetCount);
    const totalMissing = incompleteList.reduce((sum, p) => sum + Math.max(0, targetCount - (p.images_downloaded || 0)), 0);

    if (state.selectedPositions.size > 0) {
        if (incompleteList.length > 0) {
            posInfo.innerHTML = `
                <span style="color:#f59e0b;font-weight:600;">
                    ${state.selectedPositions.size} positions selected — ${incompleteList.length} incomplete (${totalMissing} missing images total)
                </span>
            `;
        } else {
            posInfo.innerHTML = `
                <span style="color:var(--accent-cyan);font-weight:500;">
                    ${state.selectedPositions.size} positions selected (all complete with ${targetCount}+ images)
                </span>
            `;
        }
    } else {
        posInfo.innerHTML = `
            <span>All ${state.positions.length} positions (${incompleteList.length} incomplete, ${totalMissing} missing images total)</span>
        `;
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
        if (document.getElementById('setting-only-ai')) {
            document.getElementById('setting-only-ai').checked = settings.only_ai_person ?? false;
        }
        if (document.getElementById('setting-local-sd-url')) {
            document.getElementById('setting-local-sd-url').value = settings.local_sd_url || 'http://127.0.0.1:7860';
        }
        document.getElementById('setting-delay').value = settings.download_delay || 2;

        const detector = await API.getDetectorStatus();
        const engineEl = document.getElementById('settings-vision-engine');
        if (engineEl) {
            engineEl.textContent = detector.active_engine || 'Free Vision (Auto)';
        }

        checkLocalSDStatus();
    } catch (err) {
        console.error('Settings load error:', err);
    }
}

async function checkLocalSDStatus() {
    const el = document.getElementById('settings-local-sd-status');
    if (!el) return;
    el.textContent = 'Checking...';
    el.style.color = 'var(--text-muted)';
    try {
        const res = await API.getLocalSDStatus();
        el.textContent = res.status;
        el.style.color = res.online ? '#4ade80' : '#f87171';
    } catch (e) {
        el.textContent = 'Offline';
        el.style.color = '#f87171';
    }
}

async function saveSettings() {
    const data = {
        gemini_api_key: document.getElementById('setting-gemini-key').value,
        openai_api_key: document.getElementById('setting-openai-key').value,
        images_per_position: parseInt(document.getElementById('setting-images-count').value),
        search_suffix: document.getElementById('setting-suffix')?.value || 'Single Person Asian',
        only_ai_person: document.getElementById('setting-only-ai')?.checked ?? false,
        local_sd_url: document.getElementById('setting-local-sd-url')?.value || 'http://127.0.0.1:7860',
        download_delay: parseInt(document.getElementById('setting-delay').value),
    };

    try {
        await API.updateSettings(data);
        showToast('Settings saved!', 'success');
        loadSettings();
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
