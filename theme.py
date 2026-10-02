"""Shared design tokens and Plotly helpers for the OECOSL dashboard."""

# ---------------------------------------------------------------- palette
PAPER = "#F6F7F5"      # page ground — faint warm grey-green
INK = "#1C2B2D"        # deep slate-teal, primary text
INK_SOFT = "#5A6B6C"   # secondary text
RULE = "#D5DAD6"       # hairlines
PANEL = "#FFFFFF"      # chart ground

TEAL = "#2F6B6E"
OCHRE = "#B98A3C"
PLUM = "#7C6A8A"
CLAY = "#9E5F52"
MOSS = "#5E7A52"
STONE = "#8A9193"

TYPE_COLORS = [TEAL, OCHRE, PLUM, CLAY, MOSS, STONE]
LEVEL_COLORS = [STONE, "#8FB3B0", "#5E9490", TEAL, "#1F4F52"]

FONT_DISPLAY = "Newsreader, Georgia, serif"
FONT_UI = "Archivo, -apple-system, Segoe UI, sans-serif"

HTML_ARGS = dict(full_html=False, include_plotlyjs=False,
                 config={"displayModeBar": False, "responsive": True})


def fmt(n, dp=0):
    return f"{n:,.{dp}f}"


def style(fig, height=340, showlegend=False, margin=None):
    """Apply the shared chart styling."""
    fig.update_layout(
        height=height,
        showlegend=showlegend,
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(family=FONT_UI, size=12, color=INK_SOFT),
        margin=margin or dict(l=8, r=8, t=8, b=8),
        hoverlabel=dict(
            bgcolor=INK,
            font=dict(family=FONT_UI, size=12, color="#FFFFFF"),
            bordercolor=INK,
        ),
        bargap=0.34,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, showline=False,
                     ticks="", color=INK_SOFT)
    fig.update_yaxes(showgrid=False, zeroline=False, showline=False,
                     ticks="", color=INK_SOFT)
    return fig
