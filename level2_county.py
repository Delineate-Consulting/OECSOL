"""
Level 2 — county view.

Builds the Indiana choropleth (with a metric selector) and the sortable
county table. Imported by build_dashboard.py.
"""

import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from theme import (PANEL, INK, INK_SOFT, RULE, TEAL, FONT_UI, FONT_DISPLAY,
                   style, HTML_ARGS, fmt)

# ---------------------------------------------------------------- scale ramps
# single-hue ramps keep the map readable and colour-blind safe
RAMP_TEAL = [[0, "#F0F4F3"], [0.25, "#BBD3D1"], [0.5, "#7FAEAC"],
             [0.75, "#4A8886"], [1.0, "#22585B"]]
RAMP_OCHRE = [[0, "#F7F3EA"], [0.25, "#E4D3AE"], [0.5, "#CDB172"],
              [0.75, "#B08C3E"], [1.0, "#7E6222"]]

# metric key, label, hover unit, whether the spread needs a log colour scale
METRICS = [
    ("total_capacity",  "Capacity",                  "seats",     True,  RAMP_TEAL),
    ("programs",        "Programs",                  "programs",  True,  RAMP_TEAL),
    ("avg_capacity",    "Average program size",      "seats",     False, RAMP_OCHRE),
    ("ccdf_eligible",   "CCDF eligible programs",    "programs",  True,  RAMP_TEAL),
    ("ccdf_children",   "CCDF children served",      "children",  True,  RAMP_TEAL),
    ("open_weekend",    "Programs open at weekends", "programs",  False, RAMP_OCHRE),
    ("avg_days_open",   "Average days open a week",  "days",      False, RAMP_OCHRE),
]


def load_geo(path):
    """Read the Indiana county geojson and return it plus a NAME -> FIPS map."""
    gj = json.load(open(path, encoding="utf-8"))
    lookup = {f["properties"]["NAME"].upper(): f["id"] for f in gj["features"]}
    return gj, lookup


def attach_fips(county, lookup):
    """Join FIPS onto the county table, reporting anything that fails to match."""
    county = county.copy()
    county["fips"] = county["CountyKey"].map(lookup)

    missed = county[county["fips"].isna()]["CountyKey"].tolist()
    if missed:
        raise ValueError(
            "These counties have no matching geojson feature: "
            + ", ".join(missed)
            + "\nCheck spelling against the NAME property in the geojson."
        )
    return county


def _log_ticks(vmax):
    """Colourbar ticks at 1, 10, 100 ... up to vmax, in log10 space."""
    stops, v = [], 1
    while v <= vmax:
        stops.append(v)
        v *= 10
    stops.append(int(vmax))
    return [np.log10(s + 1) for s in stops], [fmt(s) for s in stops]


def chart_county_map(county, geojson):
    """One choropleth trace per metric; the dropdown toggles visibility."""
    fig = go.Figure()

    for i, (key, label, unit, use_log, ramp) in enumerate(METRICS):
        vals = county[key].astype(float)

        if use_log:
            z = np.log10(vals + 1)
            ticks, ticktext = _log_ticks(vals.max())
            cb = dict(tickvals=ticks, ticktext=ticktext)
        else:
            z = vals
            cb = dict()

        fig.add_choropleth(
            geojson=geojson,
            locations=county["fips"],
            z=z,
            customdata=np.stack([
                county["County"], vals,
                county["programs"], county["total_capacity"],
                county["ccdf_eligible"], county["open_weekend"],
            ], axis=-1),
            colorscale=ramp,
            marker=dict(line=dict(color="#FFFFFF", width=0.6)),
            visible=(i == 0),
            hovertemplate=(
                "<b>%{customdata[0]} County</b><br>"
                f"{label}: " + "%{customdata[1]:,.1f} " + unit +
                "<br><br>"
                "Programs: %{customdata[2]:,}<br>"
                "Capacity: %{customdata[3]:,} seats<br>"
                "CCDF eligible: %{customdata[4]:,}<br>"
                "Open weekends: %{customdata[5]:,}"
                "<extra></extra>"
            ),
            colorbar=dict(
                thickness=11, len=0.62, x=0.99, xanchor="right",
                y=0.5, outlinewidth=0, ticks="outside", ticklen=4,
                tickfont=dict(family=FONT_UI, size=10, color=INK_SOFT),
                **cb,
            ),
        )

    buttons = []
    for i, (key, label, _u, _l, _r) in enumerate(METRICS):
        vis = [j == i for j in range(len(METRICS))]
        buttons.append(dict(label=label, method="update",
                            args=[{"visible": vis}]))

    fig.update_geos(
        fitbounds="locations", visible=False,
        bgcolor=PANEL, projection_type="mercator",
    )
    fig.update_layout(
        height=560,
        margin=dict(l=0, r=0, t=46, b=0),
        paper_bgcolor=PANEL, plot_bgcolor=PANEL,
        font=dict(family=FONT_UI, size=12, color=INK_SOFT),
        hoverlabel=dict(bgcolor=INK, bordercolor=INK,
                        font=dict(family=FONT_UI, size=12, color="#FFFFFF"),
                        align="left"),
        updatemenus=[dict(
            type="dropdown", buttons=buttons, direction="down",
            x=0, xanchor="left", y=1.075, yanchor="top",
            bgcolor=PANEL, bordercolor=RULE, borderwidth=1,
            font=dict(family=FONT_UI, size=12.5, color=INK),
            pad=dict(l=6, r=6, t=4, b=4), showactive=False,
        )],
    )
    return fig


# ---------------------------------------------------------------- table
TABLE_COLS = [
    ("County",           "County",        "text"),
    ("programs",         "Programs",      "num"),
    ("total_capacity",   "Capacity",      "num"),
    ("avg_capacity",     "Avg size",      "num1"),
    ("ccdf_eligible",    "CCDF eligible", "num"),
    ("ccdf_children",    "CCDF children", "num"),
    ("in_good_standing", "Good standing", "num"),
    ("open_weekend",     "Open weekends", "num"),
    ("level_3",          "Level 3",       "num"),
    ("level_4",          "Level 4",       "num"),
]


def county_table_html(county):
    d = county.sort_values("total_capacity", ascending=False)

    head = "".join(
        f'<th data-col="{i}" data-type="{t}" class="{"l" if t=="text" else "r"}">'
        f'{lbl}<span class="arw"></span></th>'
        for i, (_k, lbl, t) in enumerate(TABLE_COLS)
    )

    body = []
    for _, r in d.iterrows():
        cells = []
        for key, _lbl, t in TABLE_COLS:
            v = r[key]
            if t == "text":
                cells.append(f'<td class="l">{v}</td>')
            elif t == "num1":
                cells.append(f'<td class="r" data-v="{v}">{v:,.1f}</td>')
            else:
                cells.append(f'<td class="r" data-v="{v}">{v:,.0f}</td>')
        body.append("<tr>" + "".join(cells) + "</tr>")

    return f"""
<div class="table-tools">
  <input id="countySearch" type="search" placeholder="Search for a county"
         aria-label="Search counties">
  <span id="countyCount" class="tools-note">{len(d)} counties</span>
</div>
<div class="table-scroll">
  <table id="countyTable">
    <thead><tr>{head}</tr></thead>
    <tbody>{"".join(body)}</tbody>
  </table>
</div>"""


TABLE_JS = """
(function () {
  var tbl = document.getElementById('countyTable');
  if (!tbl) return;
  var tbody = tbl.tBodies[0];
  var rows  = Array.prototype.slice.call(tbody.rows);
  var note  = document.getElementById('countyCount');
  var total = rows.length;
  var sortCol = -1, sortAsc = false;

  function val(row, i, type) {
    var td = row.cells[i];
    return type === 'text' ? td.textContent.trim().toLowerCase()
                           : parseFloat(td.dataset.v);
  }

  Array.prototype.forEach.call(tbl.tHead.rows[0].cells, function (th, i) {
    th.addEventListener('click', function () {
      var type = th.dataset.type;
      sortAsc = (sortCol === i) ? !sortAsc : (type === 'text');
      sortCol = i;

      rows.sort(function (a, b) {
        var x = val(a, i, type), y = val(b, i, type);
        if (x < y) return sortAsc ? -1 : 1;
        if (x > y) return sortAsc ? 1 : -1;
        return 0;
      });
      rows.forEach(function (r) { tbody.appendChild(r); });

      Array.prototype.forEach.call(tbl.tHead.rows[0].cells, function (h) {
        h.classList.remove('asc', 'desc');
      });
      th.classList.add(sortAsc ? 'asc' : 'desc');
    });
  });

  var search = document.getElementById('countySearch');
  search.addEventListener('input', function () {
    var q = search.value.trim().toLowerCase();
    var shown = 0;
    rows.forEach(function (r) {
      var hit = !q || r.cells[0].textContent.toLowerCase().indexOf(q) > -1;
      r.style.display = hit ? '' : 'none';
      if (hit) shown++;
    });
    note.textContent = (shown === total)
      ? total + ' counties'
      : shown + ' of ' + total + ' counties';
  });
})();
"""


def build(county, geojson_path):
    """Return (map_html, table_html, table_js, top_line_facts)."""
    gj, lookup = load_geo(geojson_path)
    county = attach_fips(county, lookup)

    fig = chart_county_map(county, gj)

    top = county.nlargest(1, "total_capacity").iloc[0]
    share = top["total_capacity"] / county["total_capacity"].sum() * 100
    facts = dict(
        top_county=top["County"],
        top_capacity=fmt(top["total_capacity"]),
        top_share=f"{share:.0f}",
        smallest=int(county["programs"].min()),
        median_programs=int(county["programs"].median()),
    )

    return fig.to_html(**HTML_ARGS), county_table_html(county), TABLE_JS, facts
