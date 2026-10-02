"""
OECOSL Childcare Capacity Dashboard

Reads the summary CSVs produced by the Databricks prep notebook and writes a
single self-contained HTML file to output/dashboard.html

    python build_dashboard.py

Plotly.js is embedded in the output, so the page needs no network access.
"""

from pathlib import Path
from datetime import date
import json

import pandas as pd
import plotly as _plotly

import level1_statewide as L1
import level2_county as L2
import level3_provider as L3
from theme import (PAPER, INK, INK_SOFT, RULE, PANEL, TEAL,
                   FONT_UI, FONT_DISPLAY, fmt)

HERE = Path(__file__).parent
DATA = HERE / "data"
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------- load
summary = pd.read_csv(DATA / "statewide_summary.csv")
breakdowns = pd.read_csv(DATA / "statewide_breakdowns.csv")
county = pd.read_csv(DATA / "county_summary.csv")
provider = pd.read_csv(DATA / "provider_detail.csv", dtype={"ZipCode": str})

S = dict(zip(summary["metric"], summary["value"]))


def dim(name):
    return breakdowns[breakdowns["dimension"] == name].copy()


# ---------------------------------------------------------------- build parts
GEO = DATA / "indiana_counties.geojson"
ZIPS = DATA / "zip_centroids.json"

c1 = L1.build(dim)
map_html, table_html, table_js, cf = L2.build(county, GEO)

_gj = json.load(open(GEO, encoding="utf-8"))
pmap_html, psidebar_html, pfilter_html, pjs, pf = L3.build(provider, _gj, ZIPS)

# ---------------------------------------------------------------- kpi band
kpis = [
    ("Programs",      fmt(S["total_programs"]),   "licensed, registered and exempt"),
    ("Capacity",      fmt(S["total_capacity"]),   "across all programs"),
    ("CCDF eligible", fmt(S["ccdf_eligible"]),    "can accept CCDF"),
    ("Counties",      fmt(S["counties_covered"]), "with a provider"),
    ("Average size",  fmt(S["avg_capacity"], 1),  "capacity per program"),
    ("Median size",   fmt(S["median_capacity"]),  "capacity per program"),
]
kpi_html = "".join(
    f'<div class="kpi"><p class="kpi-label">{lab}</p>'
    f'<p class="kpi-value">{val}</p><p class="kpi-note">{note}</p></div>'
    for lab, val, note in kpis
)


def stat_list(rows):
    return "".join(
        f'<div class="stat"><span class="stat-label">{lab}</span>'
        f'<span class="stat-value">{fmt(v)}</span></div>'
        for lab, v in rows
    )


weekend_html = stat_list([
    ("Saturday only", S["open_saturday_only"]),
    ("Sunday only", S["open_sunday_only"]),
    ("Both weekend days", S["open_both_weekend"]),
    ("All seven days", S["open_every_day"]),
])
program_html = stat_list([
    ("Head Start", S["head_start"]),
    ("Early Head Start", S["early_head_start"]),
    ("Serves school-age children", S["serves_school_age"]),
    ("In good standing", S["in_good_standing"]),
])

unreported = int(S["total_programs"] - S["programs_with_capacity"])

# ---------------------------------------------------------------- plotly.js
# Default: embed the library so the page works with no network access at all.
# Pass --cdn to load it from a CDN instead (much smaller file, needs internet).
import sys

USE_CDN = "--cdn" in sys.argv

if USE_CDN:
    PLOTLY_TAG = ('<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min'
                  '@2.35.2/plotly.min.js"></script>')
else:
    _pjs = Path(_plotly.__file__).parent / "package_data" / "plotly.min.js"
    if not _pjs.exists():
        raise FileNotFoundError(
            f"plotly.min.js not found at {_pjs}. "
            "Reinstall with:  pip install --force-reinstall plotly"
        )
    PLOTLY_TAG = "<script>" + _pjs.read_text(encoding="utf-8") + "</script>"

# ---------------------------------------------------------------- template
HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Indiana Childcare Capacity</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,300;6..72,400;6..72,500&family=Archivo:wght@400;500;600&display=swap" rel="stylesheet">
{{PLOTLY_TAG}}
<style>
  :root {{
    --paper:{PAPER}; --ink:{INK}; --ink-soft:{INK_SOFT};
    --rule:{RULE}; --panel:{PANEL}; --teal:{TEAL};
    box-sizing:border-box;
    padding-top:env(safe-area-inset-top,0px);
    padding-bottom:env(safe-area-inset-bottom,0px);
  }}
  *,*::before,*::after {{ box-sizing:inherit; }}
  body {{
    margin:0; background:var(--paper); color:var(--ink);
    font-family:{FONT_UI}; font-size:15px; line-height:1.55;
    -webkit-font-smoothing:antialiased;
  }}
  .wrap {{ max-width:1180px; margin:0 auto; padding:0 28px 72px; }}

  /* ---------- masthead ---------- */
  header {{
    display:flex; flex-wrap:wrap; align-items:baseline;
    justify-content:space-between; gap:12px; padding:44px 0 16px;
  }}
  h1 {{
    margin:0; font-family:{FONT_DISPLAY};
    font-size:clamp(28px,4vw,40px); font-weight:400;
    letter-spacing:-0.015em; line-height:1.1;
  }}
  .meta {{ font-size:13px; color:var(--ink-soft); }}

  /* ---------- tabs ---------- */
  nav {{ display:flex; gap:26px; border-bottom:1px solid var(--rule); }}
  nav button {{
    appearance:none; background:none; border:none; cursor:pointer;
    font-family:{FONT_UI}; font-size:14.5px; font-weight:500;
    color:var(--ink-soft); padding:0 0 12px; margin-bottom:-1px;
    border-bottom:2px solid transparent;
  }}
  nav button:hover {{ color:var(--ink); }}
  nav button[aria-selected="true"] {{
    color:var(--ink); border-bottom-color:var(--teal);
  }}
  nav button:focus-visible {{ outline:2px solid var(--teal); outline-offset:3px; }}
  .tab {{ display:none; }}
  .tab.on {{ display:block; }}

  /* ---------- kpi band ---------- */
  .kpi-band {{
    display:grid; grid-template-columns:repeat(6,1fr);
    border-bottom:1px solid var(--rule);
  }}
  .kpi {{ padding:30px 20px 30px 0; border-right:1px solid var(--rule); }}
  .kpi:last-child {{ border-right:none; }}
  .kpi:not(:first-child) {{ padding-left:20px; }}
  .kpi-label {{ margin:0 0 6px; font-size:12.5px; font-weight:500;
                color:var(--ink-soft); }}
  .kpi-value {{
    margin:0; font-family:{FONT_DISPLAY}; font-weight:300;
    font-size:clamp(28px,3.4vw,42px); line-height:1;
    letter-spacing:-0.02em; font-variant-numeric:tabular-nums;
  }}
  .kpi-note {{ margin:8px 0 0; font-size:11.5px; color:var(--ink-soft); }}

  /* ---------- sections ---------- */
  section {{ padding-top:42px; }}
  .sec-head {{ margin-bottom:16px; max-width:64ch; }}
  h2 {{ margin:0 0 5px; font-family:{FONT_DISPLAY}; font-weight:400;
        font-size:22px; letter-spacing:-0.01em; }}
  .sec-head p {{ margin:0; font-size:13.5px; color:var(--ink-soft); }}
  .panel {{ background:var(--panel); border:1px solid var(--rule);
            padding:18px 20px 14px; }}
  .grid-2 {{ display:grid; grid-template-columns:1fr 1fr; gap:24px; }}

  /* ---------- stat lists ---------- */
  .stat {{ display:flex; justify-content:space-between; align-items:baseline;
           padding:11px 0; border-bottom:1px solid var(--rule); }}
  .stat:last-child {{ border-bottom:none; }}
  .stat-label {{ font-size:14px; color:var(--ink-soft); }}
  .stat-value {{ font-family:{FONT_DISPLAY}; font-size:23px; font-weight:400;
                 font-variant-numeric:tabular-nums; }}

  /* ---------- county table ---------- */
  .table-tools {{
    display:flex; align-items:center; justify-content:space-between;
    gap:16px; margin-bottom:10px;
  }}
  #countySearch {{
    font-family:{FONT_UI}; font-size:14px; color:var(--ink);
    padding:9px 12px; width:260px; background:var(--panel);
    border:1px solid var(--rule); border-radius:0;
  }}
  #countySearch:focus {{ outline:2px solid var(--teal); outline-offset:-1px; }}
  .tools-note {{ font-size:13px; color:var(--ink-soft); }}
  .table-scroll {{ overflow-x:auto; border:1px solid var(--rule);
                   background:var(--panel); max-height:640px; }}
  table {{ border-collapse:collapse; width:100%; font-size:13.5px; }}
  th, td {{ padding:9px 14px; white-space:nowrap; }}
  th {{
    position:sticky; top:0; background:var(--panel); cursor:pointer;
    font-weight:600; font-size:12.5px; color:var(--ink-soft);
    border-bottom:1px solid var(--rule); user-select:none;
  }}
  th:hover {{ color:var(--ink); }}
  th .arw::after {{ content:''; margin-left:5px; opacity:.5; }}
  th.asc .arw::after {{ content:'\\2191'; }}
  th.desc .arw::after {{ content:'\\2193'; }}
  td {{ border-bottom:1px solid #EDEFEE; font-variant-numeric:tabular-nums; }}
  tbody tr:last-child td {{ border-bottom:none; }}
  tbody tr:hover td {{ background:#F4F7F6; }}
  .l {{ text-align:left; }}
  .r {{ text-align:right; }}

  /* ---------- provider map row ---------- */
  .map-row {{ display:grid; grid-template-columns:1fr 258px; gap:20px; }}
  .topzip {{ padding:20px 22px; align-self:start; }}
  .tz-head {{
    margin:0 0 4px; font-size:12.5px; font-weight:600; color:var(--ink);
  }}
  .tz-list {{
    list-style:none; margin:0; padding:0;
    counter-reset:tz; font-variant-numeric:tabular-nums;
  }}
  .tz-list li {{
    display:grid; grid-template-columns:auto 1fr auto; gap:10px;
    align-items:baseline; padding:7px 0;
    border-bottom:1px solid var(--rule); font-size:13px;
  }}
  .tz-list li:last-child {{ border-bottom:none; }}
  .tz-zip {{ font-weight:600; color:var(--ink); }}
  .tz-place {{ color:var(--ink-soft); font-size:12px; }}
  .tz-n {{ color:var(--ink); }}
  .tz-foot {{
    margin:12px 0 0; font-size:11.5px; color:var(--ink-soft); line-height:1.45;
  }}

  /* ---------- provider filters ---------- */
  .filters {{
    display:flex; flex-wrap:wrap; gap:10px; margin-bottom:12px;
  }}
  .filters input, .filters select, .filters button {{
    font-family:{FONT_UI}; font-size:13.5px; color:var(--ink);
    padding:9px 11px; background:var(--panel);
    border:1px solid var(--rule); border-radius:0;
  }}
  .filters input {{ flex:1 1 220px; min-width:180px; }}
  .filters select {{ cursor:pointer; }}
  .filters button {{ cursor:pointer; color:var(--ink-soft); }}
  .filters button:hover {{ color:var(--ink); border-color:var(--ink-soft); }}
  .filters input:focus, .filters select:focus, .filters button:focus-visible {{
    outline:2px solid var(--teal); outline-offset:-1px;
  }}
  .filter-note {{
    display:flex; align-items:center; gap:10px;
    margin-bottom:10px; font-size:13px; color:var(--ink-soft);
  }}
  #zipTag {{
    background:#E8EFEE; color:var(--ink); padding:3px 8px;
    font-size:12.5px;
  }}
  #zipTag button {{
    appearance:none; border:none; background:none; cursor:pointer;
    font-family:{FONT_UI}; font-size:12.5px; color:var(--teal);
    text-decoration:underline; padding:0 0 0 6px;
  }}
  .pager {{
    display:flex; align-items:center; gap:14px;
    margin-top:12px; font-size:13px; color:var(--ink-soft);
  }}
  .pager button {{
    font-family:{FONT_UI}; font-size:13.5px; cursor:pointer;
    padding:7px 14px; background:var(--panel);
    border:1px solid var(--rule); color:var(--ink);
  }}
  .pager button:hover:not(:disabled) {{ border-color:var(--ink-soft); }}
  .pager button:disabled {{ color:#B6BDBC; cursor:default; }}
  .caveat {{
    margin:10px 0 0; font-size:12.5px; color:var(--ink-soft); max-width:70ch;
  }}

  footer {{
    margin-top:56px; padding-top:20px; border-top:1px solid var(--rule);
    font-size:12.5px; color:var(--ink-soft); max-width:70ch;
  }}
  footer p {{ margin:0 0 7px; }}

  @media (max-width:980px) {{
    .kpi-band {{ grid-template-columns:repeat(3,1fr); }}
    .kpi:nth-child(3) {{ border-right:none; }}
    .kpi:nth-child(n+4) {{ border-top:1px solid var(--rule); }}
    .grid-2 {{ grid-template-columns:1fr; }}
    .map-row {{ grid-template-columns:1fr; }}
  }}
  @media (max-width:620px) {{
    .wrap {{ padding:0 18px 56px; }}
    .kpi-band {{ grid-template-columns:repeat(2,1fr); }}
    .kpi:nth-child(even) {{ border-right:none; }}
    .kpi:nth-child(odd) {{ border-right:1px solid var(--rule); }}
    .kpi:nth-child(n+3) {{ border-top:1px solid var(--rule); }}
    #countySearch {{ width:100%; }}
    nav {{ gap:18px; }}
  }}
  @media (prefers-reduced-motion:reduce) {{
    * {{ animation:none !important; transition:none !important; }}
  }}
</style>
</head>
<body>
<div class="wrap">

  <header>
    <h1>Indiana childcare capacity</h1>
  </header>

  <nav role="tablist">
    <button role="tab" aria-selected="true"  data-tab="statewide">Statewide</button>
    <button role="tab" aria-selected="false" data-tab="counties">Counties</button>
    <button role="tab" aria-selected="false" data-tab="providers">Providers</button>
  </nav>

  <!-- ============================ STATEWIDE ============================ -->
  <div class="tab on" id="tab-statewide" role="tabpanel">

    <div class="kpi-band">{kpi_html}</div>

    <section>
      <div class="sec-head">
        <h2>Program type and Capacity</h2>
        <p></p>
      </div>
      <div class="panel">{{CHART_TYPE}}</div>
    </section>

    <section>
      <div class="sec-head">
        <h2>Current level</h2>
        <p>Programs by their current level, 0 through 4.</p>
      </div>
      <div class="panel">{{CHART_LEVEL}}</div>
    </section>

    <section>
      <div class="sec-head">
        <h2>CCDF eligible and operating schedule</h2>
        <p></p>
      </div>
      <div class="grid-2">
        <div class="panel">
          <p style="margin:0 0 4px;font-size:13px;color:var(--ink-soft)">
            CCDF eligible &mdash; by program, and by capacity</p>
          {{CHART_CCDF}}
        </div>
        <div class="panel">
          <p style="margin:0 0 4px;font-size:13px;color:var(--ink-soft)">
            Days open per week &mdash; log scale</p>
          {{CHART_DAYS}}
        </div>
      </div>
    </section>

    <section>
      <div class="grid-2">
        <div>
          <div class="sec-head"><h2>Weekend and extended care</h2></div>
          <div class="panel" style="padding:4px 20px">{weekend_html}</div>
        </div>
        <div>
          <div class="sec-head"><h2>Program designations</h2></div>
          <div class="panel" style="padding:4px 20px">{program_html}</div>
        </div>
      </div>
    </section>
  </div>

  <!-- ============================ COUNTIES ============================= -->
  <div class="tab" id="tab-counties" role="tabpanel">

    <section style="padding-top:34px">
      <div class="sec-head">
        <h2>Capacity by county</h2>
        <p>Choose a measure to shade the map. Hover any county for its full
           figures. Counts use a log colour scale, because {cf['top_county']}
           County alone holds {cf['top_share']}% of the state's capacity and would
           otherwise flatten every other county to a single shade.</p>
      </div>
      <div class="panel" style="padding:14px 8px 6px">{{MAP}}</div>
    </section>

    <section>
      <div class="sec-head">
        <h2>All 92 counties</h2>
        <p>Click any column heading to sort. The median county has
           {cf['median_programs']} programs; the smallest has {cf['smallest']}.</p>
      </div>
      {{TABLE}}
    </section>
  </div>

  <!-- ============================ PROVIDERS ============================ -->
  <div class="tab" id="tab-providers" role="tabpanel">

    <section style="padding-top:34px">
      <div class="sec-head">
        <h2>Providers by ZIP code</h2>
        <p>One bubble per ZIP, sized by how many providers it holds and shaded
           by total capacity. Click a bubble to filter the list below to that ZIP.
           {pf['busiest_zip']} in {pf['busiest_county']} County is the densest,
           with {pf['busiest_n']} providers; the median ZIP has
           {pf['median_per_zip']}.</p>
      </div>
      <div class="map-row">
        <div class="panel" style="padding:6px">{{PMAP}}</div>
        <aside class="panel topzip">{{PSIDEBAR}}</aside>
      </div>
      <p class="caveat">Bubbles sit at the centre of each ZIP code, not at any
         provider's address. The map shows where providers are concentrated, not
         where an individual facility stands.{{UNMATCHED}}</p>
    </section>

    <section>
      <div class="sec-head">
        <h2>All providers</h2>
        <p>Filter by type, county, level or CCDF eligibility, or search by name.</p>
      </div>
      {{PFILTERS}}
    </section>
  </div>

  <footer>
    <p>Source: OECOSL provider registry. One row per licensed, registered or
       exempt facility.</p>
    <p>{unreported} Ministry facilities report no capacity figure. They are
       counted as programs but excluded from every capacity total, so program
       counts and capacity counts will not reconcile.</p>
    <p>Average capacity is skewed upward by large centres; the median is shown
       alongside it for that reason.</p>
  </footer>

</div>

<script>
(function () {{
  var tabs = document.querySelectorAll('nav button');
  tabs.forEach(function (btn) {{
    btn.addEventListener('click', function () {{
      tabs.forEach(function (b) {{ b.setAttribute('aria-selected', 'false'); }});
      btn.setAttribute('aria-selected', 'true');

      document.querySelectorAll('.tab').forEach(function (p) {{
        p.classList.remove('on');
      }});
      var panel = document.getElementById('tab-' + btn.dataset.tab);
      panel.classList.add('on');

      // Plotly needs a nudge when a chart first becomes visible
      panel.querySelectorAll('.plotly-graph-div').forEach(function (g) {{
        Plotly.Plots.resize(g);
      }});
      window.scrollTo({{ top: 0 }});
    }});
  }});
}})();

{{TABLE_JS}}
</script>
</body>
</html>
"""

unmatched_note = ""
if pf["unmatched"]:
    unmatched_note = (f" {pf['unmatched']} providers have a ZIP with no known "
                      "centroid and do not appear on the map; they are still "
                      "in the list below.")

html = (HTML
        .replace("{PLOTLY_TAG}", PLOTLY_TAG)
        .replace("{CHART_TYPE}", c1["type"])
        .replace("{CHART_LEVEL}", c1["level"])
        .replace("{CHART_CCDF}", c1["ccdf"])
        .replace("{CHART_DAYS}", c1["days"])
        .replace("{MAP}", map_html)
        .replace("{TABLE}", table_html)
        .replace("{PMAP}", pmap_html)
        .replace("{PSIDEBAR}", psidebar_html)
        .replace("{PFILTERS}", pfilter_html)
        .replace("{UNMATCHED}", unmatched_note)
        .replace("{TABLE_JS}", table_js + "\n" + pjs))

path = OUT / "dashboard.html"
path.write_text(html, encoding="utf-8")

print(f"Built {path}  ({path.stat().st_size / 1024 / 1024:.1f} MB)")
print(f"  statewide : {int(S['total_programs']):,} programs, "
      f"{int(S['total_capacity']):,} capacity")
print(f"  counties  : {len(county)} rows, largest is "
      f"{cf['top_county']} at {cf['top_capacity']} capacity")
print(f"  providers : {pf['n_providers']} across {pf['n_zips']} ZIPs"
      + (f", {pf['unmatched']} unmapped" if pf["unmatched"] else ""))
