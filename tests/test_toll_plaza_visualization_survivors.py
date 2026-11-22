"""Pins for ordering, defaults and constants in toll_plaza_visualization / dashboard HTML / report."""
import sys
import types

import numpy as np
import pandas as pd
import pytest

import toll_plaza_visualization as tv
from toll_plaza_dashboard import TollPlazaDashboard
from toll_plaza_visualization import TollPlazaVisualization

ALL_STATES = [
    'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
    'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
    'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya',
    'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim',
    'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand',
    'West Bengal', 'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Puducherry', 'Chandigarh']


def clean(rows):
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame(rows)
    return v._clean_plaza_data().reset_index(drop=True)


@pytest.mark.parametrize("state", ALL_STATES)
def test_every_listed_state_is_recognised_as_exact_cell(state):
    assert clean([["1", "Q Toll Plaza", state]]).iloc[0]["state"] == state


def test_first_exact_state_cell_wins():
    assert clean([["Q Toll Plaza", "Goa", "Assam"]]).iloc[0]["state"] == "Goa"


def test_first_non_plaza_cell_containing_a_state_wins():
    df = clean([["Q Toll Plaza", "Near Goa coast", "Near Assam hills"]])
    assert df.iloc[0]["state"] == "Near Goa coast"


def test_first_highway_cell_wins():
    df = clean([["Q Toll Plaza", "NH-1", "NH-2", "Goa"]])
    assert df.iloc[0]["highway"] == "NH-1"


def test_highway_needs_word_boundary_before_nh():
    df = clean([["Q Toll Plaza", "KANH 44", "Goa"]])
    assert pd.isna(df.iloc[0]["highway"])


def test_first_plaza_cell_wins():
    df = clean([["1", "First Toll Plaza", "Second Toll Plaza", "Goa"]])
    assert df.iloc[0]["plaza_name"] == "First Toll Plaza"


@pytest.mark.parametrize("cell", ["Foo Plaza", "Foo Toll", "FOO TOLL", "FOO PLAZA"])
def test_toll_or_plaza_word_in_any_case_marks_plaza_cell(cell):
    df = clean([["Goa", "Zed", cell]])
    assert df.iloc[0]["plaza_name"] == cell


def test_partially_filled_rows_are_kept_in_extraction(monkeypatch):
    table = [["h"], ["1", "Alpha Toll Plaza", None, "Goa"]]

    class Pdf:
        pages = [types.SimpleNamespace(extract_tables=lambda: [table])]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(tv.pdfplumber, "open", lambda p: Pdf())
    df = TollPlazaVisualization().extract_toll_plazas_from_pdf(["p"])
    assert list(df["plaza_name"]) == ["Alpha Toll Plaza"]


def test_columns_with_some_values_are_kept():
    df = clean([["A Toll Plaza", "NH-1", "Goa"], ["B Toll Plaza", None, "Goa"]])
    assert df.iloc[0]["highway"] == "NH-1"


def test_geocoder_user_agent_in_both_import_paths(monkeypatch):
    seen = []
    geo = types.ModuleType("geopy.geocoders")

    class N:
        def __init__(self, user_agent=None):
            seen.append(user_agent)

        def geocode(self, q, timeout=None):
            return None

    geo.Nominatim = N
    monkeypatch.setitem(sys.modules, "geopy", types.ModuleType("geopy"))
    monkeypatch.setitem(sys.modules, "geopy.geocoders", geo)
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame({"plaza_name": ["A"], "state": ["Goa"]})
    v.geocode_plazas()
    assert seen == ["toll_plaza_mapper"]


def test_geopy_missing_triggers_pip_install_then_retries(monkeypatch):
    seen, runs = [], []
    geo = types.ModuleType("geopy.geocoders")

    class N:
        def __init__(self, user_agent=None):
            seen.append(user_agent)

        def geocode(self, q, timeout=None):
            return None

    geo.Nominatim = N
    state = {"n": 0}

    real_import = __import__

    def fake_import(name, *a, **k):
        if name == "geopy.geocoders":
            state["n"] += 1
            if state["n"] == 1:
                raise ImportError
            return geo
        return real_import(name, *a, **k)

    monkeypatch.setattr("builtins.__import__", fake_import)
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda cmd, **k: runs.append(cmd))
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame({"plaza_name": ["A"], "state": ["Goa"]})
    v.geocode_plazas()
    assert runs == [["pip", "install", "geopy", "-q"]]
    assert seen == ["toll_plaza_mapper"]


class FakeMap:
    def __init__(self, location=None, zoom_start=None, tiles=None, name=None):
        self.location, self.zoom_start, self.tiles = location, zoom_start, tiles

    def save(self, p):
        pass


class FakeLayer:
    def __init__(self, *a, **k):
        pass

    def add_to(self, parent):
        return self


@pytest.fixture
def folium(monkeypatch):
    maps = []

    class M(FakeMap):
        def __init__(self, **k):
            super().__init__(**k)
            maps.append(self)

    fo = types.ModuleType("folium")
    fo.Map, fo.Marker, fo.Icon = M, FakeLayer, lambda **k: k
    plug = types.ModuleType("folium.plugins")
    plug.HeatMap = plug.MarkerCluster = FakeLayer
    monkeypatch.setitem(sys.modules, "folium", fo)
    monkeypatch.setitem(sys.modules, "folium.plugins", plug)
    return maps


def test_single_valid_plaza_defines_the_center(folium, tmp_path):
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame({"plaza_name": ["A"], "latitude": [11.0], "longitude": [77.0]})
    m = v.create_base_map(str(tmp_path / "m.html"))
    assert m.location == [11.0, 77.0]


def test_zoom_is_five_on_every_map(folium, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame({"plaza_name": ["A"], "latitude": [11.0], "longitude": [77.0]})
    v.create_base_map(str(tmp_path / "m.html"))
    pay = pd.DataFrame({"plaza_name": ["A"], "month": ["2024-01"], "amount": [1.0],
                        "latitude": [11.0], "longitude": [77.0]})
    v.create_heat_map(payment_data=pay, output_html=str(tmp_path / "h.html"))
    assert [m.zoom_start for m in folium] == [5, 5, 5]


def test_main_places_gujarat_plazas_within_half_a_degree_of_state_point(monkeypatch):
    plazas = pd.DataFrame({"plaza_name": ["G"], "state": ["Gujarat"]})
    monkeypatch.setattr(TollPlazaVisualization, "extract_toll_plazas_from_pdf",
                        lambda self, p: setattr(self, "plazas_df", plazas.copy()) or self.plazas_df)
    monkeypatch.setattr(TollPlazaVisualization, "create_base_map", lambda self, p: None)
    monkeypatch.setattr(TollPlazaVisualization, "create_heat_map", lambda self, output_html: None)
    calls, got = [], {}
    monkeypatch.setattr(TollPlazaVisualization, "generate_report",
                        lambda self: got.update(df=self.plazas_df.copy()))
    monkeypatch.setattr(pd.DataFrame, "to_csv", lambda self, *a, **k: None)
    monkeypatch.setattr(np.random, "uniform", lambda lo, hi: calls.append((lo, hi)) or 0.0)
    tv.main()
    assert calls == [(-0.5, 0.5), (-0.5, 0.5)]
    assert (got["df"].loc[0, "latitude"], got["df"].loc[0, "longitude"]) == (22.3, 72.6)


# ---------- dashboard ----------
def dash(tmp_path, plazas, pay):
    pp, payp = tmp_path / "pl.csv", tmp_path / "pay.csv"
    pd.DataFrame(plazas).to_csv(pp, index=False)
    pd.DataFrame(pay).to_csv(payp, index=False)
    return TollPlazaDashboard(str(pp), str(payp))


def test_html_pins_state_slice_and_lakh_scaling(tmp_path):
    d = dash(tmp_path, {"plaza_name": ["A"], "state": ["Goa"]},
             {"plaza_name": ["A"], "date": ["2024-01-01"], "amount": [1e6]})
    out = tmp_path / "d.html"
    d.create_interactive_dashboard(str(out))
    html = out.read_text()
    assert "Object.keys(stateData).slice(0, 15)" in html
    assert "monthlyData[m]/100000" in html
    assert "v => v/100000" in html


def test_report_lists_at_most_fifteen_states_and_lakh_figures(tmp_path):
    n = 16
    plazas = {"plaza_name": [f"P{i}" for i in range(n)], "state": [f"State{i:02d}" for i in range(n)]}
    pay = {"plaza_name": [f"P{i}" for i in range(n)], "date": ["2024-01-01"] * n,
           "amount": [float(100_000 * (i + 1)) for i in range(n)]}
    d = dash(tmp_path, plazas, pay)
    rep = open(d.generate_text_report(str(tmp_path / "r.txt"))).read()
    sect = rep.split("COLLECTIONS BY STATE")[1].split("MONTHLY TRENDS")[0]
    listed = [l for l in sect.splitlines() if l.startswith("State")]
    assert len(listed) == 15
    assert listed[0].startswith("State15") and "State00" not in sect
    assert "Average Daily Collection: ₹136.00 Lakhs" in rep  # 13.6M rupees on a single day
    assert "Average Plaza Revenue: ₹8.50 Lakhs" in rep  # 13.6M / 16 plazas


def test_kpi_cards_show_distinct_daily_and_plaza_averages(tmp_path):

    plazas = {"plaza_name": ["A", "B", "C"], "state": ["Goa"] * 3}
    pay = {"plaza_name": ["A", "B", "C"], "date": ["2024-01-01", "2024-01-01", "2024-01-02"],
           "amount": [1_000_000.0, 1_000_000.0, 4_000_000.0]}
    d = dash(tmp_path, plazas, pay)
    out = tmp_path / "d.html"
    d.create_interactive_dashboard(str(out))
    html = out.read_text()
    assert "₹30.00 L</div>" in html      # avg daily: (2M + 4M) / 2 days = 3M
    assert "₹20.00 L</div>" in html      # avg plaza: 6M / 3 plazas = 2M


@pytest.mark.parametrize("state,lat,lon", [
    ("Gujarat", 22.3, 72.6), ("Maharashtra", 19.76, 75.71), ("Rajasthan", 27.0, 74.2),
    ("Haryana", 29.0, 77.0), ("Tamil Nadu", 11.1, 79.8), ("Karnataka", 15.3, 75.9),
    ("Andhra Pradesh", 15.9, 78.5), ("Telangana", 17.4, 78.5), ("Punjab", 31.5, 74.8),
    ("Uttar Pradesh", 26.8, 80.6), ("Delhi", 28.6, 77.2), ("Himachal Pradesh", 32.2, 77.2),
    ("Madhya Pradesh", 22.9, 78.6), ("West Bengal", 24.2, 88.4)])
def test_main_state_coordinate_table(monkeypatch, state, lat, lon):
    plazas = pd.DataFrame({"plaza_name": ["P"], "state": [state]})
    monkeypatch.setattr(TollPlazaVisualization, "extract_toll_plazas_from_pdf",
                        lambda self, p: setattr(self, "plazas_df", plazas.copy()) or self.plazas_df)
    monkeypatch.setattr(TollPlazaVisualization, "create_base_map", lambda self, p: None)
    monkeypatch.setattr(TollPlazaVisualization, "create_heat_map", lambda self, output_html: None)
    got = {}
    monkeypatch.setattr(TollPlazaVisualization, "generate_report", lambda self: got.update(df=self.plazas_df.copy()))
    monkeypatch.setattr(pd.DataFrame, "to_csv", lambda self, *a, **k: None)
    monkeypatch.setattr(np.random, "uniform", lambda lo, hi: 0.0)
    tv.main()
    assert (got["df"].loc[0, "latitude"], got["df"].loc[0, "longitude"]) == (lat, lon)
