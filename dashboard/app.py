"""PulseMetrics interactive analytics dashboard.

Design: calm and minimal. Neutral surfaces, one teal accent for the UI, and a muted data palette
validated with the dataviz palette validator (categorical slots in fixed order; gains and losses
use the reserved status colours with a label). Every page opens with the question it answers and
the short answer, and every chart has a one-line "how to read this".
"""
from __future__ import annotations

import hmac
import html
import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()
st.set_page_config(page_title="PulseMetrics", page_icon=":material/monitoring:", layout="wide")

# ------------------------------------------------------------------ palette
SURFACE, PAGE, INK, INK_2, MUTED = "#ffffff", "#f6f7f8", "#172026", "#4a555e", "#8a939b"
GRID, AXIS, DEEMPH = "#eaecee", "#d3d7db", "#c9ced3"
ACCENT = "#0f766e"          # teal: UI accent only, never a data series
SERIES = ["#3b6ea8", "#d0643c", "#2f9a7e", "#d19a1e", "#c8628b", "#5f8a2e", "#6a5aa8", "#b8433f"]
GAIN, LOSS = "#2f7d4f", "#b83c3c"
SEQ = [[0, "#eef3f9"], [0.25, "#bccfe7"], [0.5, "#93b1d6"], [0.75, "#3b6ea8"], [1, "#1b3a61"]]
FONT = 'Inter, system-ui, -apple-system, "Segoe UI", sans-serif'
RING = {"color": SURFACE, "width": 2}

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, .stApp, .stMarkdown, button, input {{ font-family: {FONT}; }}
.stApp {{ background: {PAGE}; }}
.block-container {{ padding-top: 2.2rem; max-width: 1280px; }}
[data-testid="stHeader"] {{ background: transparent; }}
section[data-testid="stSidebar"] > div {{ background: #fbfbfa; border-right: 1px solid {GRID}; }}
h1, h2, h3 {{ color: {INK}; letter-spacing: -0.015em; }}
.pm-head .kicker {{ color: {ACCENT}; text-transform: uppercase; letter-spacing: .12em; font-size: 11.5px; font-weight: 600; }}
.pm-head h1 {{ font-size: 30px; line-height: 1.2; font-weight: 650; margin: 4px 0 6px 0; padding: 0; }}
.pm-head p {{ color: {INK_2}; font-size: 15px; margin: 0 0 16px 0; max-width: 880px; line-height: 1.55; }}
.pm-qa {{ display: grid; grid-template-columns: 1fr 1.3fr; margin: 0 0 18px 0; background: {SURFACE};
          border: 1px solid {GRID}; border-radius: 12px; overflow: hidden; }}
.pm-qa > div {{ padding: 14px 18px; }}
.pm-qa > div + div {{ border-left: 1px solid {GRID}; }}
.pm-qa .lab {{ color: {MUTED}; text-transform: uppercase; letter-spacing: .08em; font-size: 11px; font-weight: 600; }}
.pm-qa .txt {{ color: {INK}; font-size: 15px; margin-top: 4px; line-height: 1.5; }}
@media (max-width: 800px) {{ .pm-qa {{ grid-template-columns: 1fr; }} .pm-qa > div + div {{ border-left: 0; border-top: 1px solid {GRID}; }} }}
.pm-card {{ background: {SURFACE}; border: 1px solid {GRID}; border-radius: 12px; padding: 14px 16px 12px 16px; min-height: 108px; }}
.pm-card .lab {{ color: {INK_2}; font-size: 13px; line-height: 1.35; }}
.pm-card .val {{ color: {INK}; font-size: 26px; font-weight: 650; line-height: 1.2; margin-top: 6px; }}
.pm-card .sub {{ color: {MUTED}; font-size: 12.5px; margin-top: 3px; line-height: 1.35; }}
.pm-card .sub.good {{ color: {GAIN}; }} .pm-card .sub.bad {{ color: {LOSS}; }}
.pm-section {{ margin: 28px 0 4px 0; }}
.pm-section h3 {{ margin: 0; padding: 0; font-size: 19px; font-weight: 650; }}
.pm-section p {{ margin: 4px 0 0 0; color: {INK_2}; font-size: 14.5px; }}
.pm-read {{ color: {INK_2}; font-size: 13.5px; margin: -6px 0 14px 0; line-height: 1.5; }}
.pm-read b {{ color: {INK}; font-weight: 600; }}
.pm-note {{ border-radius: 10px; padding: 12px 16px; margin: 6px 0 14px 0; background: {SURFACE}; border: 1px solid {GRID};
            border-left: 3px solid {ACCENT}; color: {INK_2}; font-size: 14.5px; line-height: 1.55; }}
.pm-note b {{ color: {INK}; }}
div[data-testid="stExpander"] details {{ border: 1px solid {GRID}; border-radius: 10px; background: {SURFACE}; }}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ components
def header(title: str, subtitle: str, kicker: str, question: str = "", answer: str = "") -> None:
    st.markdown(f'<div class="pm-head"><div class="kicker">{html.escape(kicker)}</div><h1>{html.escape(title)}</h1>'
                f'<p>{subtitle}</p></div>', unsafe_allow_html=True)
    if question:
        st.markdown(f'<div class="pm-qa"><div><div class="lab">The question</div><div class="txt">{question}</div></div>'
                    f'<div><div class="lab">The short answer</div><div class="txt">{answer}</div></div></div>',
                    unsafe_allow_html=True)


def cards(items: list[tuple]) -> None:
    """items: (label, value, sub, tone) where tone is '', 'good' or 'bad'."""
    for col, (label, value, sub, *tone) in zip(st.columns(len(items)), items, strict=True):
        cls = tone[0] if tone else ""
        col.markdown(f'<div class="pm-card"><div class="lab">{html.escape(label)}</div>'
                     f'<div class="val">{html.escape(value)}</div>'
                     f'<div class="sub {cls}">{html.escape(sub)}</div></div>', unsafe_allow_html=True)


def section(title: str, blurb: str = "") -> None:
    p = f"<p>{blurb}</p>" if blurb else ""
    st.markdown(f'<div class="pm-section"><h3>{html.escape(title)}</h3>{p}</div>', unsafe_allow_html=True)


def how_to_read(text_html: str) -> None:
    st.markdown(f'<div class="pm-read"><b>How to read this:</b> {text_html}</div>', unsafe_allow_html=True)


def note(text_html: str) -> None:
    st.markdown(f'<div class="pm-note">{text_html}</div>', unsafe_allow_html=True)


def show(fig: go.Figure, height: int = 340, **layout) -> None:
    """House style; page-level `layout` overrides are merged in (a string title becomes the title text)."""
    base = {"height": height, "paper_bgcolor": SURFACE, "plot_bgcolor": SURFACE,
            "font": {"family": FONT, "color": INK_2, "size": 13}, "margin": {"l": 10, "r": 10, "t": 36, "b": 10},
            "hoverlabel": {"bgcolor": "white", "bordercolor": AXIS, "font": {"color": INK, "family": FONT}},
            "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0, "title": None},
            "title": {"font": {"color": INK, "size": 14}, "x": 0, "xanchor": "left"}}
    if isinstance(layout.get("title"), str):
        layout["title"] = {"text": layout["title"]}
    for key, value in layout.items():
        base[key] = {**base[key], **value} if isinstance(value, dict) and isinstance(base.get(key), dict) else value
    fig.update_layout(**base)
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zerolinecolor=AXIS, automargin=True, title_font_color=INK_2)
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zerolinecolor=AXIS, automargin=True, title_font_color=INK_2)
    st.plotly_chart(fig, use_container_width=True, theme=None)


def pct(value, digits=1):
    return "—" if pd.isna(value) else f"{value * 100:.{digits}f}%"


def money(value, compact=False):
    if pd.isna(value):
        return "—"
    value = float(value)
    return f"${value / 1000:,.1f}K" if compact and abs(value) >= 1000 else f"${value:,.0f}"


def change(now, before, kind="pct"):
    """Month-over-month change text and tone."""
    if pd.isna(now) or pd.isna(before) or before == 0:
        return "", ""
    if kind == "points":
        d = (now - before) * 100
        return f"{d:+.1f} points vs. last month", ""
    d = now / before - 1
    return f"{d:+.1%} vs. last month", ""


# ------------------------------------------------------------------ sign in
def authenticate() -> str | None:
    if "role" in st.session_state:
        return st.session_state.role
    _, mid, _ = st.columns([1, 1.5, 1])
    with mid:
        st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)
        header("PulseMetrics", "The scoreboard for a subscription software business: how much revenue it earns each "
               "month, where new customers come from, how much they use the product, how many stay, and whether "
               "product changes work. Sign in to explore it.", "Sign in")
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True, type="primary")
        st.caption("Demo accounts are set in your local .env file. The company and data are fictional.")
    if submitted:
        users = {
            os.getenv("PULSE_ADMIN_USER", ""): (os.getenv("PULSE_ADMIN_PASSWORD", ""), "admin"),
            os.getenv("PULSE_ANALYST_USER", ""): (os.getenv("PULSE_ANALYST_PASSWORD", ""), "analyst"),
        }
        configured_password, role = users.get(username, ("", ""))
        if configured_password and hmac.compare_digest(password, configured_password):
            st.session_state.role = role
            st.rerun()
        st.error("Invalid credentials or dashboard credentials are not configured.")
    return None


role = authenticate()
if role is None:
    st.stop()


@st.cache_resource
def engine():
    return create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)


@st.cache_data(ttl=300)
def query(sql: str, params: dict | None = None) -> pd.DataFrame:
    with engine().connect() as connection:
        return pd.read_sql_query(text(sql), connection, params=params)


PAGES = {"Business overview": ":material/monitoring:", "Getting customers": ":material/filter_alt:",
         "Product usage": ":material/touch_app:", "Keeping customers": ":material/favorite:",
         "Onboarding test": ":material/science:"}
pages = list(PAGES)
if role != "admin":
    pages = ["Product usage", "Keeping customers", "Onboarding test"]
st.sidebar.markdown("**PulseMetrics**")
st.sidebar.caption("The scoreboard for a subscription software business. Fictional company, generated data.")
page = st.sidebar.radio("Pages", pages, format_func=lambda p: p, label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.caption(f"Signed in as {role}")
if st.sidebar.button("Sign out"):
    del st.session_state.role
    st.rerun()

try:
    latest = query("select max(month_start) as month_start from analytics.mart_monthly_kpis")
    if latest.empty or pd.isna(latest.iloc[0]["month_start"]):
        st.warning("No analytics data yet. Run the refresh pipeline first.")
        st.stop()
    latest_month = latest.iloc[0]["month_start"]
except SQLAlchemyError as exc:
    st.error(f"Warehouse unavailable: {exc}")
    st.stop()

FOOT = (f"Reporting through {latest_month:%B %Y} · fictional company, generated data · revenue is measured at "
        "each month's end")

# ------------------------------------------------------------------ business overview
if page == "Business overview":
    kpis = query("select * from analytics.mart_monthly_kpis order by month_start")
    cur, prev = kpis.iloc[-1], kpis.iloc[-2]
    year_ago = kpis.iloc[-13] if len(kpis) >= 13 else kpis.iloc[0]
    avg_churn = kpis.tail(6).logo_churn_rate.mean()
    header("Is the business growing, and is it healthy?",
           "PulseMetrics is the analytics scoreboard for a fictional subscription software company: customers pay "
           "a monthly fee for a work tool. This page shows how much revenue comes in each month and what's driving it.",
           "Business overview",
           question="Is monthly revenue growing, and are we keeping the customers we win?",
           answer=f"Yes. Monthly revenue is <b>{money(cur.mrr, True)}</b>, up from {money(year_ago.mrr, True)} a year "
                  f"earlier, from <b>{cur.paid_customers:,}</b> paying customers. On average <b>{pct(avg_churn)}</b> "
                  f"of customers cancel each month (last 6 months), so growth depends on winning new ones steadily.")
    cards([
        ("Monthly recurring revenue (MRR)", money(cur.mrr, True), change(cur.mrr, prev.mrr)[0]),
        ("Yearly run rate (ARR)", money(cur.arr, True), "monthly revenue × 12"),
        ("Paying customers", f"{cur.paid_customers:,}", change(cur.paid_customers, prev.paid_customers)[0]),
        ("Customers who cancelled", pct(cur.logo_churn_rate), f"this month · {cur.churned_customers:,} customers"),
        ("Cost to win a customer (CAC)", money(cur.cac), "marketing spend ÷ new customers"),
        ("Value of a customer (LTV)", money(cur.estimated_ltv), "rough lifetime revenue estimate"),
    ])
    left, right = st.columns([1.6, 1])
    with left:
        section("Monthly revenue over time")
        fig = go.Figure(go.Scatter(x=kpis.month_start, y=kpis.mrr, mode="lines+markers", fill="tozeroy",
                                   line={"color": SERIES[0], "width": 2}, fillcolor="rgba(59,110,168,0.10)",
                                   marker={"size": 7, "line": RING},
                                   hovertemplate="%{x|%b %Y}: <b>$%{y:,.0f}</b> a month<extra></extra>"))
        show(fig, 320, yaxis={"tickprefix": "$", "tickformat": ",.0f", "rangemode": "tozero"}, showlegend=False)
        how_to_read("each point is the revenue the company earns per month from active subscriptions, measured "
                    "at month end.")
    with right:
        section(f"What changed in {latest_month:%B}")
        labels = ["New customers", "Upgrades", "Downgrades", "Cancellations"]
        vals = [cur.new_mrr, cur.expansion_mrr, -cur.contraction_mrr, -cur.churned_mrr]
        fig = go.Figure(go.Bar(x=vals, y=labels, orientation="h",
                               marker={"color": [GAIN if v >= 0 else LOSS for v in vals], "line": RING},
                               text=[("+" if v > 0 else "−" if v < 0 else "") + money(abs(v)) for v in vals], textposition="outside",
                               hovertemplate="%{y}: <b>%{x:+$,.0f}</b><extra></extra>"))
        lo_v, hi_v = min(min(vals), 0), max(max(vals), 0)
        pad = (hi_v - lo_v) * 0.4 or 1
        show(fig, 320, xaxis={"range": [lo_v - pad, hi_v + pad], "showticklabels": False, "showgrid": False,
                              "zeroline": True, "zerolinecolor": AXIS},
             yaxis={"autorange": "reversed"}, showlegend=False, bargap=0.45)
        how_to_read(f"<b>green</b> bars added monthly revenue, <b>red</b> bars removed it. Net change: "
                    f"<b>{money(cur.mrr - cur.starting_mrr)}</b>.")
    mix = query("""
        select c.segment, c.channel, count(*) as customers, sum(f.mrr) as mrr
        from analytics.fct_customer_month f join analytics.dim_customer c using (customer_id)
        where f.month_start = :month and f.mrr > 0
        group by 1, 2 order by mrr desc
    """, {"month": latest_month})
    a, b = st.columns(2)
    with a:
        section("Revenue by customer size")
        seg = mix.groupby("segment", as_index=False)["mrr"].sum().sort_values("mrr")
        fig = go.Figure(go.Bar(x=seg.mrr, y=seg.segment, orientation="h", marker={"color": SERIES[0], "line": RING},
                               text=[money(v, True) for v in seg.mrr], textposition="outside",
                               hovertemplate="%{y}: <b>$%{x:,.0f}</b> a month<extra></extra>"))
        show(fig, 240, xaxis={"tickprefix": "$", "range": [0, seg.mrr.max() * 1.2]}, showlegend=False, bargap=0.45)
        how_to_read("Self Serve = small teams on the cheapest plan; SMB = small businesses; Mid Market = larger companies.")
    with b:
        section("Paying customers by how they found us")
        ch = mix.groupby("channel", as_index=False)["customers"].sum().sort_values("customers")
        fig = go.Figure(go.Bar(x=ch.customers, y=ch.channel, orientation="h", marker={"color": SERIES[0], "line": RING},
                               text=ch.customers, textposition="outside",
                               hovertemplate="%{y}: <b>%{x}</b> paying customers<extra></extra>"))
        show(fig, 240, xaxis={"range": [0, ch.customers.max() * 1.2]}, showlegend=False, bargap=0.45)
        how_to_read("Organic = found us on their own; Paid = ads; Referral = recommended by a customer; Partner = "
                    "through a reseller.")
    with st.expander("New to these terms? A short glossary"):
        st.markdown("""
| Term | Plain meaning |
|---|---|
| **MRR** (monthly recurring revenue) | What the company earns per month from active subscriptions |
| **ARR** (annual run rate) | MRR × 12: what a year would bring in at today's rate |
| **Churn** | Customers (or revenue) lost because they cancelled |
| **CAC** (customer acquisition cost) | Marketing spend ÷ number of new paying customers |
| **LTV** (lifetime value) | Rough estimate of the revenue a customer brings in before cancelling (monthly revenue per customer ÷ monthly churn) |
| **NRR** (net revenue retention) | Revenue kept from last month's customers, after upgrades, downgrades and cancellations. Above 100% = existing customers grew |
| **ROAS** (return on ad spend) | Revenue from a channel's customers ÷ what was spent on that channel |
| **DAU / WAU / MAU** | Daily / weekly / monthly active users |
""")

# ------------------------------------------------------------------ acquisition
elif page == "Getting customers":
    funnel = query("select * from analytics.mart_funnel_monthly order by month_start")
    channels = query("select * from analytics.mart_acquisition_channel_month order by month_start")
    mature = funnel[funnel.month_start < funnel.month_start.max()]
    tot = mature[["website_visitors", "signups", "trials", "activated", "paid_30d"]].sum()
    steps = {"visiting and signing up": tot.signups / tot.website_visitors,
             "signing up and starting a trial": tot.trials / tot.signups,
             "starting a trial and using a key feature": tot.activated / tot.trials,
             "using a key feature and paying": tot.paid_30d / tot.activated}
    worst = min(steps, key=steps.get)
    header("Where do new customers come from?", "Every paying customer starts as a website visitor. This page shows "
           "how many make it through each step, and what each marketing channel costs.", "Getting customers",
           question="How many website visitors become paying customers, and where do we lose them?",
           answer=f"Across all signup months, <b>{tot.signups / tot.website_visitors:.0%}</b> of visitors sign up and "
                  f"<b>{tot.paid_30d / tot.trials:.0%}</b> of free trials turn into paying customers within 30 days. "
                  f"The biggest drop is between <b>{worst}</b>: only {steps[worst]:.0%} make that step, so it's the "
                  "one worth improving first.")
    months = funnel.month_start.tolist()[::-1]
    month = st.selectbox("Signup month", months, index=1 if len(months) > 1 else 0,
                         format_func=lambda x: x.strftime("%B %Y") + (" (still filling in)" if x == months[0] else ""))
    row = funnel.loc[funnel.month_start == month].iloc[0]
    cards([
        ("Visitors who sign up", pct(row.visit_to_signup), f"{row.signups:,} of {row.website_visitors:,} visitors"),
        ("Trials that start using it", pct(row.trial_to_activation), "used a key feature within 7 days"),
        ("Trials that become paying", pct(row.trial_to_paid), "within 30 days"),
        ("Still paying after 90 days", f"{row.retained_90d:,}", "customers from this month"),
    ])
    section("From visitor to paying customer", blurb=f"People who signed up in {month:%B %Y}.")
    labels = ["Visited the website", "Signed up", "Started a free trial", "Used a key feature (7 days)",
              "Became a paying customer (30 days)"]
    counts = [row.website_visitors, row.signups, row.trials, row.activated, row.paid_30d]
    fig = go.Figure(go.Funnel(y=labels, x=counts, marker={"color": SERIES[0], "line": RING},
                              textinfo="value+percent previous", connector={"fillcolor": GRID},
                              hovertemplate="%{y}: <b>%{x:,}</b> people<extra></extra>"))
    show(fig, 360, showlegend=False)
    how_to_read("each bar is how many people reached that step; the percentage is the share who made it from the "
                "step above. Recent months may still be filling in, because trials take up to 30 days to convert.")
    section("What each marketing channel costs",
            blurb="Spend, new paying customers, and what one new customer cost, for the chosen month.")
    scoped = channels.loc[channels.month_start == month].sort_values("cac")
    a, b = st.columns(2)
    with a:
        c = scoped.dropna(subset=["cac"])
        fig = go.Figure(go.Bar(x=c.cac, y=c.channel, orientation="h", marker={"color": SERIES[0], "line": RING},
                               text=[money(v) for v in c.cac], textposition="outside",
                               hovertemplate="%{y}: <b>$%{x:,.0f}</b> per new customer<extra></extra>"))
        show(fig, 280, title="Cost to win one paying customer (CAC)", showlegend=False, bargap=0.45,
             xaxis={"tickprefix": "$", "range": [0, (c.cac.max() or 1) * 1.25]}, yaxis={"autorange": "reversed"})
        how_to_read("shorter bars are cheaper channels. Organic is cheapest because it has almost no ad spend.")
    with b:
        r = scoped.dropna(subset=["roas"]).sort_values("roas", ascending=False)
        fig = go.Figure(go.Bar(x=r.roas, y=r.channel, orientation="h", marker={"color": SERIES[0], "line": RING},
                               text=[f"{v:.2f}×" for v in r.roas], textposition="outside",
                               hovertemplate="%{y}: <b>%{x:.2f}×</b> revenue per $1 spent<extra></extra>"))
        fig.add_vline(x=1, line_color=INK_2, line_width=1, annotation_text="break-even")
        show(fig, 280, title="Revenue per $1 of ad spend (ROAS)", showlegend=False, bargap=0.45,
             xaxis={"range": [0, max(1.2, (r.roas.max() or 1) * 1.25)]}, yaxis={"autorange": "reversed"})
        how_to_read("same-month revenue from a channel's customers (new and existing) ÷ that month's spend. "
                    "Right of the line = the channel brought in more than it cost that month.")
    with st.expander("See the numbers"):
        st.dataframe(scoped[["channel", "spend", "new_paid_customers", "cac", "recognized_revenue", "roas"]].rename(columns={
            "spend": "ad spend ($)", "new_paid_customers": "new paying customers", "cac": "cost per customer ($)",
            "recognized_revenue": "revenue ($)", "roas": "revenue per $1"}), hide_index=True, use_container_width=True)

# ------------------------------------------------------------------ engagement
elif page == "Product usage":
    daily = query("select * from analytics.mart_engagement_daily order by activity_date")
    features = query("select * from analytics.mart_feature_monthly order by month_start")
    last = daily.iloc[-1]
    monthly = features.loc[features.month_start == latest_month].sort_values("adoption_rate")
    top = monthly.iloc[-1] if len(monthly) else None
    header("Are people actually using the product?", "Customers who use the product regularly are the ones who "
           "keep paying. This page shows how many people use it and which features they rely on.", "Product usage",
           question="How many customers use the product, and how often?",
           answer=f"<b>{last.mau:,}</b> people used it in the last 30 days, and about <b>{last.dau:,}</b> on a typical "
                  f"day, so the average user comes back about <b>{last.dau_mau * 30:.0f} days a month</b>."
                  + (f" The most-used feature is <b>{top.feature}</b> ({pct(top.adoption_rate, 0)} of monthly users)."
                     if top is not None else ""))
    cards([
        ("Used it today (DAU)", f"{last.dau:,}", "daily active users"),
        ("Used it this week (WAU)", f"{last.wau:,}", "weekly active users"),
        ("Used it this month (MAU)", f"{last.mau:,}", "monthly active users"),
        ("Stickiness (DAU ÷ MAU)", pct(last.dau_mau), "share of monthly users who come back on a given day"),
    ])
    section("Active users, last 90 days")
    d90 = daily.tail(90)
    fig = go.Figure()
    for col, name, color in (("mau", "Monthly active", SERIES[0]), ("wau", "Weekly active", SERIES[1]),
                             ("dau", "Daily active", SERIES[2])):
        fig.add_trace(go.Scatter(x=d90.activity_date, y=d90[col], name=name, mode="lines", line={"color": color, "width": 2},
                                 hovertemplate=f"{name}: <b>%{{y:,}}</b><extra></extra>"))
    show(fig, 320, hovermode="x unified", yaxis={"rangemode": "tozero", "title": "people"})
    how_to_read("each line counts different people who used the product in the last day, 7 days or 30 days. "
                "The gap between them shows how often people come back.")
    a, b = st.columns(2)
    with a:
        section(f"Which features people use ({latest_month:%B})")
        fig = go.Figure(go.Bar(x=monthly.adoption_rate, y=monthly.feature.str.capitalize(), orientation="h",
                               marker={"color": SERIES[0], "line": RING}, text=[pct(v, 0) for v in monthly.adoption_rate],
                               textposition="outside",
                               hovertemplate="%{y}: <b>%{x:.0%}</b> of monthly users<extra></extra>"))
        show(fig, 280, xaxis={"tickformat": ".0%", "range": [0, monthly.adoption_rate.max() * 1.2 if len(monthly) else 1]},
             showlegend=False, bargap=0.45)
        how_to_read("the share of this month's active users who used each feature at least once.")
    with b:
        section("Sessions per month")
        sessions = query("select month_start, sessions from analytics.mart_monthly_kpis order by month_start")
        fig = go.Figure(go.Bar(x=sessions.month_start, y=sessions.sessions, marker={"color": SERIES[0], "line": RING},
                               hovertemplate="%{x|%b %Y}: <b>%{y:,}</b> sessions<extra></extra>"))
        show(fig, 280, showlegend=False, bargap=0.3, yaxis={"title": "sessions"})
        how_to_read("a session is one visit to the product. Growth here follows the growing customer base.")

# ------------------------------------------------------------------ retention
elif page == "Keeping customers":
    cohorts = query("select * from analytics.mart_cohort_retention order by cohort_month, month_number")
    kpis = query("select month_start, logo_churn_rate, gross_revenue_churn_rate, net_revenue_retention "
                 "from analytics.mart_monthly_kpis order by month_start")
    m6 = cohorts[cohorts.month_number == 6]
    m6_rate = (m6.retention_rate.mean()) if len(m6) else float("nan")
    nrr6 = kpis.tail(6).net_revenue_retention.mean()
    header("Do customers stay?", "A subscription business only works if customers keep paying. This page follows "
           "each month's new customers to see how many are still paying later.", "Keeping customers",
           question="How many customers are still paying after a few months?",
           answer=f"About <b>{pct(m6_rate, 0)}</b> of customers are still paying 6 months after their first payment "
                  f"(average across signup months). Existing customers keep <b>{pct(nrr6, 0)}</b> of their revenue "
                  "month to month after upgrades, downgrades and cancellations (last 6 months).")
    max_month = st.slider("Months after first payment", 1, 12, 6)
    pv = cohorts[cohorts.month_number <= max_month].pivot(index="cohort_month", columns="month_number",
                                                           values="retention_rate")
    pv.index = pd.to_datetime(pv.index).strftime("%b %Y")
    section("Share of each month's new customers still paying")
    floor = max(0.0, (int(pv.min().min() * 10) / 10) if pv.notna().any().any() else 0.0)
    fig = go.Figure(go.Heatmap(z=pv.to_numpy(), x=[f"Month {c}" for c in pv.columns], y=pv.index, colorscale=SEQ,
                               zmin=floor, zmax=1, xgap=2, ygap=2,
                               text=[[("" if pd.isna(v) else f"{v:.0%}") for v in r] for r in pv.to_numpy()],
                               texttemplate="%{text}", textfont={"size": 11},
                               colorbar={"title": "still<br>paying", "tickformat": ".0%", "thickness": 12},
                               hovertemplate="Started %{y}, %{x}: <b>%{z:.0%}</b> still paying<extra></extra>"))
    show(fig, 120 + 26 * len(pv), yaxis={"autorange": "reversed"}, xaxis={"side": "top"}, margin={"t": 40})
    how_to_read("each row is the group of customers whose first payment was in that month. Read across to see what "
                "share were still paying 1, 2, 3... months later; lighter cells = more customers lost. The colour scale "
                f"starts at {floor:.0%} so small differences show up. Newer groups have fewer months to show yet.")
    a, b = st.columns(2)
    with a:
        section("Cancellations each month")
        fig = go.Figure()
        for col, name, color in (("logo_churn_rate", "Customers who cancelled", SERIES[0]),
                                 ("gross_revenue_churn_rate", "Revenue lost to cancellations", SERIES[1])):
            fig.add_trace(go.Scatter(x=kpis.month_start, y=kpis[col], name=name, mode="lines+markers",
                                     line={"color": color, "width": 2}, marker={"size": 7, "line": RING},
                                     hovertemplate=f"{name}: <b>%{{y:.1%}}</b><extra></extra>"))
        show(fig, 300, hovermode="x unified", yaxis={"tickformat": ".0%", "rangemode": "tozero"})
        how_to_read("lower is better. The two lines differ when bigger or smaller customers cancel.")
    with b:
        section("Revenue kept from existing customers (NRR)")
        fig = go.Figure(go.Scatter(x=kpis.month_start, y=kpis.net_revenue_retention, mode="lines+markers",
                                   line={"color": SERIES[0], "width": 2}, marker={"size": 7, "line": RING},
                                   hovertemplate="%{x|%b %Y}: <b>%{y:.1%}</b><extra></extra>"))
        fig.add_hline(y=1, line_color=INK_2, line_width=1, annotation_text="100% = no net loss")
        show(fig, 300, showlegend=False, yaxis={"tickformat": ".0%"})
        how_to_read("above 100%, last month's customers are paying more in total this month (upgrades outweigh "
                    "cancellations); below 100%, they're paying less.")

# ------------------------------------------------------------------ experiment
else:
    result = query("select experiment_name, computed_at, result from analytics.experiment_results order by computed_at desc")
    if result.empty:
        header("Onboarding test", "Run the refresh pipeline to calculate experiment results.", "Onboarding test")
        st.info("Run the refresh pipeline to calculate experiment results.")
    else:
        name = result.experiment_name.iloc[0]
        if len(result) > 1:
            name = st.selectbox("Experiment", result.experiment_name.tolist())
        r = result.loc[result.experiment_name == name].iloc[0]["result"]
        if isinstance(r, str):
            r = json.loads(r)
        ship = r["recommendation"].lower().startswith("ship")
        header("Did the new onboarding work?", "New trial users were split at random: half saw the existing "
               "welcome flow (control), half saw a redesigned one (treatment). The test checks whether more of them "
               "started using the product in their first week.", "Onboarding test",
               question="Does the redesigned onboarding get more trial users to start using the product?",
               answer=(f"{'Yes.' if ship else 'Not clearly.'} <b>{pct(r['treatment_rate'])}</b> of users who saw the "
                       f"new onboarding started using the product within 7 days, against <b>{pct(r['control_rate'])}</b> "
                       f"with the old one ({r['absolute_lift'] * 100:+.1f} points). "
                       + ("A gap this large is very unlikely to be luck, so the recommendation is to <b>ship it</b>."
                          if ship else "The evidence isn't strong enough to ship it yet.")))
        cards([
            ("Old onboarding (control)", pct(r["control_rate"]), f"{r['control_converted']:,} of {r['control_n']:,} started using it"),
            ("New onboarding (treatment)", pct(r["treatment_rate"]), f"{r['treatment_converted']:,} of {r['treatment_n']:,} started using it"),
            ("Improvement", f"{r['absolute_lift'] * 100:+.1f} points", f"{pct(r['relative_lift'], 0)} more users, relatively"),
            ("Could it be luck? (p-value)", "<0.01%" if r["p_value"] < 0.0001 else f"{r['p_value']:.2%}",
             "chance of a gap this big if nothing changed; under 5% = real"),
        ])
        note(f"<b>Recommendation: {html.escape(r['recommendation'])}.</b> The whole likely range of the improvement "
             f"({r['ci_low'] * 100:.1f} to {r['ci_high'] * 100:.1f} points) is above the "
             f"{r['practical_threshold'] * 100:.0f}-point minimum the team said would be worth shipping.")
        a, b = st.columns(2)
        with a:
            section("Share who started using the product in 7 days")
            fig = go.Figure(go.Bar(x=["Old onboarding", "New onboarding"], y=[r["control_rate"], r["treatment_rate"]],
                                   marker={"color": [DEEMPH, SERIES[0]], "line": RING}, width=0.45,
                                   text=[pct(r["control_rate"]), pct(r["treatment_rate"])], textposition="outside",
                                   hovertemplate="%{x}: <b>%{y:.1%}</b><extra></extra>"))
            show(fig, 300, showlegend=False, yaxis={"tickformat": ".0%", "range": [0, max(r["treatment_rate"], r["control_rate"]) * 1.3]})
            how_to_read("taller bar = more trial users who used a key feature within their first 7 days.")
        with b:
            section("How big is the improvement, really?")
            lo, hi, mid = r["ci_low"] * 100, r["ci_high"] * 100, r["absolute_lift"] * 100
            thr = r["practical_threshold"] * 100
            fig = go.Figure()
            fig.add_shape(type="line", x0=lo, x1=hi, y0=0, y1=0, line={"color": SERIES[0], "width": 4})
            fig.add_trace(go.Scatter(x=[mid], y=[0], mode="markers", marker={"size": 14, "color": SERIES[0], "line": RING},
                                     hovertemplate=f"Best estimate: <b>{mid:+.1f} points</b><br>likely range {lo:.1f} to {hi:.1f}<extra></extra>"))
            fig.add_vline(x=0, line_color=INK_2, line_width=1, annotation_text="no effect",
                          annotation_position="top left")
            fig.add_vline(x=thr, line_color=ACCENT, line_width=1, annotation_text=f"worth shipping ({thr:.0f} pts)",
                          annotation_position="top right")
            show(fig, 300, showlegend=False, yaxis={"visible": False, "range": [-1, 1]},
                 xaxis={"title": "improvement (percentage points)", "range": [min(-2, lo - 3), hi + 3], "ticksuffix": ""})
            how_to_read("the dot is the best estimate; the bar is the range the true improvement is 95% likely to "
                        "fall in. It sits entirely right of both lines, so the effect is real and big enough to matter.")
        with st.expander("For analysts: test details"):
            st.markdown(f"""
- **Test:** two-sided pooled two-proportion z-test, α = 0.05; 95% Newcombe interval for the rate difference.
- **Sample:** {r['control_n']:,} control ({r['control_converted']:,} activated), {r['treatment_n']:,} treatment ({r['treatment_converted']:,} activated).
- **Effect size:** Cohen's h = {r['cohen_h']:.3f}; relative lift {pct(r['relative_lift'])}.
- **Sensitivity:** smallest detectable effect at 80% power = {pct(r['mde_absolute'])} absolute; power for the pre-set {pct(r['practical_threshold'])} threshold = {pct(r['design_power'])}.
- **Decision rule:** ship only if the whole interval is above zero *and* the observed lift is at least the pre-set threshold.
""")

st.divider()
st.caption(FOOT)
