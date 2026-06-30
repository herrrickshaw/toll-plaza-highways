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
The toll↔retail distance analysis consumes fuel-outlet data from
[`fuel-retail-outlets`](https://github.com/herrrickshaw/fuel-retail-outlets)
(SSRI/BPCL outlet feeds). Point the scripts at that data, or re-run its extractors.

## Related repos
- [`fuel-retail-outlets`](https://github.com/herrrickshaw/fuel-retail-outlets) — fuel outlet data & maps
- [`india-trade-export-analysis`](https://github.com/herrrickshaw/india-trade-export-analysis) — trade/export analysis

## Notes
Toll & outlet datasets are from public sources; indicative for planning, not official.
