"""PDF extraction, geocoding, maps, report and main() in toll_plaza_visualization, with fake pdfplumber/geopy/folium."""
import sys
import types

import numpy as np
import pandas as pd
import pytest

import toll_plaza_visualization as tv
from toll_plaza_visualization import TollPlazaVisualization


# ---------- fake third-party modules ----------
class FakePage:
    def __init__(self, tables):
        self._t = tables

    def extract_tables(self):
        return self._t


class FakePdf:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_pdfplumber(monkeypatch, mapping):
    opened = []

    def open_(path):
        opened.append(path)
        return FakePdf([FakePage(t) for t in mapping[path]])

    monkeypatch.setattr(tv.pdfplumber, "open", open_)
    return opened


def test_extract_collects_rows_across_tables_pages_and_pdfs(monkeypatch, capsys):
    t1 = [["SNo", "Name", "Hwy", "State"],
          ["1", "Alpha Toll Plaza", "NH-48", "Haryana"],
          [None, None, None, None],          # all-falsy row: skipped
          None,                              # falsy row: skipped
          ["2", "Beta Toll Plaza", "NH-8", "Gujarat"]]
    t2 = [["h"], ["3", "Gamma Toll Plaza", "NH-3", "Assam"]]
    opened = fake_pdfplumber(monkeypatch, {"/x/a.pdf": [[t1], []], "/x/b.pdf": [[t2]]})
    viz = TollPlazaVisualization()
    df = viz.extract_toll_plazas_from_pdf(["/x/a.pdf", "/x/b.pdf"])
    assert opened == ["/x/a.pdf", "/x/b.pdf"]
    assert list(df["plaza_name"]) == ["Alpha Toll Plaza", "Beta Toll Plaza", "Gamma Toll Plaza"]
    assert list(df["state"]) == ["Haryana", "Gujarat", "Assam"]
    out = capsys.readouterr().out
    assert "Processing a.pdf" in out and "Processing b.pdf" in out
    assert "Extracted 3 unique toll plazas" in out and "States covered: 3" in out
    assert viz.plazas_df is df


def test_extract_header_row_is_not_a_record(monkeypatch):
    fake_pdfplumber(monkeypatch, {"p": [[[["Plaza Header", "State"], ["Delta Toll Plaza", "Goa"]]]]})
    df = TollPlazaVisualization().extract_toll_plazas_from_pdf(["p"])
    assert list(df["plaza_name"]) == ["Delta Toll Plaza"]


def clean(rows):
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame(rows)
    return v._clean_plaza_data().reset_index(drop=True)


def test_clean_drops_all_empty_columns_and_builds_raw_data():
    df = clean([["A Toll Plaza", None, "Goa"], ["B Toll Plaza", None, "Goa"]])
    assert list(df.columns) == ["plaza_name", "state", "highway", "raw_data"]
    assert df.iloc[0]["raw_data"] == "A Toll Plaza | Goa"
    assert pd.isna(df.iloc[0]["highway"])


def test_clean_blank_cells_ignored_and_unknown_plaza_name_uses_index():
    df = clean([["   ", "12", "3.5"], ["X Toll Plaza", "", "Goa"]])
    assert df.iloc[0]["plaza_name"] == "Unknown_Plaza_0"
    assert df.iloc[1]["plaza_name"] == "X Toll Plaza"


def test_clean_state_substring_in_non_plaza_cell_and_plaza_cell_ignored():
    df = clean([["Foo Toll Plaza Gujarat", "Near Haryana border"]])
    assert df.iloc[0]["state"] == "Near Haryana border"
    df = clean([["Foo Toll Plaza Gujarat", "NH-1"]])
    assert pd.isna(df.iloc[0]["state"])


def test_clean_state_match_is_case_insensitive_and_canonicalised():
    df = clean([["1", "Z Toll Plaza", "tamil nadu"]])
    assert df.iloc[0]["state"] == "Tamil Nadu"


def test_clean_highway_regex_variants_and_plaza_text_excluded():
    df = clean([["1", "P1 Toll Plaza", "nh 44", "Goa"], ["2", "P2 Toll Plaza", "NH44", "Goa"],
                ["3", "P3 Toll Plaza NH-9", "Goa", None], ["4", "P4 Toll Plaza", "Goa", None]])
    assert list(df["highway"].fillna("-")) == ["nh 44", "NH44", "-", "-"]


def test_clean_plaza_name_fallback_skips_numbers_state_highway():
    df = clean([["12.5", "NH-3", "Mehsana", "Gujarat"]])
    assert df.iloc[0]["plaza_name"] == "Mehsana"
    assert df.iloc[0]["highway"] == "NH-3"


def test_clean_duplicates_keep_first():
    df = clean([["1", "Dup Toll Plaza", "Goa"], ["2", "Dup Toll Plaza", "Assam"]])
    assert len(df) == 1 and df.iloc[0]["state"] == "Goa"


# ---------- geocoding ----------
class Loc:
    def __init__(self, lat, lon):
        self.latitude, self.longitude = lat, lon


class FakeNominatim:
    queries = []
    results = {}
    agent = None

    def __init__(self, user_agent=None):
        FakeNominatim.agent = user_agent

    def geocode(self, q, timeout=None):
        FakeNominatim.queries.append((q, timeout))
        r = FakeNominatim.results.get(q)
        if isinstance(r, Exception):
            raise r
        return r


@pytest.fixture
def geopy(monkeypatch):
    FakeNominatim.queries, FakeNominatim.results, FakeNominatim.agent = [], {}, None
    pkg = types.ModuleType("geopy")
    geo = types.ModuleType("geopy.geocoders")
    geo.Nominatim = FakeNominatim
    pkg.geocoders = geo
    monkeypatch.setitem(sys.modules, "geopy", pkg)
    monkeypatch.setitem(sys.modules, "geopy.geocoders", geo)
    return FakeNominatim


def test_geocode_success_none_and_exception(geopy, capsys):
    geopy.results = {"A, Goa, India": Loc(15.0, 74.0), "B, Assam, India": None,
                     "C, Bihar, India": RuntimeError("net")}
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame({"plaza_name": ["A", "B", "C"], "state": ["Goa", "Assam", "Bihar"]})
    df = v.geocode_plazas()
    assert geopy.agent == "toll_plaza_mapper"
    assert [q for q, _ in geopy.queries] == ["A, Goa, India", "B, Assam, India", "C, Bihar, India"]
    assert all(t == 10 for _, t in geopy.queries)
    assert df.loc[0, "latitude"] == 15.0 and df.loc[0, "longitude"] == 74.0
    assert pd.isna(df.loc[1, "latitude"]) and pd.isna(df.loc[2, "longitude"])
    out = capsys.readouterr().out
    assert "Successfully geocoded 1/3 plazas" in out
    assert "Progress: 0/3" in out


def test_geocode_progress_every_50(geopy, capsys):
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame({"plaza_name": [f"P{i}" for i in range(51)], "state": ["Goa"] * 51})
    v.geocode_plazas()
    out = capsys.readouterr().out
    assert "Progress: 0/51" in out and "Progress: 50/51" in out and "Progress: 25/51" not in out


def test_geocode_missing_state_column_uses_blank(geopy):
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame({"plaza_name": ["A"]})
    v.geocode_plazas()
    assert geopy.queries[0][0] == "A, , India"


# ---------- folium ----------
class FakeMap:
    instances = []

    def __init__(self, location=None, zoom_start=None, tiles=None, name=None):
        self.location, self.zoom_start, self.tiles, self.name = location, zoom_start, tiles, name
        self.children = []
        self.saved = None
        FakeMap.instances.append(self)

    def save(self, path):
        self.saved = str(path)


class FakeLayer:
    def __init__(self, *a, **k):
        self.a, self.k = a, k
        self.children = []

    def add_to(self, parent):
        parent.children.append(self)
        return self


class FakeMarker(FakeLayer):
    pass


@pytest.fixture
def folium(monkeypatch):
    FakeMap.instances = []
    fo = types.ModuleType("folium")
    fo.Map = FakeMap
    fo.Marker = FakeMarker
    fo.Icon = lambda **k: k
    plug = types.ModuleType("folium.plugins")
    plug.HeatMap = FakeLayer
    plug.MarkerCluster = FakeLayer
    fo.plugins = plug
    monkeypatch.setitem(sys.modules, "folium", fo)
    monkeypatch.setitem(sys.modules, "folium.plugins", plug)
    return fo


def test_base_map_requires_geocoding(folium, capsys):
    v = TollPlazaVisualization()
    assert v.create_base_map("x.html") is None
    v.plazas_df = pd.DataFrame({"plaza_name": ["A"]})
    assert v.create_base_map("x.html") is None
    assert "must be extracted and geocoded first" in capsys.readouterr().out
    assert FakeMap.instances == []


def test_base_map_center_is_mean_of_valid_and_skips_nan(folium, tmp_path):
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame({"plaza_name": ["A", "B", "C"], "state": ["Goa", "Goa", None],
                                "latitude": [10.0, 20.0, np.nan], "longitude": [70.0, 80.0, 90.0]})
    out = tmp_path / "m.html"
    m = v.create_base_map(str(out))
    assert m.location == [15.0, 75.0] and m.zoom_start == 5 and m.tiles == "OpenStreetMap"
    assert m.saved == str(out)
    cluster = m.children[0]
    markers = cluster.children
    assert len(markers) == 2
    assert markers[0].k["tooltip"] == "A"
    assert "State: Goa" in markers[0].k["popup"] and "Highway: Unknown" in markers[0].k["popup"]


def test_base_map_default_center_when_nothing_geocoded(folium, tmp_path):
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame({"plaza_name": ["A"], "latitude": [np.nan], "longitude": [np.nan]})
    m = v.create_base_map(str(tmp_path / "m.html"))
    assert m.location == [23.6345, 85.2988]
    assert m.children[0].children == []


def pay_df():
    return pd.DataFrame({
        "plaza_name": ["A", "B", "A"], "month": ["2024-01", "2024-01", "2024-02"],
        "amount": [100.0, 50.0, 200.0], "latitude": [10.0, 20.0, 10.0], "longitude": [70.0, 80.0, 70.0]})


def test_heat_map_with_payment_data_normalises_by_max(folium, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    v = TollPlazaVisualization()
    res, data = v.create_heat_map(payment_data=pay_df(), output_html=str(tmp_path / "h.html"))
    assert res.location == [pytest.approx(40 / 3), pytest.approx(220 / 3)]
    assert res.tiles == "CartoDB positron"
    heat = res.children[0]
    assert heat.a[0] == [[10.0, 70.0, 0.5], [20.0, 80.0, 0.25], [10.0, 70.0, 1.0]]
    assert heat.k == {"radius": 25, "blur": 15, "max_zoom": 1}
    monthly = [m for m in FakeMap.instances if m.name]
    assert [m.name for m in monthly] == ["Collections - 2024-01", "Collections - 2024-02"]
    assert monthly[0].children[0].a[0] == [[10.0, 70.0, 0.5], [20.0, 80.0, 0.25]]
    assert monthly[1].children[0].a[0] == [[10.0, 70.0, 1.0]]
    assert monthly[0].saved == "toll_heatmap_2024-01.html"
    assert list(data["month"]) == ["2024-01", "2024-01", "2024-02"]


def test_heat_map_without_data_and_no_geocoded_plazas(folium, capsys):
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame({"plaza_name": ["A"], "latitude": [np.nan], "longitude": [np.nan]})
    assert v.create_heat_map() is None
    assert "No geocoded plazas available" in capsys.readouterr().out


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="timedelta(days=30*month) drifts: Jan 1 + 30d is still January, so 12 'months' span only 10 distinct YYYY-MM labels")
def test_heat_map_sample_data_covers_twelve_distinct_months(folium, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    np.random.seed(0)
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame({"plaza_name": ["A"], "latitude": [10.0], "longitude": [70.0]})
    _, data = v.create_heat_map(output_html=str(tmp_path / "h.html"))
    assert data["month"].nunique() == 12


def test_heat_map_generates_twelve_months_of_sample_data(folium, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    np.random.seed(0)
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame({"plaza_name": ["A", "B", "C"], "state": ["Goa", "Goa", None],
                                "latitude": [10.0, 20.0, np.nan], "longitude": [70.0, 80.0, np.nan]})
    m, data = v.create_heat_map(output_html=str(tmp_path / "h.html"))
    assert len(data) == 12 * 2  # NaN-coordinate plaza excluded
    assert data["month"].iloc[0] == "2024-01"
    assert data["amount"].between(50 * 0.8, 500 * 1.2).all()
    assert v.payment_data is data
    assert data["state"].iloc[0] == "Goa"


# ---------- report ----------
def test_report_none_without_plazas():
    assert TollPlazaVisualization().generate_report() is None


def test_report_counts_and_top_ten(capsys):
    v = TollPlazaVisualization()
    states = ["S%d" % i for i in range(12)]
    v.plazas_df = pd.DataFrame({
        "plaza_name": [f"P{i}" for i in range(13)],
        "state": states + ["S0"],
        "highway": ["NH-1"] * 13})
    r = v.generate_report()
    assert r["total_plazas"] == 13 and r["states_covered"] == 12
    assert r["states"]["S0"] == 2
    assert r["highways"] == {"NH-1": 13}
    assert r["geocoded_plazas"] == 0
    out = capsys.readouterr().out
    assert "Total Plazas Extracted: 13" in out
    assert "S0: 2" in out
    assert out.count("  S") == 10  # only the top 10 states are printed


def test_report_geocoded_count_and_missing_highway_column():
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame({"plaza_name": ["A", "B"], "state": ["Goa", "Goa"],
                                "latitude": [1.0, np.nan], "longitude": [2.0, 3.0]})
    r = v.generate_report()
    assert r["geocoded_plazas"] == 1
    assert r["highways"] == {}


def test_report_highways_limited_to_ten():
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame({"plaza_name": [f"P{i}" for i in range(12)], "state": ["Goa"] * 12,
                                "highway": [f"NH-{i}" for i in range(12)]})
    assert len(v.generate_report()["highways"]) == 10


# ---------- main ----------
def test_main_wires_steps_and_assigns_state_coordinates(monkeypatch, capsys):
    plazas = pd.DataFrame({"plaza_name": ["G", "X"], "state": ["Gujarat", "Atlantis"]})
    calls = {}

    def extract(self, paths):
        calls["paths"] = paths
        self.plazas_df = plazas.copy()
        return self.plazas_df

    monkeypatch.setattr(TollPlazaVisualization, "extract_toll_plazas_from_pdf", extract)
    monkeypatch.setattr(TollPlazaVisualization, "create_base_map", lambda self, p: calls.setdefault("base", p))
    monkeypatch.setattr(TollPlazaVisualization, "create_heat_map",
                        lambda self, output_html: calls.setdefault("heat", output_html))
    saved = {}
    monkeypatch.setattr(pd.DataFrame, "to_csv", lambda self, p, index=None: saved.update(p=p, index=index))
    captured = {}
    def report(self):
        captured["df"] = self.plazas_df.copy()
        return True

    monkeypatch.setattr(TollPlazaVisualization, "generate_report", report)
    np.random.seed(0)
    tv.main()
    assert len(calls["paths"]) == 3 and all(p.endswith(".pdf") for p in calls["paths"])
    assert saved["p"].endswith("toll_plazas_cleaned.csv") and saved["index"] is False
    df = captured["df"]
    assert abs(df.loc[0, "latitude"] - 22.3) <= 0.5 and abs(df.loc[0, "longitude"] - 72.6) <= 0.5
    assert pd.isna(df.loc[1, "latitude"]) and pd.isna(df.loc[1, "longitude"])
    assert calls["base"].endswith("toll_plazas_map.html")
    assert calls["heat"].endswith("toll_collections_heatmap.html")
    assert "Added sample coordinates for 1/2 plazas" in capsys.readouterr().out
