"""Level 1 — statewide view. Charts for the whole-of-Indiana summary."""

import plotly.graph_objects as go

from theme import (PANEL, INK, INK_SOFT, TEAL, OCHRE, TYPE_COLORS,
                   LEVEL_COLORS, FONT_UI, FONT_DISPLAY, style, HTML_ARGS, fmt)


def chart_program_type(dim):
    """Paired horizontal bars: count on the left, capacity on the right.

    Two separate scales, shared category axis — makes the divergence between
    'how many' and 'how big' readable without a confusing dual axis.
    """
    d = dim("Program Type").sort_values("capacity", ascending=True)
    cats = d["category"].tolist()
    colors = {c: TYPE_COLORS[i] for i, c in
              enumerate(dim("Program Type")["category"].tolist())}
    bar_colors = [colors[c] for c in cats]

    fig = go.Figure()
    fig.add_bar(
        x=d["programs"], y=cats, orientation="h",
        marker=dict(color=bar_colors), xaxis="x", yaxis="y",
        text=[fmt(v) for v in d["programs"]],
        textposition="outside",
        textfont=dict(family=FONT_UI, size=11, color=INK_SOFT),
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{x:,} programs<extra></extra>",
    )
    fig.add_bar(
        x=d["capacity"], y=cats, orientation="h",
        marker=dict(color=bar_colors), xaxis="x2", yaxis="y2",
        text=[fmt(v) for v in d["capacity"]],
        textposition="outside",
        textfont=dict(family=FONT_UI, size=11, color=INK_SOFT),
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{x:,} seats<extra></extra>",
    )

    fig.update_layout(
        xaxis=dict(domain=[0.0, 0.44], showticklabels=False,
                   range=[0, d["programs"].max() * 1.22]),
        yaxis=dict(domain=[0, 0.88], tickfont=dict(size=12, color=INK)),
        xaxis2=dict(domain=[0.56, 1.0], showticklabels=False, anchor="y2",
                    range=[0, d["capacity"].max() * 1.22]),
        yaxis2=dict(domain=[0, 0.88], anchor="x2", showticklabels=False),
        annotations=[
            dict(x=0.0, y=1.0, xref="paper", yref="paper", xanchor="left",
                 text="Programs", showarrow=False,
                 font=dict(family=FONT_UI, size=12, color=INK)),
            dict(x=0.56, y=1.0, xref="paper", yref="paper", xanchor="left",
                 text="Capacity (seats)", showarrow=False,
                 font=dict(family=FONT_UI, size=12, color=INK)),
        ],
    )
    return style(fig, height=330, margin=dict(l=8, r=16, t=28, b=8))


def chart_current_level(dim):
    d = dim("Current Level").copy()
    d["category"] = d["category"].astype(str)
    d = d.sort_values("category")

    fig = go.Figure()
    fig.add_bar(
        x=d["category"], y=d["programs"],
        marker=dict(color=LEVEL_COLORS),
        text=[fmt(v) for v in d["programs"]],
        textposition="outside",
        textfont=dict(family=FONT_UI, size=12, color=INK_SOFT),
        cliponaxis=False,
        customdata=d["capacity"],
        hovertemplate="<b>Current level %{x}</b><br>%{y:,} programs"
                      "<br>%{customdata:,} seats<extra></extra>",
    )
    fig.update_yaxes(showticklabels=False, range=[0, d["programs"].max() * 1.18])
    fig.update_xaxes(tickfont=dict(size=13, color=INK))
    return style(fig, height=330, margin=dict(l=8, r=8, t=24, b=8))


def chart_ccdf(dim):
    d = dim("CCDF Status")
    elig = d[d["category"] == "CCDF Eligible"].iloc[0]
    tot_p = d["programs"].sum()
    tot_c = d["capacity"].sum()

    fig = go.Figure()
    fig.add_pie(
        values=[elig["programs"], tot_p - elig["programs"]],
        labels=["Eligible", "Not eligible"],
        hole=0.72, sort=False, direction="clockwise",
        marker=dict(colors=[TEAL, "#E4E7E4"], line=dict(color=PANEL, width=2)),
        textinfo="none", domain=dict(x=[0.0, 0.46]),
        hovertemplate="<b>%{label}</b><br>%{value:,} programs<extra></extra>",
    )
    fig.add_pie(
        values=[elig["capacity"], tot_c - elig["capacity"]],
        labels=["Eligible", "Not eligible"],
        hole=0.72, sort=False, direction="clockwise",
        marker=dict(colors=[OCHRE, "#E4E7E4"], line=dict(color=PANEL, width=2)),
        textinfo="none", domain=dict(x=[0.54, 1.0]),
        hovertemplate="<b>%{label}</b><br>%{value:,} seats<extra></extra>",
    )

    p_pct = elig["programs"] / tot_p * 100
    c_pct = elig["capacity"] / tot_c * 100
    fig.update_layout(annotations=[
        dict(x=0.205, y=0.56, text=f"{p_pct:.0f}%", showarrow=False,
             font=dict(family=FONT_DISPLAY, size=34, color=INK)),
        dict(x=0.205, y=0.38, text=f"{fmt(elig['programs'])} programs",
             showarrow=False, font=dict(family=FONT_UI, size=11, color=INK_SOFT)),
        dict(x=0.795, y=0.56, text=f"{c_pct:.0f}%", showarrow=False,
             font=dict(family=FONT_DISPLAY, size=34, color=INK)),
        dict(x=0.795, y=0.38, text=f"{fmt(elig['capacity'])} seats",
             showarrow=False, font=dict(family=FONT_UI, size=11, color=INK_SOFT)),
    ])
    return style(fig, height=250, margin=dict(l=8, r=8, t=8, b=8))


def chart_days_open(dim):
    d = dim("Days Open Per Week").copy()
    d["category"] = d["category"].astype(int)
    d = d.sort_values("category")

    peak = d["programs"].max()
    colors = [TEAL if v == peak else "#A9BEBC" for v in d["programs"]]

    fig = go.Figure()
    fig.add_bar(
        x=d["category"], y=d["programs"],
        marker=dict(color=colors),
        text=[fmt(v) for v in d["programs"]],
        textposition="outside",
        textfont=dict(family=FONT_UI, size=11, color=INK_SOFT),
        cliponaxis=False,
        hovertemplate="<b>Open %{x} days a week</b>"
                      "<br>%{y:,} programs<extra></extra>",
    )
    fig.update_yaxes(showticklabels=False, type="log", range=[0, 3.9])
    fig.update_xaxes(tickmode="linear", dtick=1,
                     tickfont=dict(size=13, color=INK))
    return style(fig, height=250, margin=dict(l=8, r=8, t=24, b=8))


def build(dim):
    """Return the four Level 1 chart fragments."""
    return dict(
        type=chart_program_type(dim).to_html(**HTML_ARGS),
        level=chart_current_level(dim).to_html(**HTML_ARGS),
        ccdf=chart_ccdf(dim).to_html(**HTML_ARGS),
        days=chart_days_open(dim).to_html(**HTML_ARGS),
    )
