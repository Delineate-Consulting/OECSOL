"""
Level 3 — provider view.

A ZIP-level bubble map (one bubble per ZIP, sized by provider count) above a
filterable, paginated table of every individual provider.

Providers are positioned by the centroid of their ZIP code, not by their street
address. The bubble is therefore the honest unit on the map: it says "this many
providers are somewhere in this ZIP", not "this provider is at this point".
"""

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from theme import (PANEL, INK, INK_SOFT, RULE, TEAL, OCHRE,
                   FONT_UI, HTML_ARGS, fmt)

# columns shown in the table, in order
TABLE_COLS = [
    ("FacilityName",            "Provider",  "text"),
    ("FacilityTypeDescription", "Type",      "text"),
    ("County",                  "County",    "text"),
    ("City",                    "City",      "text"),
    ("Capacity",                "Capacity",  "num"),
    ("CurrentLevel",            "Level",     "num"),
    ("CCDFEligibility",         "CCDF",      "bool"),
    ("ScheduleLabel",           "Schedule",  "text"),
    ("Ages",                    "Ages",      "text"),
]


def load_zips(path):
    """ZIP -> [lat, lon] lookup."""
    return json.load(open(path, encoding="utf-8"))


def attach_coords(prov, zips):
    """Add lat/lon from the ZIP centroid table. Returns (df, n_unmatched)."""
    prov = prov.copy()
    prov["ZipCode"] = (prov["ZipCode"].astype(str)
                       .str.replace(r"\.0$", "", regex=True).str.zfill(5))

    prov["lat"] = prov["ZipCode"].map(lambda z: zips.get(z, [None, None])[0])
    prov["lon"] = prov["ZipCode"].map(lambda z: zips.get(z, [None, None])[1])

    unmatched = prov["lat"].isna().sum()
    return prov, int(unmatched)


def _top(s):
    """Most common non-null value, or blank when the group is entirely null.

    Needed because .mode() returns an empty Series for an all-null group,
    and 1,837 providers have no City recorded.
    """
    m = s.dropna().mode()
    return m.iat[0] if len(m) else ""


def zip_rollup(prov):
    """Aggregate providers to one row per ZIP for the bubble layer."""
    g = (prov.dropna(subset=["lat"])
         .groupby("ZipCode")
         .agg(lat=("lat", "first"), lon=("lon", "first"),
              providers=("FacilityGenID", "count"),
              capacity=("Capacity", "sum"),
              ccdf=("CCDFEligibility", "sum"),
              city=("City", _top),
              county=("County", _top))
         .reset_index())
    return g.sort_values("providers", ascending=False)


def chart_zip_map(zg, geojson):
    """County outlines for context, ZIP bubbles on top."""
    fig = go.Figure()

    # faint county base layer, purely for orientation
    fig.add_choropleth(
        geojson=geojson,
        locations=[f["id"] for f in geojson["features"]],
        z=[0] * len(geojson["features"]),
        colorscale=[[0, "#EDF1F0"], [1, "#EDF1F0"]],
        showscale=False,
        marker=dict(line=dict(color="#FFFFFF", width=0.7)),
        hoverinfo="skip",
    )

    # bubble area scales with provider count; sqrt keeps big ZIPs from swamping
    size = np.sqrt(zg["providers"]) * 3.0
    size = size.clip(lower=4.5, upper=24)

    fig.add_scattergeo(
        lat=zg["lat"], lon=zg["lon"],
        mode="markers",
        marker=dict(
            size=size,
            color=zg["capacity"],
            colorscale=[[0, "#B8D2CE"], [0.4, "#6BA09D"],
                        [0.75, "#3B7B7C"], [1, "#1E4F52"]],
            opacity=0.68,
            line=dict(color="#FFFFFF", width=0.7),
            sizemode="diameter",
            colorbar=dict(
                title=dict(text="Capacity", side="top",
                           font=dict(family=FONT_UI, size=11, color=INK_SOFT)),
                thickness=9, len=0.44, x=1.0, xanchor="right",
                y=0.5, outlinewidth=0, ticks="outside", ticklen=3,
                tickfont=dict(family=FONT_UI, size=10, color=INK_SOFT),
            ),
        ),
        customdata=np.stack([
            zg["ZipCode"], zg["county"], zg["providers"],
            zg["capacity"], zg["ccdf"],
        ], axis=-1),
        hovertemplate=(
            "<b>ZIP %{customdata[0]}</b>  ·  %{customdata[1]} County<br><br>"
            "Providers: %{customdata[2]}<br>"
            "Capacity: %{customdata[3]:,} capacity<br>"
            "CCDF eligible: %{customdata[4]}"
            "<extra></extra>"
        ),
    )

    fig.update_geos(fitbounds="locations", visible=False,
                    bgcolor=PANEL, projection_type="mercator")
    fig.update_layout(
        height=600,
        margin=dict(l=0, r=0, t=6, b=6),
        paper_bgcolor=PANEL, plot_bgcolor=PANEL,
        showlegend=False,
        font=dict(family=FONT_UI, size=12, color=INK_SOFT),
        hoverlabel=dict(bgcolor=INK, bordercolor=INK, align="left",
                        font=dict(family=FONT_UI, size=12, color="#FFFFFF")),
    )
    return fig


def top_zip_html(zg, n=14):
    """Ranked list of the densest ZIPs, to fill the space beside the map."""
    d = zg.head(n)
    rows = "".join(
        f'<li><span class="tz-zip">{r["ZipCode"]}</span>'
        f'<span class="tz-place">{r["county"]}</span>'
        f'<span class="tz-n">{int(r["providers"])}</span></li>'
        for _, r in d.iterrows()
    )
    return f"""
<p class="tz-head">Densest ZIP codes</p>
<ol class="tz-list">{rows}</ol>
<p class="tz-foot">Provider count. Click a bubble on the map to filter
the list below.</p>"""


def table_payload(prov):
    """Compact row arrays + filter option lists, for the browser to render."""
    d = prov.sort_values(["County", "FacilityName"])

    def cell(v, kind):
        if pd.isna(v) or v == "":
            return ""
        if kind == "bool":
            return 1 if bool(v) else 0
        if kind == "num":
            return int(v) if float(v).is_integer() else float(v)
        return str(v)

    rows = [
        [cell(r[k], t) for k, _lbl, t in TABLE_COLS] + [str(r["ZipCode"])]
        for _, r in d.iterrows()
    ]

    return dict(
        rows=rows,
        cols=[lbl for _k, lbl, _t in TABLE_COLS],
        types=[t for _k, _l, t in TABLE_COLS],
        types_opt=sorted(d["FacilityTypeDescription"].dropna().unique().tolist()),
        county_opt=sorted(d["County"].dropna().unique().tolist()),
        level_opt=sorted(int(v) for v in d["CurrentLevel"].dropna().unique()),
    )


FILTER_HTML = """
<div class="filters">
  <input id="pSearch" type="search" placeholder="Search provider name"
         aria-label="Search provider name">
  <select id="fType"   aria-label="Filter by type"></select>
  <select id="fCounty" aria-label="Filter by county"></select>
  <select id="fLevel"  aria-label="Filter by current level"></select>
  <select id="fCcdf"   aria-label="Filter by CCDF eligibility">
    <option value="">CCDF: any</option>
    <option value="1">CCDF eligible</option>
    <option value="0">Not CCDF eligible</option>
  </select>
  <button id="fClear" type="button">Clear</button>
</div>
<div class="filter-note">
  <span id="pCount"></span>
  <span id="zipTag" hidden></span>
</div>
<div class="table-scroll">
  <table id="provTable">
    <thead><tr id="provHead"></tr></thead>
    <tbody id="provBody"></tbody>
  </table>
</div>
<div class="pager">
  <button id="pPrev" type="button">Previous</button>
  <span id="pPage"></span>
  <button id="pNext" type="button">Next</button>
</div>
"""


PROVIDER_JS = """
(function () {
  var D = window.__PROVIDERS__;
  if (!D) return;

  var PAGE = 50, page = 0, view = D.rows.slice(), zipFilter = null;
  var Z = D.cols.length;                    // ZIP sits in the last column

  var body   = document.getElementById('provBody');
  var head   = document.getElementById('provHead');
  var count  = document.getElementById('pCount');
  var pageEl = document.getElementById('pPage');
  var zipTag = document.getElementById('zipTag');

  head.innerHTML = D.cols.map(function (c, i) {
    var cls = (D.types[i] === 'text') ? 'l' : 'r';
    return '<th class="' + cls + '">' + c + '</th>';
  }).join('');

  function fill(sel, opts, label) {
    sel.innerHTML = '<option value="">' + label + '</option>' +
      opts.map(function (o) {
        return '<option value="' + o + '">' + o + '</option>';
      }).join('');
  }
  fill(document.getElementById('fType'),   D.types_opt,  'Type: any');
  fill(document.getElementById('fCounty'), D.county_opt, 'County: any');
  fill(document.getElementById('fLevel'),  D.level_opt,  'Level: any');

  function render() {
    var start = page * PAGE;
    var slice = view.slice(start, start + PAGE);

    body.innerHTML = slice.map(function (r) {
      return '<tr>' + D.cols.map(function (_c, i) {
        var v = r[i], t = D.types[i], cls = (t === 'text') ? 'l' : 'r';
        if (t === 'bool') v = v ? 'Yes' : 'No';
        else if (t === 'num' && v !== '') v = Number(v).toLocaleString();
        if (t === 'text' && String(v).length > 60) {
          return '<td class="l" title="' + String(v).replace(/"/g, '&quot;') +
                 '">' + String(v).slice(0, 58) + '\\u2026</td>';
        }
        return '<td class="' + cls + '">' + v + '</td>';
      }).join('') + '</tr>';
    }).join('');

    count.textContent = view.length.toLocaleString() + ' of ' +
                        D.rows.length.toLocaleString() + ' providers';
    var pages = Math.max(1, Math.ceil(view.length / PAGE));
    pageEl.textContent = 'Page ' + (page + 1) + ' of ' + pages;
    document.getElementById('pPrev').disabled = (page === 0);
    document.getElementById('pNext').disabled = (page >= pages - 1);
  }

  function apply() {
    var q      = document.getElementById('pSearch').value.trim().toLowerCase();
    var fType  = document.getElementById('fType').value;
    var fCty   = document.getElementById('fCounty').value;
    var fLvl   = document.getElementById('fLevel').value;
    var fCcdf  = document.getElementById('fCcdf').value;

    view = D.rows.filter(function (r) {
      if (q && String(r[0]).toLowerCase().indexOf(q) === -1) return false;
      if (fType && r[1] !== fType) return false;
      if (fCty  && r[2] !== fCty)  return false;
      if (fLvl  && String(r[5]) !== fLvl) return false;
      if (fCcdf && String(r[6]) !== fCcdf) return false;
      if (zipFilter && r[Z] !== zipFilter) return false;
      return true;
    });
    page = 0;
    render();
  }

  ['pSearch', 'fType', 'fCounty', 'fLevel', 'fCcdf'].forEach(function (id) {
    var el = document.getElementById(id);
    el.addEventListener(el.tagName === 'INPUT' ? 'input' : 'change', apply);
  });

  document.getElementById('fClear').addEventListener('click', function () {
    document.getElementById('pSearch').value = '';
    ['fType', 'fCounty', 'fLevel', 'fCcdf'].forEach(function (id) {
      document.getElementById(id).value = '';
    });
    zipFilter = null;
    zipTag.hidden = true;
    apply();
  });

  document.getElementById('pPrev').addEventListener('click', function () {
    if (page > 0) { page--; render(); }
  });
  document.getElementById('pNext').addEventListener('click', function () {
    if ((page + 1) * PAGE < view.length) { page++; render(); }
  });

  // clicking a ZIP bubble filters the table to that ZIP
  var mapDiv = document.querySelector('#tab-providers .plotly-graph-div');
  if (mapDiv) {
    mapDiv.on('plotly_click', function (ev) {
      var pt = ev.points && ev.points[0];
      if (!pt || !pt.customdata) return;
      zipFilter = String(pt.customdata[0]);
      zipTag.hidden = false;
      zipTag.innerHTML = 'ZIP ' + zipFilter +
        ' <button type="button" id="zipClear">clear</button>';
      apply();
      document.getElementById('zipClear').addEventListener('click', function () {
        zipFilter = null; zipTag.hidden = true; apply();
      });
      document.querySelector('.filters').scrollIntoView(
        { behavior: 'smooth', block: 'start' });
    });
  }

  apply();
})();
"""


def build(prov, geojson, zip_path):
    """Return (map_html, sidebar_html, filters_html, js, facts)."""
    zips = load_zips(zip_path)
    prov, unmatched = attach_coords(prov, zips)
    zg = zip_rollup(prov)

    fig = chart_zip_map(zg, geojson)
    payload = table_payload(prov)

    js = ("window.__PROVIDERS__ = " + json.dumps(payload, separators=(",", ":"))
          + ";\n" + PROVIDER_JS)

    biggest = zg.iloc[0]
    facts = dict(
        n_providers=fmt(len(prov)),
        n_zips=fmt(zg["ZipCode"].nunique()),
        unmatched=unmatched,
        busiest_zip=biggest["ZipCode"],
        busiest_n=int(biggest["providers"]),
        busiest_county=biggest["county"],
        median_per_zip=int(zg["providers"].median()),
    )
    return (fig.to_html(**HTML_ARGS), top_zip_html(zg),
            FILTER_HTML, js, facts)
