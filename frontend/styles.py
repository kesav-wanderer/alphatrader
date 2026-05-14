DARK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Base ── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #080c14; color: #e2e8f0; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid #1e2a3a;
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }

/* ── Nav — hide radio circles, style as nav links ── */
[data-testid="stSidebar"] .stRadio > div {
    display: flex !important;
    flex-direction: column !important;
    gap: 2px !important;
}
[data-testid="stSidebar"] .stRadio label {
    display: flex !important;
    align-items: center !important;
    padding: 10px 14px !important;
    border-radius: 8px !important;
    border-left: 3px solid transparent !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
    margin: 1px 0 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #64748b !important;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: #1e2a3a !important;
    color: #e2e8f0 !important;
    border-left-color: #3b82f6 !important;
}
/* Hide the actual radio circle dot */
[data-testid="stSidebar"] .stRadio label > div:first-child {
    display: none !important;
}
/* Selected state */
[data-testid="stSidebar"] .stRadio label[data-checked="true"] {
    background: #1e293b !important;
    color: #f1f5f9 !important;
    border-left-color: #3b82f6 !important;
}
[data-testid="stSidebar"] .stRadio [aria-checked="true"] ~ div,
[data-testid="stSidebar"] .stRadio input:checked + div + div span {
    color: #f1f5f9 !important;
}
/* Wipe the widget label above the radio group */
[data-testid="stSidebar"] .stRadio > label { display: none !important; }

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: #0d1117;
    border: 1px solid #1e2a3a;
    border-radius: 12px;
    padding: 16px !important;
    transition: border-color 0.2s;
}
[data-testid="stMetric"]:hover { border-color: #3b82f6; }
[data-testid="stMetricLabel"] { color: #64748b !important; font-size: 12px !important; text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 24px !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"] svg { display: none; }
[data-testid="stMetricDelta"] > div { font-size: 12px !important; font-weight: 600; }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
    color: white !important; border: none !important;
    border-radius: 8px !important; font-weight: 600 !important;
    padding: 8px 20px !important; transition: all 0.2s !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #2563eb, #3b82f6) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(59,130,246,0.4) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #059669, #10b981) !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #10b981, #34d399) !important;
    box-shadow: 0 4px 15px rgba(16,185,129,0.4) !important;
}

/* ── DataFrames / Tables ── */
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
[data-testid="stDataFrame"] iframe { background: #0d1117 !important; }
.dvn-scroller { background: #0d1117 !important; }

/* ── Inputs & Selects ── */
.stSelectbox > div > div, .stNumberInput > div > div > input, .stTextArea textarea {
    background: #0d1117 !important;
    border: 1px solid #1e2a3a !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}
.stSelectbox > div > div:focus-within, .stNumberInput > div > div > input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.2) !important;
}

/* ── Divider ── */
hr { border-color: #1e2a3a !important; margin: 16px 0 !important; }

/* ── Titles ── */
h1 { color: #f1f5f9 !important; font-weight: 700 !important; font-size: 28px !important; }
h2 { color: #e2e8f0 !important; font-weight: 600 !important; font-size: 20px !important; }
h3 { color: #cbd5e1 !important; font-weight: 600 !important; }

/* ── Alerts ── */
.stSuccess { background: rgba(16,185,129,0.1) !important; border: 1px solid #10b981 !important; border-radius: 8px !important; color: #6ee7b7 !important; }
.stError   { background: rgba(239,68,68,0.1)  !important; border: 1px solid #ef4444 !important; border-radius: 8px !important; color: #fca5a5 !important; }
.stWarning { background: rgba(245,158,11,0.1) !important; border: 1px solid #f59e0b !important; border-radius: 8px !important; color: #fcd34d !important; }
.stInfo    { background: rgba(59,130,246,0.1) !important; border: 1px solid #3b82f6 !important; border-radius: 8px !important; color: #93c5fd !important; }

/* ── Progress bar ── */
.stProgress > div > div { background: linear-gradient(90deg, #1d4ed8, #10b981) !important; border-radius: 4px; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: #3b82f6 !important; }

/* ── Code blocks ── */
.stCode { background: #0d1117 !important; border: 1px solid #1e2a3a !important; border-radius: 8px !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { background: #0d1117; border-radius: 10px; padding: 4px; }
.stTabs [data-baseweb="tab"] { color: #64748b !important; border-radius: 8px; }
.stTabs [aria-selected="true"] { background: #1e2a3a !important; color: #f1f5f9 !important; }

/* ── Expander ── */
.streamlit-expanderHeader { background: #0d1117 !important; border: 1px solid #1e2a3a !important; border-radius: 8px !important; color: #e2e8f0 !important; }
.streamlit-expanderContent { background: #080c14 !important; border: 1px solid #1e2a3a !important; border-top: none !important; }

/* ── Toggle ── */
.stToggle > label { color: #94a3b8 !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #080c14; }
::-webkit-scrollbar-thumb { background: #1e2a3a; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #2d3f55; }
</style>
"""

def action_badge(action: str) -> str:
    colors = {
        "BUY":  ("rgba(16,185,129,0.15)", "#10b981", "#6ee7b7"),
        "SELL": ("rgba(239,68,68,0.15)",  "#ef4444", "#fca5a5"),
        "HOLD": ("rgba(100,116,139,0.15)","#475569", "#94a3b8"),
    }
    bg, border, text = colors.get(action, colors["HOLD"])
    return f'<span style="background:{bg};border:1px solid {border};color:{text};padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700">{action}</span>'


def stat_card(label: str, value: str, sub: str = "", color: str = "#3b82f6") -> str:
    return f"""
    <div style="background:#0d1117;border:1px solid #1e2a3a;border-left:3px solid {color};
                border-radius:10px;padding:16px 20px;margin:4px 0">
        <div style="color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px">{label}</div>
        <div style="color:#f1f5f9;font-size:22px;font-weight:700">{value}</div>
        {f'<div style="color:#64748b;font-size:12px;margin-top:4px">{sub}</div>' if sub else ''}
    </div>"""


def ticker_card(symbol: str, price: float, change_pct: float) -> str:
    color  = "#10b981" if change_pct >= 0 else "#ef4444"
    arrow  = "▲" if change_pct >= 0 else "▼"
    bg     = "rgba(16,185,129,0.05)" if change_pct >= 0 else "rgba(239,68,68,0.05)"
    border = "rgba(16,185,129,0.2)"  if change_pct >= 0 else "rgba(239,68,68,0.2)"
    return f"""
    <div style="background:{bg};border:1px solid {border};border-radius:10px;
                padding:12px 16px;text-align:center;min-width:120px">
        <div style="color:#94a3b8;font-size:11px;font-weight:600;margin-bottom:4px">{symbol}</div>
        <div style="color:#f1f5f9;font-size:16px;font-weight:700">₹{price:,.2f}</div>
        <div style="color:{color};font-size:12px;font-weight:600">{arrow} {abs(change_pct):.2f}%</div>
    </div>"""


def signal_pill(name: str, value: int, reason: str) -> str:
    if value == 1:
        bg, border, text, icon = "rgba(16,185,129,0.1)", "#10b981", "#6ee7b7", "●"
    elif value == -1:
        bg, border, text, icon = "rgba(239,68,68,0.1)", "#ef4444", "#fca5a5", "●"
    else:
        bg, border, text, icon = "rgba(100,116,139,0.1)", "#475569", "#94a3b8", "●"
    return f"""
    <div style="background:{bg};border:1px solid {border};border-radius:8px;padding:10px 14px;margin:4px">
        <div style="color:{text};font-size:11px;font-weight:700">{icon} {name}</div>
        <div style="color:#64748b;font-size:10px;margin-top:4px">{reason}</div>
    </div>"""
