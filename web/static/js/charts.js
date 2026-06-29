/**
 * Chart.js rendering for the Report Dashboard
 */

// Global chart instances for destruction
window.charts = {
    phase: null,
    skill: null
};

Chart.defaults.color = '#a1a1aa';
Chart.defaults.font.family = "'Inter', sans-serif";

function renderPhaseComparisonChart(phaseData) {
    const ctx = document.getElementById('phase-chart').getContext('2d');
    
    if (window.charts.phase) {
        window.charts.phase.destroy();
    }

    if (!phaseData || Object.keys(phaseData).length === 0) {
        // Fallback or empty state
        return;
    }

    // Extract data
    const labels = [];
    const dutMs = [];
    const refMs = [];
    const colors = [];

    const pKeys = ["P1", "P2", "P3", "P4", "P5", "P6", "P7"];
    
    pKeys.forEach(k => {
        if(phaseData[k]) {
            const p = phaseData[k];
            labels.push(`${k} ${p.name || ''}`);
            dutMs.push(p.dut_ms || 0);
            refMs.push(p.ref_ms || 0);
            
            const diff = (p.dut_ms || 0) - (p.ref_ms || 0);
            if(diff > 5) colors.push('rgba(239, 68, 68, 0.8)'); // Red (Regression)
            else if(diff > 1) colors.push('rgba(245, 158, 11, 0.8)'); // Yellow
            else colors.push('rgba(16, 185, 129, 0.8)'); // Green (Equivalent/Better)
        }
    });

    window.charts.phase = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'DUT (ms)',
                    data: dutMs,
                    backgroundColor: colors,
                    borderRadius: 4,
                    barPercentage: 0.8,
                    categoryPercentage: 0.4
                },
                {
                    label: 'REF (ms)',
                    data: refMs,
                    backgroundColor: 'rgba(102, 126, 234, 0.5)',
                    borderRadius: 4,
                    barPercentage: 0.8,
                    categoryPercentage: 0.4
                }
            ]
        },
        options: {
            indexAxis: 'y', // Horizontal bar
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false,
                },
                legend: { position: 'top' }
            },
            scales: {
                x: { stacked: false, title: { display: true, text: 'Duration (ms)' } },
                y: { stacked: false }
            }
        }
    });
}

function renderSkillExecutionChart(skillRuns) {
    if (!skillRuns || !skillRuns.runs) return;

    const ctx = document.getElementById('skill-chart').getContext('2d');
    if (window.charts.skill) {
        window.charts.skill.destroy();
    }

    const labels = [];
    const data = [];
    const colors = [];

    // Filter out very fast skills to reduce noise, or show top 10
    const runs = skillRuns.runs
        .filter(r => r.duration_ms > 0)
        .sort((a,b) => b.duration_ms - a.duration_ms)
        .slice(0, 10);

    runs.forEach(r => {
        labels.push(r.skill);
        data.push(r.duration_ms);
        colors.push('rgba(118, 75, 162, 0.7)');
    });

    window.charts.skill = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Duration (ms)',
                data: data,
                backgroundColor: colors,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { title: { display: true, text: 'Execution Time (ms)' } }
            }
        }
    });
}
