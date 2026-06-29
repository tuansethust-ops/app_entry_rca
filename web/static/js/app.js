/**
 * Core Application Logic (Navigation, File Browser, API Calls)
 */
const API_BASE = '/api';

const state = {
    currentJobId: null,
    backendMode: 'auto',
};

// Elements
const views = document.querySelectorAll('.view');
const navBtns = document.querySelectorAll('.nav-btn');

// Show Toast
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Navigation
function switchView(viewId) {
    views.forEach(v => v.classList.remove('active'));
    navBtns.forEach(b => b.classList.remove('active'));
    document.getElementById(`view-${viewId}`).classList.add('active');
    
    const btn = document.querySelector(`.nav-btn[data-view="${viewId}"]`);
    if (btn) btn.classList.add('active');

    if (viewId === 'jobs') loadJobs();
}

navBtns.forEach(btn => {
    btn.addEventListener('click', () => switchView(btn.dataset.view));
});

document.getElementById('btn-back-to-analyze').addEventListener('click', () => {
    switchView('analyze');
    state.currentJobId = null;
    resetLiveView();
});

// File Browser Modal
const modal = document.getElementById('modal-overlay');
const closeBtn = document.getElementById('modal-close');
const browserList = document.getElementById('browser-file-list');
const breadcrumb = document.getElementById('browser-breadcrumb');
const selectedText = document.getElementById('browser-selected');
const selectBtn = document.getElementById('browser-select-btn');

let currentBrowseTarget = null; // 'dut', 'ref', 'batch-dut', 'batch-ref'
let currentBrowsePath = '~';
let selectedPath = null;
let isDirSelection = false;

async function openBrowser(target, initialPath = '~') {
    currentBrowseTarget = target;
    isDirSelection = target.startsWith('batch');
    modal.classList.add('active');
    await loadDirectory(initialPath);
}

function closeBrowser() {
    modal.classList.remove('active');
    selectedPath = null;
}

closeBtn.addEventListener('click', closeBrowser);
modal.addEventListener('click', (e) => {
    if (e.target === modal) closeBrowser();
});

async function loadDirectory(path) {
    try {
        const res = await fetch(`${API_BASE}/browse?path=${encodeURIComponent(path)}`);
        const data = await res.json();
        
        if (!res.ok) throw new Error(data.error);

        currentBrowsePath = data.current;
        breadcrumb.textContent = data.current;
        browserList.innerHTML = '';
        selectedPath = null;
        updateSelectBtn();

        if (isDirSelection) {
            selectedPath = data.current;
            updateSelectBtn();
        }

        // Add Parent directory option
        if (data.parent) {
            const div = document.createElement('div');
            div.className = 'browser-item';
            div.innerHTML = `<span class="browser-item-icon">📁</span><span class="browser-item-name">..</span>`;
            div.onclick = () => loadDirectory(data.parent);
            browserList.appendChild(div);
        }

        data.items.forEach(item => {
            if (isDirSelection && !item.is_dir) return; // Only show dirs in batch mode

            const div = document.createElement('div');
            div.className = 'browser-item';
            const icon = item.is_dir ? '📁' : '📄';
            let size = item.size ? (item.size / 1024 / 1024).toFixed(2) + ' MB' : '';
            div.innerHTML = `
                <span class="browser-item-icon">${icon}</span>
                <span class="browser-item-name">${item.name}</span>
                <span class="browser-item-size">${size}</span>
            `;
            
            div.onclick = () => {
                if (item.is_dir) {
                    loadDirectory(item.path);
                } else {
                    document.querySelectorAll('.browser-item').forEach(el => el.classList.remove('selected'));
                    div.classList.add('selected');
                    selectedPath = item.path;
                    updateSelectBtn();
                }
            };
            browserList.appendChild(div);
        });
    } catch (e) {
        showToast(e.message, 'error');
    }
}

function updateSelectBtn() {
    if (selectedPath) {
        selectedText.textContent = selectedPath;
        selectBtn.disabled = false;
    } else {
        selectedText.textContent = isDirSelection ? currentBrowsePath : 'No file selected';
        selectBtn.disabled = !isDirSelection;
    }
}

selectBtn.addEventListener('click', () => {
    if (!selectedPath) return;
    
    if (currentBrowseTarget === 'dut') {
        document.getElementById('dut-path').value = selectedPath;
    } else if (currentBrowseTarget === 'ref') {
        document.getElementById('ref-path').value = selectedPath;
    } else if (currentBrowseTarget === 'batch-dut') {
        document.getElementById('batch-dut-dir').value = selectedPath;
    } else if (currentBrowseTarget === 'batch-ref') {
        document.getElementById('batch-ref-dir').value = selectedPath;
    }
    
    checkReadyState();
    closeBrowser();
});

// Attach browse buttons
document.getElementById('btn-browse-dut').addEventListener('click', () => openBrowser('dut'));
document.getElementById('btn-browse-ref').addEventListener('click', () => openBrowser('ref'));
document.getElementById('btn-browse-batch-dut').addEventListener('click', () => openBrowser('batch-dut'));
document.getElementById('btn-browse-batch-ref').addEventListener('click', () => openBrowser('batch-ref'));

// Form Validation
const dutInput = document.getElementById('dut-path');
const refInput = document.getElementById('ref-path');
const startBtn = document.getElementById('btn-start-analysis');

function checkReadyState() {
    startBtn.disabled = !(dutInput.value.trim() && refInput.value.trim());
}
dutInput.addEventListener('input', checkReadyState);
refInput.addEventListener('input', checkReadyState);

// Start Analysis
startBtn.addEventListener('click', async () => {
    const payload = {
        dut_path: dutInput.value.trim(),
        ref_path: refInput.value.trim(),
        target: document.getElementById('opt-target').value.trim(),
        backend: document.getElementById('opt-backend').value,
        options: {
            include_better_final: document.getElementById('opt-include-better').checked,
            include_correlation: document.getElementById('opt-include-correlation').checked
        }
    };

    try {
        startBtn.disabled = true;
        startBtn.innerHTML = 'Starting...';
        
        const res = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        if (!res.ok) throw new Error(data.error);

        state.currentJobId = data.job_id;
        showToast('Analysis started', 'success');
        
        // Setup Live View
        setupLiveView(data.job_id, payload.dut_path, payload.ref_path);
        switchView('live');
        
        // Connect WebSocket
        connectWebSocket(data.job_id);
        
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        startBtn.disabled = false;
        startBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Start Analysis';
    }
});

// Live View Functions
function setupLiveView(jobId, dut, ref) {
    document.getElementById('live-job-id').textContent = `ID: ${jobId}`;
    const dutName = dut.split(/[\\/]/).pop();
    const refName = ref.split(/[\\/]/).pop();
    document.getElementById('live-job-title').textContent = `${dutName} vs ${refName}`;
    
    // Reset Pipeline
    const skills = [
        "trace-ingestion", "launch-context", "trace-validation", "phase-localizer",
        "running-analysis", "runnable-analysis", "cpu-core-frequency", "wait-dependency",
        "block-io-analysis", "memory-gc-analysis", "art-runtime", "render-frame",
        "system-interference", "leaf-evaluator", "evidence-graph", "report-generator"
    ];
    
    const list = document.getElementById('pipeline-list');
    list.innerHTML = '';
    skills.forEach(s => {
        const div = document.createElement('div');
        div.className = 'pipeline-item pending';
        div.id = `skill-${s}`;
        div.innerHTML = `<span class="skill-icon">⏳</span><span class="skill-name">${s}</span><span class="skill-dur"></span>`;
        list.appendChild(div);
    });
    
    document.getElementById('log-output').innerHTML = '';
    updateProgress(0, 0, 16);
}

function resetLiveView() {
    document.getElementById('progress-bar').style.width = '0%';
    document.getElementById('progress-percent').textContent = '0%';
    document.getElementById('progress-detail').textContent = '0/0 skills';
    if(window.ws) window.ws.close();
}

function updateProgress(progress, completed, total) {
    const pct = Math.round(progress * 100);
    document.getElementById('progress-bar').style.width = `${pct}%`;
    document.getElementById('progress-percent').textContent = `${pct}%`;
    document.getElementById('progress-detail').textContent = `${completed}/${total} skills`;
}

document.getElementById('btn-clear-log').addEventListener('click', () => {
    document.getElementById('log-output').innerHTML = '';
});

document.getElementById('btn-cancel-job').addEventListener('click', async () => {
    if(state.currentJobId) {
        if(confirm("Are you sure you want to cancel and delete this job?")) {
            await fetch(`${API_BASE}/jobs/${state.currentJobId}`, { method: 'DELETE' });
            if(window.ws) window.ws.close();
            switchView('analyze');
            showToast('Job cancelled', 'warning');
        }
    }
});

// Jobs View
async function loadJobs() {
    try {
        const res = await fetch(`${API_BASE}/jobs`);
        const data = await res.json();
        
        const list = document.getElementById('jobs-list');
        list.innerHTML = '';
        
        if (data.jobs.length === 0) {
            list.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:2rem;">No jobs found</div>';
            return;
        }

        const table = document.createElement('table');
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Time</th>
                    <th>DUT File</th>
                    <th>REF File</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody></tbody>
        `;
        const tbody = table.querySelector('tbody');

        data.jobs.forEach(j => {
            const tr = document.createElement('tr');
            const dname = j.dut_path.split(/[\\/]/).pop();
            const rname = j.ref_path.split(/[\\/]/).pop();
            const time = new Date(j.created_at).toLocaleString();
            
            let statusHtml = `<span class="badge">${j.status}</span>`;
            if(j.status === 'COMPLETED') statusHtml = `<span class="badge success">✅ Done</span>`;
            if(j.status === 'FAILED') statusHtml = `<span class="badge error">❌ Failed</span>`;
            if(j.status === 'RUNNING') statusHtml = `<span class="badge warning">🔄 Running</span>`;

            tr.innerHTML = `
                <td>${time}</td>
                <td>${dname}</td>
                <td>${rname}</td>
                <td>${statusHtml}</td>
                <td>
                    <button class="btn-icon" onclick="viewJob('${j.id}')" title="View Report">👁️</button>
                    <button class="btn-icon" onclick="deleteJob('${j.id}')" title="Delete">🗑️</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
        list.appendChild(table);

    } catch (e) {
        showToast(e.message, 'error');
    }
}

document.getElementById('btn-refresh-jobs').addEventListener('click', loadJobs);

window.viewJob = async function(jobId) {
    state.currentJobId = jobId;
    const res = await fetch(`${API_BASE}/jobs/${jobId}`);
    const job = await res.json();
    if(job.status === 'COMPLETED') {
        renderReportDashboard(jobId);
    } else {
        showToast(`Job is ${job.status}`);
        if(job.status === 'RUNNING') {
            setupLiveView(jobId, job.dut_path, job.ref_path);
            switchView('live');
            connectWebSocket(jobId);
        }
    }
};

window.deleteJob = async function(jobId) {
    if(confirm("Delete this job permanently?")) {
        await fetch(`${API_BASE}/jobs/${jobId}`, { method: 'DELETE' });
        showToast('Job deleted');
        loadJobs();
    }
};

// Batch mode setup: Quick Scan & Smart Selection
let currentBatchPairs = [];

document.getElementById('btn-scan-folders').addEventListener('click', async () => {
    const dDir = document.getElementById('batch-dut-dir').value.trim();
    const rDir = document.getElementById('batch-ref-dir').value.trim();
    if(!dDir || !rDir) {
        showToast("Select both DUT and REF directories", "error");
        return;
    }
    
    const btn = document.getElementById('btn-scan-folders');
    btn.innerHTML = 'Scanning...';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/scan-folders`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ dut_dir: dDir, ref_dir: rDir })
        });
        const data = await res.json();
        if(!res.ok) throw new Error(data.error);

        // Populate Device Info
        document.getElementById('scan-dut-model').textContent = data.dut.model;
        document.getElementById('scan-dut-ram').textContent = data.dut.ram;
        document.getElementById('scan-dut-build').textContent = data.dut.build;
        document.getElementById('scan-dut-count').textContent = data.dut.total_files;

        document.getElementById('scan-ref-model').textContent = data.ref.model;
        document.getElementById('scan-ref-ram').textContent = data.ref.ram;
        document.getElementById('scan-ref-build').textContent = data.ref.build;
        document.getElementById('scan-ref-count').textContent = data.ref.total_files;

        // Populate Table
        currentBatchPairs = data.matched_apps;
        const tbody = document.getElementById('scan-apps-tbody');
        tbody.innerHTML = '';
        currentBatchPairs.forEach((pair, i) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><input type="checkbox" class="scan-app-cb" data-index="${i}" ${pair.selected ? 'checked' : ''}></td>
                <td style="font-weight:600; color:var(--text-main)">${pair.target}</td>
                <td class="mono" style="font-size:0.8rem; opacity:0.8">${pair.dut_file.split(/[\\/]/).pop()}</td>
                <td class="mono" style="font-size:0.8rem; opacity:0.8">${pair.ref_file.split(/[\\/]/).pop()}</td>
            `;
            tbody.appendChild(tr);
        });

        // Update selected count
        const updateCount = () => {
            const checked = document.querySelectorAll('.scan-app-cb:checked').length;
            document.getElementById('scan-selected-count').textContent = checked;
            document.getElementById('btn-start-batch').disabled = checked === 0;
            // Update internal state
            document.querySelectorAll('.scan-app-cb').forEach(cb => {
                currentBatchPairs[cb.dataset.index].selected = cb.checked;
            });
        };

        // Attach listeners to checkboxes
        document.querySelectorAll('.scan-app-cb').forEach(cb => {
            cb.addEventListener('change', updateCount);
        });
        
        document.getElementById('scan-select-all').checked = true;
        document.getElementById('scan-select-all').addEventListener('change', (e) => {
            document.querySelectorAll('.scan-app-cb').forEach(cb => {
                cb.checked = e.target.checked;
            });
            updateCount();
        });

        updateCount();

        // Show panel
        document.getElementById('scan-results-panel').style.display = 'block';
        showToast(`Found ${currentBatchPairs.length} matched pairs`, 'success');

    } catch(e) {
        showToast(e.message, 'error');
    } finally {
        btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg> Quick Scan Folders';
        btn.disabled = false;
    }
});

// Start Selected Batch
document.getElementById('btn-start-batch').addEventListener('click', async () => {
    const selectedPairs = currentBatchPairs.filter(p => p.selected).map(p => ({
        dut_path: p.dut_file,
        ref_path: p.ref_file,
        target: p.target
    }));

    if (selectedPairs.length === 0) return;

    const payload = {
        pairs: selectedPairs,
        backend: document.getElementById('opt-backend').value,
        options: {
            include_better_final: document.getElementById('opt-include-better').checked,
            include_correlation: document.getElementById('opt-include-correlation').checked
        }
    };
    
    const btn = document.getElementById('btn-start-batch');
    btn.innerHTML = 'Submitting...';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/batch`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if(!res.ok) throw new Error(data.error);
        showToast(`Started ${data.count} jobs successfully`, 'success');
        
        // Hide scan panel and switch to jobs view
        document.getElementById('scan-results-panel').style.display = 'none';
        switchView('jobs');
    } catch(e) {
        showToast(e.message, 'error');
    } finally {
        btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg> Start Selected Jobs';
        btn.disabled = false;
    }
});

document.getElementById('btn-download-zip').addEventListener('click', () => {
    if(state.currentJobId) {
        window.location.href = `${API_BASE}/jobs/${state.currentJobId}/download`;
    }
});
