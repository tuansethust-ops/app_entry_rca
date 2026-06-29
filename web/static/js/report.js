/**
 * Report Dashboard rendering logic
 */

let currentReportData = null;

async function renderReportDashboard(jobId) {
    try {
        const res = await fetch(`${API_BASE}/jobs/${jobId}/report`);
        const report = await res.json();
        
        if (!res.ok) throw new Error(report.error || 'Failed to load report');
        
        currentReportData = report;
        switchView('report');
        
        renderSummaryCards(report);
        if(report.phase_comparison) renderPhaseComparisonChart(report.phase_comparison);
        if(report.skill_runs) renderSkillExecutionChart(report.skill_runs);
        if(report.final_leaves) renderLeavesTable(report.final_leaves);
        if(report.evidence_graph) renderEvidenceGraph(report.evidence_graph);
        if(report.raw_phase_intervals) renderWaterfall(report.raw_phase_intervals);
        if(report.raw_metrics) renderMetricsTable(report.raw_metrics);

    } catch(e) {
        showToast(e.message, 'error');
    }
}

function renderSummaryCards(report) {
    const summary = report.analysis_summary || {};
    const container = document.getElementById('summary-cards');
    
    let resultClass = 'success';
    let resultText = 'EQUIVALENT';
    if(summary.verdict === 'DUT_REGRESSION') { resultClass = 'error'; resultText = 'REGRESSION'; }
    if(summary.verdict === 'DUT_BETTER') { resultClass = 'success'; resultText = 'BETTER'; }

    let delta = summary.delta_ms ? summary.delta_ms.toFixed(1) : '0.0';
    let deltaSign = delta > 0 ? '+' : '';

    const cards = [
        { title: 'Result', value: resultText, sub: `Score: ${summary.score || 'N/A'}`, class: resultClass },
        { title: 'Time Delta', value: `${deltaSign}${delta} ms`, sub: 'DUT vs REF difference', class: '' },
        { title: 'Root Cause', value: summary.root_cause || 'Unknown', sub: 'Top ranked leaf', class: '' },
        { title: 'Leaves Evaluated', value: summary.total_leaves || '0', sub: `${summary.regressed_leaves || 0} regressed`, class: '' }
    ];

    container.innerHTML = cards.map(c => `
        <div class="card glass">
            <span class="card-title">${c.title}</span>
            <span class="card-value ${c.class ? 'text-'+c.class : ''}" style="color: ${c.class==='error'?'#ef4444':c.class==='success'?'#10b981':''}">${c.value}</span>
            <span class="card-sub">${c.sub}</span>
        </div>
    `).join('');
}

function renderLeavesTable(leaves) {
    const wrapper = document.getElementById('leaves-table-wrapper');
    document.getElementById('leaf-count-badge').textContent = leaves.length;

    if (!leaves || leaves.length === 0) {
        wrapper.innerHTML = '<p style="color:var(--text-muted)">No root causes identified.</p>';
        return;
    }

    let html = `
        <table>
            <thead>
                <tr>
                    <th>Score</th>
                    <th>Phase</th>
                    <th>Leaf Name</th>
                    <th>Status</th>
                    <th>Causality</th>
                    <th>Delta (ms)</th>
                </tr>
            </thead>
            <tbody>
    `;

    leaves.forEach((l, i) => {
        let statusBadge = l.status === 'DUT_REGRESSION' ? 'error' : l.status === 'DUT_BETTER' ? 'success' : 'warning';
        html += `
            <tr class="row-expandable" onclick="toggleDetails('leaf-details-${i}')">
                <td class="num">${(l.score||0).toFixed(1)}</td>
                <td><span class="badge">${l.phase || 'UNK'}</span></td>
                <td class="mono">${l.name}</td>
                <td><span class="badge ${statusBadge}">${l.status}</span></td>
                <td>${l.causality || '-'}</td>
                <td class="num" style="color: ${l.delta_ms > 0 ? 'var(--color-error)' : 'var(--color-success)'}">${l.delta_ms > 0 ? '+' : ''}${(l.delta_ms||0).toFixed(2)}</td>
            </tr>
            <tr class="row-details" id="leaf-details-${i}">
                <td colspan="6">
                    <div class="details-content">
                        <div class="detail-box">
                            <h4>Action Recommended</h4>
                            <p>${l.action || 'No action defined.'}</p>
                        </div>
                        <div class="detail-box">
                            <h4>Description</h4>
                            <p>${l.description || 'No description available.'}</p>
                        </div>
                    </div>
                </td>
            </tr>
        `;
    });

    html += `</tbody></table>`;
    wrapper.innerHTML = html;
}

window.toggleDetails = function(id) {
    document.getElementById(id).classList.toggle('open');
};

function renderEvidenceGraph(graph) {
    const container = document.getElementById('evidence-tree');
    // For now, pretty print JSON. In a full implementation, this builds a nested HTML tree.
    container.textContent = JSON.stringify(graph, null, 2);
}

function renderWaterfall(intervals) {
    const container = document.getElementById('waterfall-container');
    if(!intervals || !intervals.DUT) {
        container.innerHTML = '<p style="color:var(--text-muted)">No interval data available.</p>';
        return;
    }

    // Basic CSS Gantt chart
    let html = '<div style="display:flex; flex-direction:column; gap:4px; font-family:var(--font-mono); font-size:12px;">';
    
    // Find global min/max
    let minTs = Number.MAX_VALUE;
    let maxTs = 0;
    
    ['DUT', 'REF'].forEach(side => {
        if(intervals[side]) {
            Object.values(intervals[side]).forEach(p => {
                if(p.start < minTs) minTs = p.start;
                if(p.end > maxTs) maxTs = p.end;
            });
        }
    });

    const totalDur = maxTs - minTs;
    if(totalDur <= 0) return;

    ['DUT', 'REF'].forEach(side => {
        if(!intervals[side]) return;
        html += `<div style="margin-top:8px; font-weight:bold; color: ${side==='DUT'?'var(--color-error)':'var(--color-success)'}">${side} Phases</div>`;
        
        const pKeys = ["P1", "P2", "P3", "P4", "P5", "P6", "P7"];
        pKeys.forEach(k => {
            const p = intervals[side][k];
            if(p) {
                const leftPct = ((p.start - minTs) / totalDur) * 100;
                const widthPct = ((p.end - p.start) / totalDur) * 100;
                
                html += `
                    <div style="display:flex; align-items:center;">
                        <div style="width: 40px;">${k}</div>
                        <div style="flex:1; background:rgba(0,0,0,0.2); position:relative; height:16px; border-radius:2px;">
                            <div style="position:absolute; left:${leftPct}%; width:${widthPct}%; background:rgba(102,126,234,0.7); height:100%; border-radius:2px;"></div>
                        </div>
                        <div style="width: 60px; text-align:right;">${((p.end - p.start)*1000).toFixed(1)}ms</div>
                    </div>
                `;
            }
        });
    });

    html += '</div>';
    container.innerHTML = html;
}

function renderMetricsTable(metrics) {
    const wrapper = document.getElementById('metrics-table-wrapper');
    if (!metrics || metrics.length === 0) {
        wrapper.innerHTML = '<p style="color:var(--text-muted)">No raw metrics available.</p>';
        return;
    }

    let html = `
        <table>
            <thead><tr><th>Metric ID</th><th>DUT Value</th><th>REF Value</th></tr></thead>
            <tbody>
    `;

    metrics.forEach(m => {
        html += `
            <tr>
                <td class="mono">${m.id}</td>
                <td class="num">${m.dut !== null ? m.dut : '-'}</td>
                <td class="num">${m.ref !== null ? m.ref : '-'}</td>
            </tr>
        `;
    });
    
    html += `</tbody></table>`;
    wrapper.innerHTML = html;
}
