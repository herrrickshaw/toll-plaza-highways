# 🛣️ Toll Plaza & Highway Analysis — India

Toll-plaza visualisation and **toll ↔ fuel-retail-outlet distance analysis** along
Indian highways — identifying retail/service-outlet opportunities relative to toll
infrastructure.

## Contents

| File | What it does |
|---|---|
| `toll_plaza_dashboard.py` | Interactive toll-plaza dashboard |
| `toll_plaza_visualization.py` | Toll-plaza map/visualisation generator |
| `update_toll_visualization.py` | Refresh the visualisation from latest data |
| `TOLL_RETAIL_DISTANCE_ANALYSIS_SUMMARY.md` | Toll↔retail-outlet shortest-path / distance analysis writeup |
| `TOLL_RETAIL_INTEGRATION_SUMMARY.md` | Integration of toll-plaza and retail-outlet datasets |

## Run
```bash
python toll_plaza_dashboard.py
# or
python toll_plaza_visualization.py && python update_toll_visualization.py
```

## Data dependency
`toll_plaza_dashboard.py` / `toll_plaza_visualization.py` / `update_toll_visualization.py`
are self-contained: they parse NHAI toll-plaza PDFs and write their own
`toll_plazas_cleaned.csv` locally — no read from `fuel-retail-outlets` at
runtime.

The toll↔retail distance analysis (`TOLL_RETAIL_DISTANCE_ANALYSIS_SUMMARY.md`,
`TOLL_RETAIL_INTEGRATION_SUMMARY.md`) is different: it's a one-time manual
cross-reference against outlet data produced by
[`fuel-retail-outlets`](https://github.com/herrrickshaw/fuel-retail-outlets)'s
`extract_ssri_complete_107k.py` (SSRI/BPCL feeds) — that script and its output
live in the other repo, not here. To reproduce the distance analysis: run
`extract_ssri_complete_107k.py` in `fuel-retail-outlets` first, then join its
output against `toll_plazas_cleaned.csv` by coordinates (no committed script
does this join automatically yet).

## Related repos
- [`fuel-retail-outlets`](https://github.com/herrrickshaw/fuel-retail-outlets) — fuel outlet data & maps
- [`india-trade-export-analysis`](https://github.com/herrrickshaw/india-trade-export-analysis) — trade/export analysis

## Notes
Toll & outlet datasets are from public sources; indicative for planning, not official.
