# Toll Plaza and Highway Analysis — India

Scripts that parse NHAI toll-plaza PDFs into a cleaned plaza table, draw folium maps and heat maps, and build an
HTML/JSON/text dashboard of toll collections. The repo also carries two write-ups of a one-off toll-to-fuel-retail-outlet
distance analysis, used to look for retail/service-outlet opportunities relative to toll infrastructure on Indian
highways.

> Status: research-only. Toll and outlet datasets come from public sources and are indicative for planning, not
> official. The maps and dashboard currently run on **synthetic sample data** (see Limitations).

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/herrrickshaw/toll-plaza-highways/blob/main/notebooks/colab_test.ipynb)
New here? See [How to use this repo with AI](HOW_TO_USE_WITH_AI.md).

## What it does
- Extracts toll-plaza tables from NHAI PDFs (`pdfplumber`) and writes `toll_plazas_cleaned.csv` (`toll_plaza_visualization.py`).
- Builds a folium base map and monthly heat maps of collections (same module).
- Generates a Chart.js HTML dashboard, a metrics JSON and a text report from plaza and payment CSVs (`toll_plaza_dashboard.py`).
- Re-generates those outputs from a real payment CSV with `plaza_name,date,amount` columns (`update_toll_visualization.py`).
- Documents the toll to retail-outlet distance analysis (`TOLL_RETAIL_*_SUMMARY.md`).

## Quick start
```bash
git clone https://github.com/herrrickshaw/toll-plaza-highways
cd toll-plaza-highways
python -m venv .venv && source .venv/bin/activate
pip install pandas numpy pdfplumber folium geopy pytest ruff
python toll_plaza_dashboard.py          # needs toll_plazas_cleaned.csv, see Configuration
```

Or, with your own payment data:
```bash
python toll_plaza_visualization.py && python update_toll_visualization.py --data payments.csv [--output Downloads] [--archive] [--force]
```

## How it works
| Stage | Module | Output |
|---|---|---|
| PDF tables to plaza rows, cleaning, state/highway detection | `toll_plaza_visualization.py` (`TollPlazaVisualization`) | `toll_plazas_cleaned.csv` |
| Placeholder coordinates (state centroid plus jitter) | `assign_sample_coordinates` | latitude/longitude columns |
| Maps | `create_base_map`, `create_heat_map` | `toll_plazas_map.html`, `toll_collections_heatmap.html`, `toll_heatmap_<YYYY-MM>.html` |
| Metrics and rendering | `toll_plaza_dashboard.py` (`TollPlazaDashboard`, `render_dashboard_html`, `build_text_report`) | `toll_dashboard.html`, `toll_metrics.json`, `toll_analysis_report.txt` |
| Validate a payment CSV and regenerate outputs | `update_toll_visualization.py` | `*_updated.*` files |
| Paths and unit constants | `toll_config.py` | n/a |

Rendering and report building are pure functions (data in, string out); file I/O sits in the class methods and `main()`.

## Repository layout
| Path | Purpose |
|---|---|
| `toll_plaza_visualization.py` | PDF extraction, cleaning, folium maps |
| `toll_plaza_dashboard.py` | Metrics, HTML dashboard, JSON and text report, sample-data generator |
| `update_toll_visualization.py` | CLI to refresh outputs from a payment CSV |
| `toll_config.py` | Default input/output locations and unit constants |
| `tests/` | pytest unit and smoke tests (no network, no PDFs) |
| `TOLL_RETAIL_*_SUMMARY.md` | Distance-analysis and integration write-ups |
| `from-global-*/` | Historical outputs imported from other repos (HTML heat maps, metrics, reports); not regenerated |
| `notebooks/colab_test.ipynb` | Colab test notebook |

## Data sources
| Source | What is taken | Access route | Licence / caveat |
|---|---|---|---|
| NHAI toll-plaza PDFs (`NH-Fee-Plazas-1.pdf`, `NH-Toll-Plaza-.pdf`, `NHAI-toll-list.pdf`) | plaza name, state, highway | manual download into `~/Downloads` | public NHAI documents; not committed |
| [`fuel-retail-outlets`](https://github.com/herrrickshaw/fuel-retail-outlets) `extract_ssri_complete_107k.py` | outlet coordinates (distance analysis only) | run in the other repo | SSRI/BPCL feeds; the join is manual, no script here does it |

## Configuration
Defaults live in `toll_config.py` and point at `/Users/umashankar/Downloads/` (inputs `toll_plazas_cleaned.csv` and the three
PDFs; outputs next to them). Edit `HOME_DIR` there to relocate. `update_toll_visualization.py --output` is a sub-directory of
`HOME_DIR`. No credentials are used or required.

## Testing
```bash
pytest -q
ruff check .
```

## Limitations and known issues
- Coordinates are state-centroid placeholders with random jitter; real geocoding (`geocode_plazas`, Nominatim) exists but is not used by `main()`.
- With no payment CSV the heat maps and `toll_plaza_dashboard.py` run on randomly generated sample data, so figures are illustrative only.
- State detection covers 14 states; plazas elsewhere get no state/coordinates.
- Monthly heat maps step in 30-day offsets from 2024-01-01, so some months (for example 2024-02) are skipped.
- `toll_plaza_dashboard.py` and the visualiser use hard-coded home-directory defaults (see Configuration).
- The toll to retail-outlet distance analysis is a one-time manual cross-reference; to reproduce it run `extract_ssri_complete_107k.py` in `fuel-retail-outlets`, then join its output against `toll_plazas_cleaned.csv` by coordinates.

## Related repositories
- [`fuel-retail-outlets`](https://github.com/herrrickshaw/fuel-retail-outlets) — fuel outlet data and maps
- [`india-trade-export-analysis`](https://github.com/herrrickshaw/india-trade-export-analysis) — trade/export analysis

## Licence
No licence file yet — all rights reserved.
