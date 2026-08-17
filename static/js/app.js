/**
 * TverKar Image Scrapping — Main Frontend Logic
 */

// State Management
const state = {
    currentPage: 'dashboard',
    selectedSource: 'ai_local_sd',
    positions: [],
    selectedPositions: new Set(),
    galleryPosition: null,
    gallerySort: 'recent',
    galleryData: {},
    logs: [],
    stats: {},
    scrapeStatus: { status: 'idle' },
    eventSource: null,
};

// API Client
const API = {
    async getPositions(target) {
        const url = target ? `/api/positions?target=${target}` : '/api/positions';
        const res = await fetch(url);
        return res.json();
    },

    async addPosition(name) {
        const res = await fetch('/api/positions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name }),
        });
        return res.json();
    },

    async deletePosition(id) {
        const res = await fetch(`/api/positions/${id}`, { method: 'DELETE' });
        return res.json();
    },

    async startScrape(options) {
        const res = await fetch('/api/scrape/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(options),
        });
        return res.json();
    },

    async stopScrape() {
        const res = await fetch('/api/scrape/stop', { method: 'POST' });
        return res.json();
    },

    async getScrapeStatus() {
        const res = await fetch('/api/scrape/status');
        return res.json();
    },

    async getImages() {
        const res = await fetch('/api/images');
        return res.json();
    },

    async getImagesForPosition(position) {
        const res = await fetch(`/api/images/${encodeURIComponent(position)}`);
        return res.json();
    },

    async getSettings() {
        const res = await fetch('/api/settings');
        return res.json();
    },

    async updateSettings(settings) {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings),
        });
        return res.json();
    },

    async getStats() {
        const res = await fetch('/api/stats');
        return res.json();
    },

    async getDetectorStatus() {
        const res = await fetch('/api/detector/status');
        return res.json();
    },

    async getLocalSDStatus() {
        const res = await fetch('/api/local_sd/status');
        return res.json();
    },
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

    // Update sections
    document.querySelectorAll('.page-section').forEach(sec => {
        sec.classList.remove('active');
    });

    const activeSection = document.getElementById(`page-${page}`);
    if (activeSection) {
        activeSection.classList.add('active');
    }

    // Trigger page-specific loads
    if (page === 'dashboard') loadDashboard();
    if (page === 'positions') loadPositions();
    if (page === 'scrape') loadScrapePage();
    if (page === 'gallery') loadGallery();
    if (page === 'settings') loadSettings();
}

// ============================================================
// Dashboard
// ============================================================
async function loadDashboard() {
    try {
        const stats = await API.getStats();
        state.stats = stats;

        const elPos = document.getElementById('stat-positions') || document.getElementById('stat-total-positions');
        const elImg = document.getElementById('stat-images') || document.getElementById('stat-total-images');
        const elFolders = document.getElementById('stat-folders') || document.getElementById('stat-positions-with-images');

        if (elPos) elPos.textContent = stats.total_positions ?? 0;
        if (elImg) elImg.textContent = stats.total_images ?? 0;
        if (elFolders) elFolders.textContent = stats.positions_with_images ?? 0;

        updateStatusBadge(stats.scraper_status || 'idle');
    } catch (err) {
        console.error('Dashboard load error:', err);
    }
}

function updateStatusBadge(status) {
    const badge = document.getElementById('stat-status') || document.getElementById('stat-scraper-status');
    if (!badge) return;

    badge.className = `stat-value status-badge ${status}`;
    const labels = {
        idle: 'IDLE',
        running: 'RUNNING',
        paused: 'PAUSED',
        completed: 'COMPLETED',
        stopped: 'STOPPED',
        error: 'ERROR',
    };
    badge.textContent = labels[status] || status.toUpperCase();
}

// ============================================================
// Positions
// ============================================================
let currentPosFilter = 'all';

function setPosFilter(filter) {
    currentPosFilter = filter;
    ['all', 'complete', 'incomplete'].forEach(f => {
        const btn = document.getElementById(`tab-filter-${f}`);
        if (btn) btn.classList.toggle('active', f === filter);
    });
    const searchVal = document.getElementById('position-search')?.value || '';
    renderPositions(searchVal);
}

async function loadPositions() {
    const target = parseInt(document.getElementById('scrape-count')?.value || '40');
    try {
        const positions = await API.getPositions(target);
        state.positions = positions;
        const searchVal = document.getElementById('position-search')?.value || '';
        renderPositions(searchVal);
    } catch (err) {
        console.error('Positions load error:', err);
    }
}

function renderPositions(filter = '') {
    const container = document.getElementById('position-list');
    if (!container) return;

    const target = parseInt(document.getElementById('scrape-count')?.value || '40');
    const q = filter.toLowerCase().trim();

    let allFiltered = state.positions.filter(pos => {
        if (!q) return true;
        return pos.name.toLowerCase().includes(q);
    });

    const completeCount = state.positions.filter(p => p.is_complete).length;
    const incompleteCount = state.positions.filter(p => !p.is_complete).length;

    const cntAll = document.getElementById('cnt-filter-all');
    const cntComplete = document.getElementById('cnt-filter-complete');
    const cntIncomplete = document.getElementById('cnt-filter-incomplete');
    if (cntAll) cntAll.textContent = state.positions.length;
    if (cntComplete) cntComplete.textContent = completeCount;
    if (cntIncomplete) cntIncomplete.textContent = incompleteCount;

    let list = allFiltered;
    if (currentPosFilter === 'complete') {
        list = allFiltered.filter(p => p.is_complete);
    } else if (currentPosFilter === 'incomplete') {
        list = allFiltered.filter(p => !p.is_complete);
    }

    if (list.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🔍</div>
                <p>No positions match your filter</p>
            </div>`;
        updateSelectCount();
        return;
    }

    container.innerHTML = list.map(pos => {
        const isSelected = state.selectedPositions.has(pos.id);
        const count = pos.images_downloaded || 0;
        const isComplete = pos.is_complete;
        const missing = pos.missing_count || 0;

        let badgeHtml = '';
        if (isComplete) {
            badgeHtml = `<span class="badge" style="background:rgba(34,197,94,0.15);color:#4ade80;border:1px solid rgba(34,197,94,0.3);font-size:0.75rem;">✓ ${count} / ${target}</span>`;
        } else if (count > 0) {
            badgeHtml = `<span class="badge" style="background:rgba(245,158,11,0.15);color:#fbbf24;border:1px solid rgba(245,158,11,0.3);font-size:0.75rem;">⚠️ ${count} / ${target} (need ${missing})</span>`;
        } else {
            badgeHtml = `<span class="badge" style="background:rgba(239,68,68,0.15);color:#f87171;border:1px solid rgba(239,68,68,0.3);font-size:0.75rem;">0 / ${target} (need ${missing})</span>`;
        }

        return `
            <div class="position-item ${isSelected ? 'selected' : ''}" onclick="togglePosition(${pos.id})">
                <input type="checkbox" ${isSelected ? 'checked' : ''} onclick="event.stopPropagation(); togglePosition(${pos.id})" />
                <span class="position-name">${escapeHtml(pos.name)}</span>
                ${badgeHtml}
                <div class="position-actions" onclick="event.stopPropagation()">
                    <button class="btn btn-sm btn-secondary" onclick="quickViewGallery('${escapeAttr(pos.name)}')">📁 View</button>
                    <button class="btn btn-sm btn-danger" onclick="deletePosition(${pos.id})">🗑️</button>
                </div>
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
    const searchVal = document.getElementById('position-search')?.value || '';
    renderPositions(searchVal);
    updateScrapeUI();
}

function selectAllPositions() {
    state.positions.forEach(p => state.selectedPositions.add(p.id));
    const searchVal = document.getElementById('position-search')?.value || '';
    renderPositions(searchVal);
    updateScrapeUI();
}

function selectIncompletePositions() {
    state.selectedPositions.clear();
    state.positions.filter(p => !p.is_complete).forEach(p => state.selectedPositions.add(p.id));
    const searchVal = document.getElementById('position-search')?.value || '';
    renderPositions(searchVal);
    updateScrapeUI();
}

function deselectAllPositions() {
    state.selectedPositions.clear();
    const searchVal = document.getElementById('position-search')?.value || '';
    renderPositions(searchVal);
    updateScrapeUI();
}

function selectIncompleteForScrape() {
    const target = parseInt(document.getElementById('scrape-count')?.value || '40');
    state.selectedPositions.clear();
    state.positions.filter(p => (p.images_downloaded || 0) < target).forEach(p => state.selectedPositions.add(p.id));
    updateScrapeUI();
    showToast(`Selected ${state.selectedPositions.size} incomplete positions`, 'info');
}

function updateSelectCount() {
    const countEl = document.getElementById('select-count');
    if (countEl) {
        countEl.textContent = `${state.selectedPositions.size} of ${state.positions.length} selected`;
    }
}

async function addPosition() {
    const input = document.getElementById('new-position-input');
    const name = input.value.trim();
    if (!name) return;

    try {
        const result = await API.addPosition(name);
        if (result.error) {
            showToast(result.error, 'error');
            return;
        }
        input.value = '';
        showToast(`Added: ${name}`, 'success');
        loadPositions();
    } catch (err) {
        showToast('Failed to add position', 'error');
    }
}

async function deletePosition(id) {
    if (!confirm('Are you sure you want to delete this position?')) return;

    try {
        await API.deletePosition(id);
        state.selectedPositions.delete(id);
        showToast('Position deleted', 'success');
        loadPositions();
    } catch (err) {
        showToast('Failed to delete position', 'error');
    }
}

// ============================================================
// Scrape
// ============================================================
const modelDescriptions = {
    'majicmix': '💡 <b>MajicMIX Realistic v7:</b> Top specialized model for natural Asian skin, authentic facial features, and realistic worker uniforms.',
    'flux_schnell': '💡 <b>FLUX.1 [schnell]:</b> 12B Flow Transformer (World #1). Flawless hands, lifelike anatomy, and DSLR realism.',
    'realvisxl': '💡 <b>RealVisXL:</b> Gold standard for studio lighting and DSLR portraits (1024x1024).',
    'juggernaut': '💡 <b>Juggernaut XL:</b> Specialist for workplace settings, uniforms, factory/office environments, and tools (1024x1024).',
    'realistic_vision': '💡 <b>Realistic Vision v6.0:</b> Ultra-fast photorealism generating crisp portraits in just 2–4 seconds (512x512).',
    'epicrealism': '💡 <b>EpiCRealism:</b> Candid documentary-style workplace photography with authentic natural lighting.'
};

function onModelSelectChange() {
    const val = document.getElementById('local-sd-model')?.value || 'majicmix';
    const descEl = document.getElementById('model-desc-text');
    if (descEl && modelDescriptions[val]) {
        descEl.innerHTML = modelDescriptions[val];
    }
}

async function loadScrapePage() {
    await loadPositions();

    try {
        const detector = await API.getDetectorStatus();
        const badge = document.getElementById('lbl-active-vision-engine');
        if (badge) {
            badge.textContent = detector.active_engine;
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

    const modelGroup = document.getElementById('local-sd-model-group');
    if (modelGroup) {
        modelGroup.style.display = (source === 'ai_local_sd') ? 'block' : 'none';
    }
}

async function startScrape() {
    const count = parseInt(document.getElementById('scrape-count')?.value || '40');
    const searchSuffix = document.getElementById('scrape-suffix')?.value?.trim() ?? 'Single Person Asian';
    const topUp = document.getElementById('scrape-top-up')?.checked ?? true;
    const onlyAiPerson = document.getElementById('scrape-only-ai')?.checked ?? true;
    const localSdModel = document.getElementById('local-sd-model')?.value || 'majicmix';

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
        addLog(`Started scrape: ${result.positions_count} positions via ${state.selectedSource}${filterNotice}`, 'info');

        startProgressStream();
    } catch (err) {
        showToast('Failed to start scraping', 'error');
    }
}

async function stopScrape() {
    try {
        await API.stopScrape();
        showToast('Stopping scrape job...', 'info');
        addLog('Stopping scrape job...', 'warn');
    } catch (err) {
        showToast('Failed to stop scraping', 'error');
    }
}

function startProgressStream() {
    if (state.eventSource) {
        state.eventSource.close();
    }

    state.eventSource = new EventSource('/api/scrape/stream');

    state.eventSource.onmessage = (event) => {
        try {
            const progress = JSON.parse(event.data);
            state.scrapeStatus = progress;
            updateProgressUI(progress);

            if (progress.status === 'completed' || progress.status === 'stopped' || progress.status === 'error') {
                state.eventSource.close();
                state.eventSource = null;
                loadDashboard();
                loadPositions();
                if (progress.status === 'completed') {
                    showToast('Scraping completed successfully!', 'success');
                }
            }
        } catch (e) {
            console.error('SSE parse error:', e);
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

    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    if (btnStart) btnStart.disabled = isRunning;
    if (btnStop) btnStop.disabled = !isRunning;

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
        
        ${progress.current_position ? `
        <div style="margin-top:14px;padding:12px;background:linear-gradient(135deg, rgba(59,130,246,0.15), rgba(168,85,247,0.15));border:1px solid rgba(168,85,247,0.3);border-radius:8px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
            <div style="font-size:0.85rem;color:#e2e8f0;">
                📂 <b>Saved in:</b> <code style="color:var(--accent-cyan);background:rgba(0,0,0,0.3);padding:2px 6px;border-radius:4px;">downloads/${escapeHtml(progress.current_position)}/</code>
            </div>
            <div style="display:flex;gap:8px;">
                <button class="btn btn-sm btn-primary" onclick="quickViewGallery('${escapeAttr(progress.current_position)}')">
                    🖼️ View in Gallery
                </button>
                <a href="/api/download_zip/${encodeURIComponent(progress.current_position)}" class="btn btn-sm btn-secondary" style="text-decoration:none;">
                    ⬇️ Download ZIP
                </a>
            </div>
        </div>` : ''}
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
// Gallery System
// ============================================================
function quickViewGallery(position) {
    navigateTo('gallery');
    openFolder(position);
}

function setGallerySort(sortType) {
    state.gallerySort = sortType;
    document.querySelectorAll('#gallery-toolbar .filter-tabs button').forEach(b => {
        b.classList.toggle('active', b.id === `gallery-sort-${sortType}`);
    });
    renderGalleryFolders();
}

function filterGallery() {
    renderGalleryFolders();
}

async function loadGallery() {
    const container = document.getElementById('gallery-content');
    const toolbar = document.getElementById('gallery-toolbar');
    if (!container) return;

    if (state.galleryPosition) {
        if (toolbar) toolbar.style.display = 'none';
        await loadGalleryImages(state.galleryPosition);
        return;
    }

    if (toolbar) toolbar.style.display = 'block';

    try {
        const images = await API.getImages();
        state.galleryData = images;
        renderGalleryFolders();
    } catch (err) {
        console.error('Gallery load error:', err);
        container.innerHTML = '<div class="empty-state"><p>Failed to load gallery</p></div>';
    }
}

function renderGalleryFolders() {
    const container = document.getElementById('gallery-content');
    if (!container) return;

    const searchTerm = (document.getElementById('gallery-search')?.value || '').toLowerCase().trim();
    let entries = Object.entries(state.galleryData || {});

    if (entries.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🖼️</div>
                <p>No images downloaded yet. Go to Scrape Images to generate or download images!</p>
            </div>`;
        return;
    }

    // Filter by search
    if (searchTerm) {
        entries = entries.filter(([name]) => name.toLowerCase().includes(searchTerm));
    }

    // Sort entries
    if (state.gallerySort === 'recent') {
        entries.sort((a, b) => (b[1].mtime || 0) - (a[1].mtime || 0));
    } else if (state.gallerySort === 'name') {
        entries.sort((a, b) => a[0].localeCompare(b[0]));
    } else if (state.gallerySort === 'count') {
        entries.sort((a, b) => (b[1].count || 0) - (a[1].count || 0));
    }

    if (entries.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No positions match "${escapeHtml(searchTerm)}"</p>
            </div>`;
        return;
    }

    container.innerHTML = `
        <div class="folder-grid">
            ${entries.map(([name, info], idx) => {
                const isRecent = idx < 3 && state.gallerySort === 'recent';
                return `
                <div class="folder-card" style="position:relative;cursor:pointer;" onclick="openFolder('${escapeAttr(name)}')">
                    ${isRecent ? `<span style="position:absolute;top:8px;right:8px;font-size:0.7rem;background:rgba(168,85,247,0.3);color:#e9d5ff;padding:2px 6px;border-radius:10px;border:1px solid rgba(168,85,247,0.5);">✨ Recent</span>` : ''}
                    <div class="folder-icon">📁</div>
                    <div class="folder-name" style="font-weight:600;">${escapeHtml(name)}</div>
                    <div class="folder-count" style="color:var(--accent-cyan);font-size:0.85rem;">${info.count} images</div>
                    <div style="margin-top:8px;display:flex;gap:6px;width:100%;" onclick="event.stopPropagation()">
                        <a href="/api/download_zip/${encodeURIComponent(name)}" class="btn btn-sm btn-secondary" style="width:100%;text-align:center;font-size:0.75rem;padding:4px 8px;text-decoration:none;">
                            ⬇️ ZIP
                        </a>
                    </div>
                </div>
            `;}).join('')}
        </div>`;
}

async function openFolder(position) {
    state.galleryPosition = position;
    await loadGalleryImages(position);
}

async function loadGalleryImages(position) {
    const container = document.getElementById('gallery-content');
    const header = document.getElementById('gallery-header');
    const toolbar = document.getElementById('gallery-toolbar');
    if (toolbar) toolbar.style.display = 'none';
    if (!container) return;

    if (header) {
        header.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;width:100%;flex-wrap:wrap;gap:12px;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <button class="btn btn-sm btn-secondary" onclick="backToGallery()">← Back to All Folders</button>
                    <h3 style="margin:0;">📁 ${escapeHtml(position)}</h3>
                </div>
                <div style="display:flex;gap:8px;">
                    <button class="btn btn-sm btn-secondary" onclick="copyFolderPath('${escapeAttr(position)}')">📋 Copy Folder Path</button>
                    <a href="/api/download_zip/${encodeURIComponent(position)}" class="btn btn-sm btn-primary" style="text-decoration:none;">⬇️ Download All (.ZIP)</a>
                </div>
            </div>
        `;
    }

    try {
        const data = await API.getImagesForPosition(position);

        if (!data.images || data.images.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>No images in this folder</p></div>';
            return;
        }

        container.innerHTML = `
            <div style="margin-bottom:14px;padding:8px 12px;background:rgba(255,255,255,0.03);border-radius:6px;font-size:0.85rem;color:var(--text-muted);display:flex;align-items:center;justify-content:space-between;">
                <span>📂 <b>Disk Path:</b> <code id="disk-path-txt" style="color:var(--accent-cyan);">/home/jupyter/WORKINGNA/image-scrapping/downloads/${escapeHtml(position)}/</code></span>
                <span><b>${data.count}</b> images</span>
            </div>
            <div class="gallery-grid">
                ${data.images.map((img, idx) => `
                    <div class="gallery-item" onclick="openLightbox('${escapeAttr(img.url)}')">
                        <img src="${img.url}" alt="${escapeAttr(img.name)}" loading="lazy" />
                        <div class="overlay">
                            <span class="img-name">${escapeHtml(img.name)}</span>
                            <div class="overlay-actions">
                                <a href="${img.url}" download="${escapeAttr(img.name)}" class="btn btn-sm btn-primary" onclick="event.stopPropagation()">⬇️</a>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (err) {
        console.error('Folder load error:', err);
        container.innerHTML = '<div class="empty-state"><p>Failed to load images</p></div>';
    }
}

function backToGallery() {
    state.galleryPosition = null;
    const header = document.getElementById('gallery-header');
    if (header) {
        header.innerHTML = '<span class="icon">🖼️</span> Image Gallery';
    }
    loadGallery();
}

function copyFolderPath(position) {
    const fullPath = `/home/jupyter/WORKINGNA/image-scrapping/downloads/${position}/`;
    navigator.clipboard.writeText(fullPath).then(() => {
        showToast('📋 Copied full folder path to clipboard!', 'success');
    }).catch(() => {
        prompt('Folder Path:', fullPath);
    });
}

// Lightbox
function openLightbox(url) {
    const lightbox = document.getElementById('lightbox');
    const img = document.getElementById('lightbox-img');
    if (img && lightbox) {
        img.src = url;
        lightbox.classList.add('show');
    }
}

function closeLightbox() {
    const lightbox = document.getElementById('lightbox');
    if (lightbox) {
        lightbox.classList.remove('show');
    }
}

// ============================================================
// Settings
// ============================================================
async function loadSettings() {
    try {
        const settings = await API.getSettings();
        if (document.getElementById('setting-gemini-key')) {
            document.getElementById('setting-gemini-key').value = settings.gemini_api_key || '';
        }
        if (document.getElementById('setting-openai-key')) {
            document.getElementById('setting-openai-key').value = settings.openai_api_key || '';
        }
        if (document.getElementById('setting-images-count')) {
            document.getElementById('setting-images-count').value = settings.images_per_position || 30;
        }
        if (document.getElementById('setting-suffix')) {
            document.getElementById('setting-suffix').value = settings.search_suffix || 'Single Person Asian';
        }
        if (document.getElementById('setting-only-ai')) {
            document.getElementById('setting-only-ai').checked = settings.only_ai_person ?? false;
        }
        if (document.getElementById('setting-local-sd-url')) {
            document.getElementById('setting-local-sd-url').value = settings.local_sd_url || 'http://127.0.0.1:7860';
        }
        if (document.getElementById('setting-delay')) {
            document.getElementById('setting-delay').value = settings.download_delay || 3;
        }

        checkLocalSDStatus();
        checkDetectorEngine();
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
        if (res.status === 'ok') {
            el.textContent = `🟢 Connected (${res.checkpoint || 'Ready'})`;
            el.style.color = 'var(--accent-green)';
        } else {
            el.textContent = `🔴 Offline (${res.error || 'Cannot connect'})`;
            el.style.color = 'var(--accent-red)';
        }
    } catch (e) {
        el.textContent = '🔴 Offline';
        el.style.color = 'var(--accent-red)';
    }
}

async function checkDetectorEngine() {
    const el = document.getElementById('settings-vision-engine');
    if (!el) return;
    try {
        const res = await API.getDetectorStatus();
        el.textContent = res.active_engine;
    } catch (e) {
        el.textContent = 'Unknown';
    }
}

async function saveSettings() {
    const data = {
        gemini_api_key: document.getElementById('setting-gemini-key')?.value || '',
        openai_api_key: document.getElementById('setting-openai-key')?.value || '',
        images_per_position: parseInt(document.getElementById('setting-images-count')?.value || '30'),
        search_suffix: document.getElementById('setting-suffix')?.value || 'Single Person Asian',
        only_ai_person: document.getElementById('setting-only-ai')?.checked ?? false,
        local_sd_url: document.getElementById('setting-local-sd-url')?.value || 'http://127.0.0.1:7860',
        download_delay: parseInt(document.getElementById('setting-delay')?.value || '3'),
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
    if (!container) return;
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
    if (!str) return '';
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
