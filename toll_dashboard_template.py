"""HTML template pieces for the toll-plaza dashboard (pure string builders)."""
from __future__ import annotations

import json

from toll_config import CRORE, LAKH

_HEAD_HTML = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Toll Plaza Traffic & Collection Dashboard</title>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.4/moment.min.js"></script>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }
                .container {
                    max-width: 1400px;
                    margin: 0 auto;
                }
                .header {
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                }
                .header h1 {
                    color: #333;
                    margin-bottom: 10px;
                    font-size: 2.5em;
                }
                .header p {
                    color: #666;
                    font-size: 1.1em;
                }
                .kpi-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }
                .kpi-card {
                    background: white;
                    padding: 25px;
                    border-radius: 10px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                    text-align: center;
                    transition: transform 0.3s ease;
                }
                .kpi-card:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 10px 25px rgba(0,0,0,0.15);
                }
                .kpi-value {
                    font-size: 2em;
                    font-weight: bold;
                    color: #667eea;
                    margin: 10px 0;
                }
                .kpi-label {
                    color: #666;
                    font-size: 0.9em;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }
                .charts-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }
                .chart-card {
                    background: white;
                    padding: 25px;
                    border-radius: 10px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                }
                .chart-title {
                    font-size: 1.2em;
                    font-weight: bold;
                    color: #333;
                    margin-bottom: 20px;
                    border-bottom: 3px solid #667eea;
                    padding-bottom: 10px;
                }
                .table-card {
                    background: white;
                    padding: 25px;
                    border-radius: 10px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                    margin-bottom: 30px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 0.95em;
                }
                th {
                    background: #667eea;
                    color: white;
                    padding: 12px;
                    text-align: left;
                    font-weight: 600;
                }
                td {
                    padding: 12px;
                    border-bottom: 1px solid #eee;
                }
                tr:hover {
                    background: #f5f5f5;
                }
                .footer {
                    text-align: center;
                    color: white;
                    padding: 20px;
                    font-size: 0.9em;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚗 Toll Plaza Traffic & Collection Dashboard</h1>
                    <p>Nationwide traffic movement and revenue analysis across major toll booths</p>
                </div>

"""


def _kpi_html(metrics, n_active_plazas) -> str:
    """KPI card grid (rupee totals shown in crore / lakh)."""
    return f"""                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-label">Total Collections</div>
                        <div class="kpi-value">₹{metrics['total_collections']/CRORE:.2f} Cr</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Average Daily</div>
                        <div class="kpi-value">₹{metrics['avg_daily_collection']/LAKH:.2f} L</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Avg Plaza Revenue</div>
                        <div class="kpi-value">₹{metrics['avg_plaza_revenue']/LAKH:.2f} L</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Active Plazas</div>
                        <div class="kpi-value">{n_active_plazas}</div>
                    </div>
                </div>

"""


_CHARTS_TABLE_HTML = """                <div class="charts-grid">
                    <div class="chart-card">
                        <div class="chart-title">Monthly Collections Trend</div>
                        <canvas id="monthlyChart"></canvas>
                    </div>
                    <div class="chart-card">
                        <div class="chart-title">Top 10 Plazas by Revenue</div>
                        <canvas id="topPlazasChart"></canvas>
                    </div>
                </div>

                <div class="charts-grid">
                    <div class="chart-card">
                        <div class="chart-title">Collections by State</div>
                        <canvas id="stateChart"></canvas>
                    </div>
                </div>

                <div class="table-card">
                    <div class="chart-title">Top 15 Toll Plazas</div>
                    <table>
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Plaza Name</th>
                                <th>State</th>
                                <th>Total Collections (₹ Lakhs)</th>
                                <th>Revenue Share (%)</th>
                            </tr>
                        </thead>
                        <tbody id="topPlazasTable"></tbody>
                    </table>
                </div>

"""


def _footer_html(generated_at) -> str:
    """Footer with the generation timestamp."""
    return f"""                <div class="footer">
                    <p>📊 Dashboard generated on {generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>Data source: National Highway Authority of India (NHAI)</p>
                </div>
            </div>

"""


def _script_monthly(metrics) -> str:
    """Chart.js block: monthly collections trend."""
    return f"""            <script>
                // Monthly trend chart
                const monthlyData = {json.dumps(metrics['monthly_breakdown'])};
                const months = Object.keys(monthlyData).sort();
                const monthlyValues = months.map(m => monthlyData[m]/100000);

                new Chart(document.getElementById('monthlyChart'), {{
                    type: 'line',
                    data: {{
                        labels: months,
                        datasets: [{{
                            label: 'Collections (₹ Lakhs)',
                            data: monthlyValues,
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            borderWidth: 3,
                            fill: true,
                            tension: 0.4,
                            pointRadius: 5,
                            pointBackgroundColor: '#667eea',
                            pointHoverRadius: 7
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            legend: {{ display: true, position: 'top' }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{ display: true, text: 'Collections (₹ Lakhs)' }}
                            }}
                        }}
                    }}
                }});

                // Top plazas chart
"""


def _script_top_plazas(metrics) -> str:
    """Chart.js block: top plazas bar chart."""
    return f"""                const topPlazas = {json.dumps(metrics['top_plazas'])};
                const plazaNames = Object.keys(topPlazas);
                const plazaValues = Object.values(topPlazas).map(v => v/100000);

                new Chart(document.getElementById('topPlazasChart'), {{
                    type: 'bar',
                    data: {{
                        labels: plazaNames,
                        datasets: [{{
                            label: 'Collections (₹ Lakhs)',
                            data: plazaValues,
                            backgroundColor: [
                                '#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe',
                                '#43e97b', '#fa709a', '#fee140', '#30cfd0', '#330867'
                            ]
                        }}]
                    }},
                    options: {{
                        indexAxis: 'y',
                        responsive: true,
                        plugins: {{
                            legend: {{ display: false }}
                        }},
                        scales: {{
                            x: {{
                                beginAtZero: true,
                                title: {{ display: true, text: 'Collections (₹ Lakhs)' }}
                            }}
                        }}
                    }}
                }});

                // State breakdown chart
"""


def _script_state(metrics) -> str:
    """Chart.js block: state doughnut chart."""
    return f"""                const stateData = {json.dumps(metrics['state_breakdown'])};
                const stateNames = Object.keys(stateData).slice(0, 15);
                const stateValues = stateNames.map(s => stateData[s]/100000);

                new Chart(document.getElementById('stateChart'), {{
                    type: 'doughnut',
                    data: {{
                        labels: stateNames,
                        datasets: [{{
                            data: stateValues,
                            backgroundColor: [
                                '#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe',
                                '#43e97b', '#fa709a', '#fee140', '#30cfd0', '#330867',
                                '#c747d4', '#30b3f3', '#ff6b9d', '#c44569', '#ffa502'
                            ]
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            legend: {{
                                position: 'right',
                                labels: {{ font: {{ size: 10 }} }}
                            }}
                        }}
                    }}
                }});

                // Populate top plazas table
                const tableBody = document.getElementById('topPlazasTable');
"""


def _script_table(metrics) -> str:
    """Script block that fills the top-plazas table."""
    return f"""                const totalCollections = {metrics['total_collections']};
                let rank = 1;
                plazaNames.forEach((name, idx) => {{
                    const amount = plazaValues[idx];
                    const percentage = ((amount * 100000 / totalCollections) * 100).toFixed(2);
                    const row = `
                        <tr>
                            <td>${{rank}}</td>
                            <td>${{name}}</td>
                            <td>--</td>
                            <td>${{amount.toFixed(2)}}</td>
                            <td>${{percentage}}%</td>
                        </tr>
                    `;
                    tableBody.innerHTML += row;
                    rank++;
                }});
            </script>
"""


_CLOSE_HTML = """        </body>
        </html>
        """


def render_dashboard_html(metrics, n_active_plazas, generated_at):
    """Render the dashboard HTML (pure function: metrics dict in, HTML str out)."""
    return "".join([
        _HEAD_HTML,
        _kpi_html(metrics, n_active_plazas),
        _CHARTS_TABLE_HTML,
        _footer_html(generated_at),
        _script_monthly(metrics),
        _script_top_plazas(metrics),
        _script_state(metrics),
        _script_table(metrics),
        _CLOSE_HTML,
    ])
