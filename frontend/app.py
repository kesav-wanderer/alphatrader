import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import threading
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _ist_now() -> datetime:
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

from config import WATCHLIST
from frontend.styles import DARK_CSS, action_badge, stat_card, ticker_card, signal_pill
from backend.data.fetcher import fetch_ohlcv, fetch_multiple, fetch_info, get_live_prices, _is_market_hours
from backend.data.indicators import add_indicators, get_indicator_snapshot
from backend.strategies.signal_engine import evaluate_signals, scan_watchlist
from backend.broker.paper_broker import get_portfolio, place_order, get_pnl
from backend.models.predictor import model_available

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AlphaTrader — NSE AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(DARK_CSS, unsafe_allow_html=True)

# ── Auto-scheduler — process-level singleton so multiple browser tabs don't ──
# ── each start their own scheduler (causing duplicate monitor log entries)  ──
_SCHEDULER_LOCK = threading.Lock()
_SCHEDULER_STARTED = threading.Event()

def _start_scheduler():
    with _SCHEDULER_LOCK:
        if _SCHEDULER_STARTED.is_set():
            st.session_state["scheduler"] = True
            return
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
            from backend.broker.auto_trader import morning_scan, monitor_positions

            sched = BackgroundScheduler(timezone="Asia/Kolkata")
            sched.add_job(morning_scan,      CronTrigger(hour=9,  minute=16, day_of_week="mon-fri"), id="morning_scan")
            sched.add_job(monitor_positions, CronTrigger(minute="*/5",       day_of_week="mon-fri"), id="monitor")
            sched.start()
            _SCHEDULER_STARTED.set()
            st.session_state["scheduler"] = True
        except Exception:
            pass

_start_scheduler()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 8px">
        <div style="font-size:22px;font-weight:800;color:#f1f5f9;letter-spacing:-0.5px">
            ⚡ AlphaTrader
        </div>
        <div style="font-size:11px;color:#475569;margin-top:2px">NSE AI Paper Trading</div>
    </div>
    """, unsafe_allow_html=True)

    market_open = _is_market_hours()
    ist_time_str = _ist_now().strftime("%H:%M IST")
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;'
        f'background:{"rgba(16,185,129,0.1)" if market_open else "rgba(239,68,68,0.1)"};'
        f'border:1px solid {"#10b981" if market_open else "#ef4444"};border-radius:8px;margin-bottom:12px">'
        f'<span style="color:{"#10b981" if market_open else "#ef4444"};font-size:8px">●</span>'
        f'<span style="color:{"#6ee7b7" if market_open else "#fca5a5"};font-size:12px;font-weight:600">'
        f'{"Market Open" if market_open else "Market Closed"}</span>'
        f'<span style="color:#475569;font-size:11px;margin-left:auto">{ist_time_str}</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    if model_available():
        st.markdown('<div style="background:rgba(59,130,246,0.1);border:1px solid #3b82f6;border-radius:8px;padding:6px 12px;font-size:12px;color:#93c5fd;margin-bottom:12px">🤖 ML Model Active</div>', unsafe_allow_html=True)

    page = st.radio("", [
        "📊  Dashboard",
        "📈  Stock Analysis",
        "🔍  Scanner",
        "⏱  Backtest",
        "🤖  Auto Trade",
        "💼  Portfolio",
        "⚙️  Settings",
    ], label_visibility="collapsed")
    # strip icon prefix for logic checks below
    page = page.split("  ", 1)[-1]

    st.divider()
    show_debug = st.toggle("Signal Debug", value=False)
    if st.button("↺ Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Scheduler status
    if "scheduler" in st.session_state:
        st.markdown('<div style="color:#475569;font-size:10px;text-align:center;margin-top:8px">⏱ Auto-scheduler active</div>', unsafe_allow_html=True)


# ── Dashboard ─────────────────────────────────────────────────────────────────
if page == "Dashboard":
    st.markdown("<h1>Market Dashboard</h1>", unsafe_allow_html=True)

    # Live ticker strip
    with st.spinner(""):
        live = get_live_prices(WATCHLIST[:15])

    valid = [(s, d) for s, d in live.items() if d.get("price")]
    if valid:
        cols = st.columns(len(valid[:10]))
        for i, (sym, d) in enumerate(valid[:10]):
            with cols[i]:
                st.markdown(ticker_card(sym.replace(".NS",""), d["price"], d.get("change_pct", 0)),
                            unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    with st.spinner("Running AI signal scan..."):
        raw_data = fetch_multiple(WATCHLIST, period="1y")
        enriched, snap_map = {}, {}
        for sym, df in raw_data.items():
            try:
                df_ind     = add_indicators(df)
                snap       = get_indicator_snapshot(df_ind)
                lp         = live.get(sym, {}).get("price")
                if lp: snap["close"] = lp
                enriched[sym] = snap
                snap_map[sym] = df
            except Exception:
                pass

    decisions = scan_watchlist(enriched, raw_frames=snap_map)
    buys  = [d for d in decisions if d.action == "BUY"]
    sells = [d for d in decisions if d.action == "SELL"]

    # Summary bar
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scanned",     len(decisions))
    c2.metric("BUY Signals", len(buys),  delta=f"+{len(buys)}"  if buys  else None)
    c3.metric("SELL Signals",len(sells), delta=f"-{len(sells)}" if sells else None, delta_color="inverse")
    c4.metric("Portfolio",   f"₹{get_portfolio().get('cash',100000):,.0f}", delta="Cash")

    st.divider()
    ml_tag = "🤖 ML Active" if model_available() else "⚙️ Rule-Based"
    st.markdown(f"<h2>Top Picks &nbsp;<span style='font-size:13px;color:#475569'>{ml_tag}</span></h2>", unsafe_allow_html=True)

    rows = []
    for d in decisions:
        snap = enriched.get(d.symbol, {})
        lp   = live.get(d.symbol, {})
        rows.append({
            "Symbol":     d.symbol.replace(".NS",""),
            "Action":     d.action,
            "Score":      d.score,
            "Live Price": f"₹{lp.get('price', snap.get('close',0)):,.2f}" if lp.get("price") else f"₹{snap.get('close',0):.2f}",
            "Change":     f"{lp.get('change_pct',0):+.2f}%" if lp.get("price") else "—",
            "RSI":        f"{snap.get('rsi',0):.1f}" if snap.get("rsi") else "—",
            "ML Prob":    f"{d.ml_proba:.0%}" if d.ml_proba is not None else "—",
            "Target":     f"₹{d.target}" if d.target else "—",
            "Stop Loss":  f"₹{d.stop_loss}" if d.stop_loss else "—",
        })

    df_tbl = pd.DataFrame(rows)
    def _color(val):
        if val == "BUY":  return "background-color:#052e16;color:#6ee7b7;font-weight:700"
        if val == "SELL": return "background-color:#450a0a;color:#fca5a5;font-weight:700"
        return "color:#475569"
    st.dataframe(df_tbl.style.map(_color, subset=["Action"]), use_container_width=True, hide_index=True)

    if show_debug:
        st.markdown("<h2>Signal Debug</h2>", unsafe_allow_html=True)
        for d in decisions[:10]:
            with st.expander(f"{d.symbol.replace('.NS','')} — {d.action}  score={d.score}  ml={f'{d.ml_proba:.0%}' if d.ml_proba else 'N/A'}"):
                pills = "".join(signal_pill(s.name, s.value, s.reason) for s in d.signals)
                st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:4px">{pills}</div>', unsafe_allow_html=True)

    if _is_market_hours():
        time.sleep(300); st.rerun()


# ── Stock Analysis ────────────────────────────────────────────────────────────
elif page == "Stock Analysis":
    st.markdown("<h1>Stock Analysis</h1>", unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    sym    = c1.selectbox("", WATCHLIST, format_func=lambda x: x.replace(".NS",""), label_visibility="collapsed")
    period = c2.select_slider("", ["1mo","3mo","6mo","1y","2y"], value="6mo", label_visibility="collapsed")

    with st.spinner(""):
        try:
            df_raw   = fetch_ohlcv(sym, period=period)
            df       = add_indicators(df_raw)
            snap     = get_indicator_snapshot(df)
            decision = evaluate_signals(sym, snap, df_raw=df_raw)
            info     = fetch_info(sym)
            live_p   = get_live_prices([sym]).get(sym, {})
        except Exception as e:
            st.error(str(e)); st.stop()

    price = live_p.get("price") or snap.get("close", 0)
    chg   = live_p.get("change_pct", 0)
    chg_color = "#10b981" if chg >= 0 else "#ef4444"

    # Header cards
    st.markdown(f"""
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:16px">
        {stat_card("Company",    info.get("name","")[:20],  info.get("sector",""), "#3b82f6")}
        {stat_card("Live Price", f"₹{price:,.2f}", f'<span style="color:{chg_color}">{chg:+.2f}%</span>', chg_color)}
        {stat_card("Day High",   f"₹{live_p.get('day_high',0):,.2f}"  if live_p.get('day_high') else "—", "High", "#f59e0b")}
        {stat_card("Day Low",    f"₹{live_p.get('day_low',0):,.2f}"   if live_p.get('day_low') else "—", "Low", "#ef4444")}
        {stat_card("Decision",   decision.action, f"ML {decision.ml_proba:.0%}" if decision.ml_proba else f"Conf {decision.confidence:.0%}",
                   "#10b981" if decision.action=="BUY" else ("#ef4444" if decision.action=="SELL" else "#475569"))}
    </div>
    """, unsafe_allow_html=True)

    # Chart
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.6,0.2,0.2],
                        vertical_spacing=0.03,
                        subplot_titles=("", "RSI", "MACD"))

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="Price", increasing_line_color="#10b981", decreasing_line_color="#ef4444",
        increasing_fillcolor="#052e16", decreasing_fillcolor="#450a0a"
    ), row=1, col=1)

    for col, color, width in [("EMA_20","#f59e0b",1.2),("EMA_50","#3b82f6",1.2),("EMA_200","#ef4444",1.5)]:
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[col], name=col, line=dict(color=color, width=width)), row=1, col=1)

    if "RSI_14" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI_14"], name="RSI",
                                  line=dict(color="#a78bfa", width=1.5), fill="tozeroy",
                                  fillcolor="rgba(167,139,250,0.05)"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", line_width=1, row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#10b981", line_width=1, row=2, col=1)

    if "MACD_hist" in df.columns:
        bar_c = ["#10b981" if v >= 0 else "#ef4444" for v in df["MACD_hist"]]
        fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist"], name="Hist", marker_color=bar_c, opacity=0.7), row=3, col=1)
    if "MACD" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="#3b82f6",width=1.2)), row=3, col=1)
    if "MACD_signal" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], name="Signal", line=dict(color="#f59e0b",width=1.2)), row=3, col=1)

    fig.update_layout(
        height=680, template="plotly_dark",
        paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
        font=dict(family="Inter", color="#94a3b8"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font_size=11),
        margin=dict(t=20, b=10, l=10, r=10),
        xaxis_rangeslider_visible=False,
    )
    for i in range(1, 4):
        fig.update_xaxes(gridcolor="#1e2a3a", showgrid=True, row=i, col=1)
        fig.update_yaxes(gridcolor="#1e2a3a", showgrid=True, row=i, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # Signal pills
    st.markdown("<h2>Signal Breakdown</h2>", unsafe_allow_html=True)
    pills = "".join(signal_pill(s.name, s.value, s.reason) for s in decision.signals)
    st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:8px">{pills}</div>', unsafe_allow_html=True)

    # Trade panel
    st.divider()
    st.markdown("<h2>Place Paper Trade</h2>", unsafe_allow_html=True)
    p1, p2, p3 = st.columns(3)
    qty   = p1.number_input("Quantity", min_value=1, value=10, step=1)
    tprice = p2.number_input("Price (₹)", value=float(price), step=0.05)
    with p3:
        st.markdown("<br>", unsafe_allow_html=True)
        action_color = "primary" if decision.action == "BUY" else "secondary"
        if st.button(f"Place {decision.action} — {qty} × ₹{tprice:.2f}", type="primary", use_container_width=True):
            trade = place_order(sym, decision.action, qty, tprice,
                                stop_loss=decision.stop_loss, target=decision.target)
            if trade["status"] == "EXECUTED":
                st.success(f"✅ {decision.action} executed  |  SL: ₹{decision.stop_loss}  →  Target: ₹{decision.target}")
            else:
                st.error(f"Rejected: {trade.get('reason')}")


# ── Scanner ───────────────────────────────────────────────────────────────────
elif page == "Scanner":
    st.markdown("<h1>Watchlist Scanner</h1>", unsafe_allow_html=True)

    custom = st.text_area("Symbols (one per line, suffix .NS)", "\n".join(WATCHLIST), height=130)
    symbols = [s.strip() for s in custom.strip().splitlines() if s.strip()]

    if st.button("▶  Run Full Scan", type="primary"):
        prog = st.progress(0)
        raw_data, live_all = {}, {}
        for i, s in enumerate(symbols):
            try:
                df     = fetch_ohlcv(s, period="1y")
                df_ind = add_indicators(df)
                raw_data[s] = get_indicator_snapshot(df_ind)
            except Exception: pass
            prog.progress((i+1)/len(symbols))
        live_all = get_live_prices(symbols)
        prog.empty()

        decisions = scan_watchlist(raw_data)
        rows = []
        for d in decisions:
            snap = raw_data.get(d.symbol, {})
            lp   = live_all.get(d.symbol, {})
            rows.append({
                "Symbol":   d.symbol.replace(".NS",""),
                "Action":   d.action,
                "Score":    d.score,
                "Price":    f"₹{lp.get('price',0):,.2f}" if lp.get("price") else "—",
                "Change":   f"{lp.get('change_pct',0):+.2f}%" if lp.get("price") else "—",
                "RSI":      f"{snap.get('rsi',0):.0f}" if snap.get("rsi") else "—",
                "ML":       f"{d.ml_proba:.0%}" if d.ml_proba else "—",
                "Target":   f"₹{d.target}" if d.target else "—",
                "SL":       f"₹{d.stop_loss}" if d.stop_loss else "—",
                "🟢":       sum(1 for s in d.signals if s.value==1),
                "🔴":       sum(1 for s in d.signals if s.value==-1),
            })

        df_scan = pd.DataFrame(rows)
        def _color(v):
            if v=="BUY":  return "background-color:#052e16;color:#6ee7b7;font-weight:700"
            if v=="SELL": return "background-color:#450a0a;color:#fca5a5;font-weight:700"
            return "color:#475569"
        st.dataframe(df_scan.style.map(_color, subset=["Action"]), use_container_width=True, hide_index=True)

        buys = df_scan[df_scan["Action"]=="BUY"]
        if not buys.empty:
            st.markdown(f'<div style="background:rgba(16,185,129,0.1);border:1px solid #10b981;border-radius:8px;padding:12px 16px;color:#6ee7b7;font-weight:600">🎯 {len(buys)} BUY opportunities found</div>', unsafe_allow_html=True)


# ── Backtest ──────────────────────────────────────────────────────────────────
elif page == "Backtest":
    st.markdown("<h1>Strategy Backtester</h1>", unsafe_allow_html=True)
    st.caption("Validate strategy on 2 years of historical data before trading")

    from backend.backtest.runner import generate_signal_history
    from backend.backtest.engine import run_backtest

    c1, c2, c3, c4 = st.columns(4)
    capital   = c1.number_input("Capital/trade (₹)", value=25000, step=5000)
    target    = c2.slider("Target %", 3, 15, 6) / 100
    sl        = c3.slider("Stop Loss %", 1, 5, 2) / 100
    hold_days = c4.slider("Max hold days", 2, 10, 5)

    custom = st.text_area("Symbols", "\n".join(WATCHLIST), height=100)
    symbols = [s.strip() for s in custom.strip().splitlines() if s.strip()]

    if st.button("▶  Run Backtest", type="primary"):
        results, prog = [], st.progress(0)
        status = st.empty()
        for i, sym in enumerate(symbols):
            status.markdown(f'<div style="color:#64748b;font-size:13px">Testing {sym} ({i+1}/{len(symbols)})...</div>', unsafe_allow_html=True)
            try:
                df_raw  = fetch_ohlcv(sym, period="2y")
                sigs    = generate_signal_history(sym, df_raw)
                if sigs:
                    r = run_backtest(sym, df_raw, sigs, capital, sl, target, hold_days)
                    results.append(r)
            except Exception: pass
            prog.progress((i+1)/len(symbols))
        status.empty(); prog.empty()

        if not results:
            st.error("No results."); st.stop()

        total_pnl   = sum(r.total_pnl   for r in results)
        avg_win     = sum(r.win_rate     for r in results) / len(results)
        avg_sharpe  = sum(r.sharpe       for r in results) / len(results)
        total_trades= sum(r.total_trades for r in results)

        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Total Trades",  total_trades)
        m2.metric("Avg Win Rate",  f"{avg_win:.1f}%",  delta="Profitable" if avg_win>=55 else "Needs tuning")
        m3.metric("Total P&L",     f"₹{total_pnl:,.0f}", delta="+" if total_pnl>0 else "-", delta_color="normal" if total_pnl>0 else "inverse")
        m4.metric("Avg Sharpe",    f"{avg_sharpe:.2f}", delta="Strong" if avg_sharpe>=1.5 else "Moderate")

        st.divider()
        rows = [{"Symbol": r.symbol.replace(".NS",""), "Trades": r.total_trades,
                 "Win %": f"{r.win_rate:.1f}%", "Avg Ret": f"{r.avg_return:+.2f}%",
                 "P&L": f"₹{r.total_pnl:,.0f}", "Max DD": f"{r.max_drawdown:.1f}%",
                 "Sharpe": f"{r.sharpe:.2f}",
                 "Grade": "✅ Strong" if r.win_rate>=55 and r.total_pnl>0 else ("⚠️ Weak" if r.win_rate>=45 else "❌ Poor")}
                for r in sorted(results, key=lambda x: x.total_pnl, reverse=True)]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        best = sorted([r for r in results if r.win_rate>=55 and r.total_pnl>0 and r.total_trades>=3],
                      key=lambda x: x.total_pnl, reverse=True)[:5]
        if best:
            st.markdown("<h2>🎯 Recommended for Paper Trade</h2>", unsafe_allow_html=True)
            for r in best:
                st.markdown(
                    stat_card(r.symbol.replace(".NS",""),
                              f"Win {r.win_rate:.0f}%  |  Avg {r.avg_return:+.1f}%  |  Sharpe {r.sharpe:.2f}",
                              f"₹{r.total_pnl:,.0f} over {r.total_trades} trades",
                              "#10b981"),
                    unsafe_allow_html=True)


# ── Auto Trade ────────────────────────────────────────────────────────────────
elif page == "Auto Trade":
    st.markdown("<h1>Auto Paper Trader</h1>", unsafe_allow_html=True)

    from backend.broker.auto_trader import morning_scan, monitor_positions, CAPITAL_PER_TRADE, MAX_OPEN_POSITIONS, LOG_FILE

    sched_running = "scheduler" in st.session_state
    st.markdown(f"""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px">
        {stat_card("Capital / Trade",    f"₹{CAPITAL_PER_TRADE:,.0f}", "per position", "#3b82f6")}
        {stat_card("Max Positions",      str(MAX_OPEN_POSITIONS), "open at once", "#8b5cf6")}
        {stat_card("Market",             "Open" if _is_market_hours() else "Closed", "IST 9:15–15:30", "#10b981" if _is_market_hours() else "#ef4444")}
        {stat_card("Scheduler",          "Active ✓" if sched_running else "Inactive", "auto-fires 9:16 IST", "#10b981" if sched_running else "#f59e0b")}
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    if sched_running:
        st.markdown('<div style="background:rgba(16,185,129,0.1);border:1px solid #10b981;border-radius:8px;padding:12px 16px;color:#6ee7b7;margin-bottom:16px">⏱ Auto-scheduler is running — morning scan fires at <b>9:16 AM IST</b> on weekdays. Position monitor checks every 5 minutes.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background:rgba(245,158,11,0.1);border:1px solid #f59e0b;border-radius:8px;padding:12px 16px;color:#fcd34d;margin-bottom:16px">⚠ Scheduler not started. Install apscheduler: <code>pip install apscheduler</code> then restart the app.</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    if c1.button("🔍 Run Morning Scan Now", type="primary", use_container_width=True):
        with st.spinner("Scanning watchlist for BUY signals..."):
            morning_scan()
        st.success("Scan complete — check Portfolio for new positions")
        st.rerun()

    if c2.button("📊 Check Positions Now", use_container_width=True):
        with st.spinner("Checking open positions..."):
            monitor_positions()
        st.success("Monitor done — exits placed if SL/target hit")
        st.rerun()

    # ── Manual Force Buy ──────────────────────────────────────────────────────
    st.divider()
    st.markdown("<h2>Manual Force Buy</h2>", unsafe_allow_html=True)
    st.caption("Bypass scan — buy any stock immediately at live price (or override).")

    fb1, fb2, fb3, fb4 = st.columns([3, 1, 1, 2])
    fb_sym  = fb1.selectbox("Stock", WATCHLIST, format_func=lambda x: x.replace(".NS",""), label_visibility="collapsed", key="fb_sym")
    fb_qty  = fb2.number_input("Qty", min_value=1, value=10, step=1, label_visibility="collapsed", key="fb_qty")

    _fb_live = get_live_prices([fb_sym]).get(fb_sym, {})
    _fb_default_price = float(_fb_live.get("price") or 0)
    fb_price = fb3.number_input("Price ₹", min_value=0.05, value=max(_fb_default_price, 0.05), step=0.05, label_visibility="collapsed", key="fb_price")

    with fb4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(f"⚡ Force BUY {fb_sym.replace('.NS','')}", type="primary", use_container_width=True):
            from backend.strategies.signal_engine import evaluate_signals
            from backend.data.indicators import add_indicators, get_indicator_snapshot
            try:
                _df = add_indicators(fetch_ohlcv(fb_sym, period="6mo", use_cache=True))
                _snap = get_indicator_snapshot(_df)
                _dec = evaluate_signals(fb_sym, _snap, df_raw=_df)
                sl, tgt = _dec.stop_loss, _dec.target
            except Exception:
                sl, tgt = round(fb_price * 0.98, 2), round(fb_price * 1.06, 2)

            trade = place_order(fb_sym, "BUY", fb_qty, fb_price, stop_loss=sl, target=tgt)
            if trade["status"] == "EXECUTED":
                st.success(f"✅ Bought {fb_qty} × {fb_sym.replace('.NS','')} @ ₹{fb_price:.2f}  |  SL ₹{sl}  →  Target ₹{tgt}")
            else:
                st.error(f"Rejected: {trade.get('reason')}")
            st.rerun()

    st.divider()
    st.markdown("<h2>Activity Log</h2>", unsafe_allow_html=True)
    import os as _os
    if _os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            lines = f.readlines()
        st.code("".join(lines[-40:][::-1]), language=None)
        if st.button("Clear Log"):
            open(LOG_FILE, "w").close(); st.rerun()
    else:
        st.markdown('<div style="color:#475569;text-align:center;padding:32px">No activity yet. Run Morning Scan to start.</div>', unsafe_allow_html=True)


# ── Portfolio ─────────────────────────────────────────────────────────────────
elif page == "Portfolio":
    st.markdown("<h1>Paper Portfolio</h1>", unsafe_allow_html=True)

    portfolio = get_portfolio()
    positions = portfolio.get("positions", {})
    trades    = portfolio.get("trades", [])
    cash      = portfolio.get("cash", 100000.0)

    # ── Buttons ──────────────────────────────────────────────────────────────
    btn_col1, btn_col2 = st.columns([1, 5])
    load_live = btn_col1.button("↺ Load Live Prices", type="primary", use_container_width=True)

    if not positions:
        st.markdown('<div style="color:#475569;text-align:center;padding:48px 0;font-size:16px">No open positions.<br><span style="font-size:13px">Go to Auto Trade → Run Morning Scan, or Stock Analysis to place manually.</span></div>', unsafe_allow_html=True)
        st.metric("Available Cash", f"₹{cash:,.2f}")
    else:
        # ── Step 1: always render positions from portfolio JSON (instant) ────
        total_invested = sum(p["qty"] * p["avg_price"] for p in positions.values())

        # ── Step 2: optionally fetch live prices when button is clicked ──────
        current_prices = {}
        price_status   = "entry prices shown"
        if load_live or st.session_state.get("portfolio_live_loaded"):
            st.session_state["portfolio_live_loaded"] = True
            with st.spinner("Fetching live prices..."):
                try:
                    raw = get_live_prices(list(positions.keys()))
                    current_prices = {s: d["price"] for s, d in raw.items()
                                      if d.get("price") is not None}
                    price_status = f"live prices — {len(current_prices)}/{len(positions)} stocks updated"
                except Exception as ex:
                    price_status = f"price fetch failed: {ex}"

        # ── Summary cards ─────────────────────────────────────────────────────
        total_current = sum(
            positions[s]["qty"] * (current_prices.get(s) or positions[s]["avg_price"])
            for s in positions
        )
        total_pnl     = total_current - total_invested
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0
        pnl_color     = "#10b981" if total_pnl >= 0 else "#ef4444"

        st.markdown(f"""
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px">
            {stat_card("Cash",          f"₹{cash:,.2f}",           "available",      "#3b82f6")}
            {stat_card("Invested",      f"₹{total_invested:,.2f}", "deployed",        "#8b5cf6")}
            {stat_card("Current Value", f"₹{total_current:,.2f}",  price_status,      "#f59e0b")}
            {stat_card("Total P&L",     f"₹{total_pnl:,.2f}",      f"{total_pnl_pct:+.2f}%", pnl_color)}
        </div>
        """, unsafe_allow_html=True)

        # ── Positions table ───────────────────────────────────────────────────
        rows = []
        for sym, pos in positions.items():
            entry   = float(pos["avg_price"])
            qty     = int(pos["qty"])
            live_p  = current_prices.get(sym)
            cur     = float(live_p) if live_p else entry
            invested= qty * entry
            cur_val = qty * cur
            pnl_amt = round(cur_val - invested, 2)
            pnl_pct = round((pnl_amt / invested * 100) if invested else 0, 2)
            sl      = pos.get("stop_loss")
            tgt     = pos.get("target")
            rows.append({
                "Stock":      sym.replace(".NS",""),
                "Qty":        qty,
                "Entry":      round(entry, 2),
                "Current":    round(cur, 2) if live_p else None,
                "Invested":   round(invested, 2),
                "Value":      round(cur_val, 2),
                "P&L ₹":      pnl_amt,
                "P&L %":      pnl_pct,
                "SL":         sl,
                "Target":     tgt,
            })

        df_pos = pd.DataFrame(rows)
        st.dataframe(df_pos, use_container_width=True, hide_index=True)
        if not current_prices:
            st.caption("Current column shows entry price — click 'Load Live Prices' to update")

    # ── Trade History ─────────────────────────────────────────────────────────
    if trades:
        st.divider()
        st.markdown("<h2>Trade History</h2>", unsafe_allow_html=True)
        df_trades = pd.DataFrame(trades).iloc[::-1].reset_index(drop=True)
        keep = [c for c in ["timestamp","symbol","action","qty","price","cost","status","reason"] if c in df_trades.columns]
        st.dataframe(df_trades[keep], use_container_width=True, hide_index=True)
    else:
        st.caption("No trades yet.")


# ── Settings ──────────────────────────────────────────────────────────────────
elif page == "Settings":
    st.markdown("<h1>Settings</h1>", unsafe_allow_html=True)

    st.markdown("<h2>Kite Connect (Zerodha)</h2>", unsafe_allow_html=True)
    st.info("Only needed for live trading. Paper trade works without API keys.")

    api_key    = st.text_input("API Key",    type="password", placeholder="your_api_key")
    api_secret = st.text_input("API Secret", type="password", placeholder="your_api_secret")

    if st.button("Save API Keys", type="primary"):
        env_path = os.path.join(os.path.dirname(__file__), "../.env")
        existing = {}
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        existing[k] = v
        existing.update({"KITE_API_KEY": api_key, "KITE_API_SECRET": api_secret})
        with open(env_path, "w") as f:
            [f.write(f"{k}={v}\n") for k, v in existing.items()]
        st.success("Saved to .env")

    st.divider()
    st.markdown("<h2>Signal Engine Thresholds</h2>", unsafe_allow_html=True)
    st.markdown(stat_card("Edit config.py",
                           "MIN_SIGNALS_TO_BUY = 4",
                           "STOP_LOSS_PCT=0.02 | TARGET_PCT=0.06 | RISK_PER_TRADE=0.02",
                           "#3b82f6"), unsafe_allow_html=True)
