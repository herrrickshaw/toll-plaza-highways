"""Characterisation tests for the toll-plaza scripts (no network, no PDFs)."""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

import toll_plaza_dashboard as dash
import toll_plaza_visualization as viz
import update_toll_visualization as upd


@pytest.fixture
def plazas():
    return pd.DataFrame({
        'plaza_name': ['A Toll Plaza', 'B Toll Plaza', 'C Toll Plaza'],
        'state': ['Gujarat', 'Gujarat', 'Bihar'],
    })


@pytest.fixture
def payments_csv(tmp_path):
    path = tmp_path / 'pay.csv'
    pd.DataFrame({
        'plaza_name': ['A Toll Plaza', 'B Toll Plaza', 'A Toll Plaza'],
        'date': ['2024-01-01', '2024-01-01', '2024-02-01'],
        'amount': [100000.0, 300000.0, 200000.0],
    }).to_csv(path, index=False)
    return path


@pytest.fixture
def dashboard(tmp_path, plazas, payments_csv):
    plazas_path = tmp_path / 'plz.csv'
    plazas.to_csv(plazas_path, index=False)
    return dash.TollPlazaDashboard(str(plazas_path), str(payments_csv))


def test_metrics(dashboard):
    m = dashboard.metrics
    assert m['total_collections'] == 600000.0
    assert m['monthly_breakdown'] == {'2024-01': 400000.0, '2024-02': 200000.0}
    assert m['state_breakdown'] == {'Gujarat': 600000.0}
    assert list(m['top_plazas']) == ['A Toll Plaza', 'B Toll Plaza']


def test_outputs_written(dashboard, tmp_path):
    html = dashboard.create_interactive_dashboard(str(tmp_path / 'd.html'))
    assert 'Toll Plaza Traffic & Collection Dashboard' in open(html).read()
    dashboard.export_metrics_json(str(tmp_path / 'm.json'))
    dashboard.generate_text_report(str(tmp_path / 'r.txt'))
    assert 'MONTHLY TRENDS' in (tmp_path / 'r.txt').read_text()


def test_build_text_report_pure(dashboard):
    text = dash.build_text_report(
        dashboard.plazas, dashboard.payments, dashboard.metrics, datetime(2024, 3, 1, 12, 0, 0))
    assert 'Report Generated: 2024-03-01 12:00:00' in text
    assert 'Total Collections: ₹0.06 Crore' in text
    assert ' 1. A Toll Plaza' in text


def test_render_dashboard_html_pure(dashboard):
    html = dash.render_dashboard_html(dashboard.metrics, 2, datetime(2024, 3, 1))
    assert '2024-03-01 00:00:00' in html
    assert '<div class="kpi-value">2</div>' in html


def test_sample_payment_data_shape(plazas, tmp_path):
    np.random.seed(0)
    df = dash.create_sample_payment_data(plazas, str(tmp_path / 's.csv'))
    assert set(df.columns) == {'plaza_name', 'date', 'amount', 'vehicle_count'}
    assert len(df) == 12 * 28 * 3


def test_clean_plaza_data_dedupes_and_extracts_state():
    v = viz.TollPlazaVisualization()
    v.plazas_df = pd.DataFrame([
        ['NH-8 Vapi Toll Plaza', 'Gujarat'],
        ['NH-8 Vapi Toll Plaza', 'Gujarat'],
        ['Pune Toll', 'Maharashtra'],
    ])
    out = v._clean_plaza_data()
    assert list(out['plaza_name']) == ['NH-8 Vapi Toll Plaza', 'Pune Toll']
    assert list(out['state']) == ['Gujarat', 'Maharashtra']


def test_assign_sample_coordinates_within_jitter():
    df = pd.DataFrame({'state': ['Gujarat', 'Atlantis']})
    np.random.seed(0)
    lats = viz.assign_sample_coordinates(df)
    assert lats[1] is None and pd.isna(df['longitude'][1])
    assert abs(df['latitude'][0] - 22.3) <= 0.5


def test_generate_report_counts():
    v = viz.TollPlazaVisualization()
    v.plazas_df = pd.DataFrame({'state': ['Gujarat', 'Gujarat', 'Bihar'],
                                'latitude': [1.0, None, 2.0], 'longitude': [1.0, None, 2.0]})
    r = v.generate_report()
    assert r['total_plazas'] == 3 and r['states_covered'] == 2 and r['geocoded_plazas'] == 2


def test_validate_payment_data(payments_csv, tmp_path):
    assert upd.validate_payment_data(str(payments_csv)) is True
    bad = tmp_path / 'bad.csv'
    pd.DataFrame({'plaza_name': ['x']}).to_csv(bad, index=False)
    assert upd.validate_payment_data(str(bad)) is False
    assert upd.validate_payment_data(str(tmp_path / 'missing.csv')) is False


def test_resolve_output_dir_keeps_legacy_layout():
    assert str(upd.resolve_output_dir('Downloads')) == '/Users/umashankar/Downloads'


def test_cli_help_smoke(capsys):
    with pytest.raises(SystemExit) as e:
        import sys
        old = sys.argv
        sys.argv = ['update_toll_visualization.py', '--help']
        try:
            upd.main()
        finally:
            sys.argv = old
    assert e.value.code == 0
    assert '--data' in capsys.readouterr().out
