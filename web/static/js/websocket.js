/**
 * WebSocket handling for Real-Time Logs and Progress
 */

window.ws = null;

function connectWebSocket(jobId) {
    if (window.ws) {
        window.ws.close();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/job/${jobId}`;
    
    window.ws = new WebSocket(wsUrl);

    window.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleWsEvent(msg);
    };

    window.ws.onerror = (error) => {
        console.error('WebSocket Error:', error);
    };

    window.ws.onclose = () => {
        console.log('WebSocket Connection Closed');
    };
}

function handleWsEvent(event) {
    const type = event.type;
    const data = event.data;
    
    // Log format
    const time = new Date(event.timestamp * 1000).toLocaleTimeString([], {hour12: false});
    const logBox = document.getElementById('log-output');

    if (type.startsWith('log.')) {
        const level = type.split('.')[1]; // info, warning, error
        const div = document.createElement('div');
        div.className = 'log-line';
        div.innerHTML = `
            <span class="log-ts">${time}</span>
            <span class="log-lvl ${level}">[${level.toUpperCase()}]</span>
            <span class="log-msg">${data.message}</span>
        `;
        logBox.appendChild(div);
        logBox.scrollTop = logBox.scrollHeight;
    }

    if (type === 'progress.update') {
        updateProgress(data.progress, data.completed, data.total);
    }

    if (type === 'skill.started') {
        const item = document.getElementById(`skill-${data.skill}`);
        if(item) {
            item.className = 'pipeline-item running';
            item.querySelector('.skill-icon').textContent = '🔄';
        }
    }

    if (type === 'skill.completed') {
        const item = document.getElementById(`skill-${data.skill}`);
        if(item) {
            item.className = 'pipeline-item success';
            item.querySelector('.skill-icon').textContent = '✅';
            item.querySelector('.skill-dur').textContent = `${data.duration_ms}ms`;
        }
    }

    if (type === 'skill.skipped') {
        const item = document.getElementById(`skill-${data.skill}`);
        if(item) {
            item.className = 'pipeline-item skipped';
            item.querySelector('.skill-icon').textContent = '⏭️';
            item.querySelector('.skill-dur').textContent = `skipped`;
        }
    }

    if (type === 'skill.error') {
        const item = document.getElementById(`skill-${data.skill}`);
        if(item) {
            item.className = 'pipeline-item error';
            item.querySelector('.skill-icon').textContent = '❌';
            item.querySelector('.skill-dur').textContent = `error`;
        }
    }

    if (type === 'job.completed') {
        showToast('Analysis completed successfully!', 'success');
        setTimeout(() => {
            renderReportDashboard(event.job_id);
        }, 1000);
    }

    if (type === 'job.failed') {
        showToast(`Job failed: ${data.error}`, 'error');
        const div = document.createElement('div');
        div.className = 'log-line';
        div.innerHTML = `<span class="log-ts">${time}</span><span class="log-lvl error">[FATAL]</span><span class="log-msg">${data.error}</span>`;
        logBox.appendChild(div);
    }
}
