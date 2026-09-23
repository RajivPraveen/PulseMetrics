"""PulseMetrics interactive analytics dashboard."""
from __future__ import annotations

import hmac
import json
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()
st.set_page_config(page_title="PulseMetrics", page_icon="📊", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.5rem; max-width: 1440px;}
h1, h2, h3 {letter-spacing: -0.035em;}
[data-testid="stMetric"] {background: #f4f7fc; padding: 1rem; border-radius: 12px;}
</style>
""", unsafe_allow_html=True)


def authenticate() -> str | None:
    if "role" in st.session_state:
        return st.session_state.role
    st.title("PulseMetrics")
    st.caption("Sign in to view the analytics workspace")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)
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


def pct(value, digits=1):
    return "—" if pd.isna(value) else f"{value * 100:.{digits}f}%"


def money(value, compact=False):
    if pd.isna(value):
        return "—"
    value = float(value)
    return f"${value / 1000:,.1f}k" if compact and value >= 1000 else f"${value:,.0f}"


pages = ["Executive Overview", "Acquisition", "Engagement", "Retention", "Experimentation"]
if role != "admin":
    pages = ["Engagement", "Retention", "Experimentation"]
st.sidebar.title("◉ PulseMetrics")
page = st.sidebar.radio("Workspace", pages)
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

st.caption(f"Reporting through {latest_month:%B %Y} · synthetic SaaS data · monthly revenue at period end")

if page == "Executive Overview":
    st.title("Executive Overview")
    kpis = query("select * from analytics.mart_monthly_kpis order by month_start")
    current = kpis.iloc[-1]
    for col, label, value in zip(st.columns(6),
        ["MRR", "ARR", "Paid customers", "Logo churn", "Est. LTV", "CAC"],
        [money(current.mrr, True), money(current.arr, True), f"{current.paid_customers:,}",
         pct(current.logo_churn_rate), money(current.estimated_ltv), money(current.cac)]):
        col.metric(label, value)
    left, right = st.columns([1.7, 1])
    with left:
        fig = px.line(kpis, x="month_start", y="mrr", markers=True,
                      title="MRR trend", labels={"mrr": "USD", "month_start": "Month"})
        st.plotly_chart(fig, use_container_width=True)
    with right:
        movement = pd.DataFrame({"Movement": ["New", "Expansion", "Contraction", "Churn"],
                                 "MRR": [current.new_mrr, current.expansion_mrr,
                                         -current.contraction_mrr, -current.churned_mrr]})
        st.plotly_chart(px.bar(movement, x="Movement", y="MRR", color="MRR",
                               color_continuous_scale="RdYlGn", title="Latest MRR movement"),
                        use_container_width=True)
    st.subheader("Customer mix")
    mix = query("""
        select c.segment, c.channel, count(*) as customers, sum(f.mrr) as mrr
        from analytics.fct_customer_month f join analytics.dim_customer c using (customer_id)
        where f.month_start = :month and f.mrr > 0
        group by 1, 2 order by mrr desc
    """, {"month": latest_month})
    a, b = st.columns(2)
    a.plotly_chart(px.bar(mix.groupby("segment", as_index=False)["mrr"].sum(),
                          x="segment", y="mrr", title="MRR by segment"), use_container_width=True)
    b.plotly_chart(px.bar(mix.groupby("channel", as_index=False)["customers"].sum(),
                          x="channel", y="customers", title="Paid customers by acquisition channel"),
                   use_container_width=True)

elif page == "Acquisition":
    st.title("Acquisition")
    funnel = query("select * from analytics.mart_funnel_monthly order by month_start")
    channels = query("select * from analytics.mart_acquisition_channel_month order by month_start")
    month = st.selectbox("Signup cohort", funnel.month_start.tolist()[::-1],
                         format_func=lambda x: x.strftime("%B %Y"))
    row = funnel.loc[funnel.month_start == month].iloc[0]
    labels = ["Website", "Signup", "Trial", "Activated", "Paid in 30d"]
    counts = [row.website_visitors, row.signups, row.trials, row.activated, row.paid_30d]
    st.plotly_chart(go.Figure(go.Funnel(y=labels, x=counts)).update_layout(
        title="Acquisition funnel by signup month"), use_container_width=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Visit → signup", pct(row.visit_to_signup))
    c2.metric("Trial → activation", pct(row.trial_to_activation))
    c3.metric("Trial → paid", pct(row.trial_to_paid))
    c4.metric("90-day retained", f"{row.retained_90d:,}")
    st.subheader("Channel economics")
    scoped = channels.loc[channels.month_start == month].copy()
    st.dataframe(scoped[["channel", "spend", "new_paid_customers", "cac", "recognized_revenue", "roas"]],
                 hide_index=True, use_container_width=True)
    st.caption("ROAS = same-month attributed invoice revenue ÷ same-month channel spend; CAC = spend ÷ new paid customers.")

elif page == "Engagement":
    st.title("Engagement")
    daily = query("select * from analytics.mart_engagement_daily order by activity_date")
    features = query("select * from analytics.mart_feature_monthly order by month_start")
    latest_day = daily.iloc[-1]
    a, b, c, d = st.columns(4)
    a.metric("DAU", f"{latest_day.dau:,}")
    b.metric("WAU", f"{latest_day.wau:,}")
    c.metric("MAU", f"{latest_day.mau:,}")
    d.metric("DAU / MAU", pct(latest_day.dau_mau))
    st.plotly_chart(px.line(daily.tail(90), x="activity_date", y=["dau", "wau", "mau"],
                            title="Active users · trailing 90 days"), use_container_width=True)
    monthly = features.loc[features.month_start == latest_month]
    st.plotly_chart(px.bar(monthly, x="feature", y="adoption_rate", color="feature",
                           title="Feature adoption among monthly active users"), use_container_width=True)
    sessions = query("select month_start, sessions from analytics.mart_monthly_kpis order by month_start")
    st.plotly_chart(px.bar(sessions, x="month_start", y="sessions", title="Monthly sessions"),
                    use_container_width=True)

elif page == "Retention":
    st.title("Retention")
    cohorts = query("select * from analytics.mart_cohort_retention order by cohort_month, month_number")
    max_month = st.slider("Months after first payment", 1, 12, 6)
    cohort_pivot = cohorts[cohorts.month_number <= max_month].pivot(
        index="cohort_month", columns="month_number", values="retention_rate")
    cohort_pivot.index = pd.to_datetime(cohort_pivot.index).strftime("%b %Y")
    st.plotly_chart(px.imshow(cohort_pivot, color_continuous_scale="Blues", zmin=0, zmax=1,
                              text_auto=".0%", aspect="auto", title="Paid customer cohort retention",
                              labels={"x": "Month after first payment", "y": "Cohort", "color": "Retained"}),
                    use_container_width=True)
    st.caption("A customer is retained when their subscription is active at the end of the month. Newer cohorts have fewer observed months.")
    kpis = query("select month_start, logo_churn_rate, gross_revenue_churn_rate, net_revenue_retention from analytics.mart_monthly_kpis order by month_start")
    st.plotly_chart(px.line(kpis, x="month_start", y=["logo_churn_rate", "gross_revenue_churn_rate", "net_revenue_retention"],
                            title="Churn and net revenue retention"), use_container_width=True)

else:
    st.title("Experimentation")
    result = query("select experiment_name, computed_at, result from analytics.experiment_results order by computed_at desc")
    if result.empty:
        st.info("Run the refresh pipeline to calculate experiment results.")
    else:
        name = st.selectbox("Experiment", result.experiment_name.tolist())
        r = result.loc[result.experiment_name == name].iloc[0]["result"]
        if isinstance(r, str):
            r = json.loads(r)
        a, b, c, d = st.columns(4)
        a.metric("Control activation", pct(r["control_rate"]))
        b.metric("Treatment activation", pct(r["treatment_rate"]))
        c.metric("Relative lift", pct(r["relative_lift"]))
        d.metric("p-value", "<0.0001" if r["p_value"] < 0.0001 else f"{r['p_value']:.4f}")
        st.success(r["recommendation"])
        st.plotly_chart(go.Figure(go.Bar(
            x=["Control", "Treatment"], y=[r["control_rate"], r["treatment_rate"]],
            marker_color=["#64748b", "#2563eb"],
            text=[pct(r["control_rate"]), pct(r["treatment_rate"])], textposition="outside",
        )).update_layout(title="Activation within seven days", yaxis_tickformat=".0%"),
            use_container_width=True)
        st.write(f"**Absolute lift:** {pct(r['absolute_lift'])} · "
                 f"**95% CI:** {pct(r['ci_low'])} to {pct(r['ci_high'])} · "
                 f"**Cohen's h:** {r['cohen_h']:.3f}")
        st.write(f"**Sample:** {r['control_n']:,} control ({r['control_converted']:,} activated), "
                 f"{r['treatment_n']:,} treatment ({r['treatment_converted']:,} activated)")
        st.write(f"**MDE at 80% power:** {pct(r['mde_absolute'])} absolute · "
                 f"**Power for a {pct(r['practical_threshold'])} effect:** {pct(r['design_power'])}")
        st.caption("Two-sided pooled z-test; Newcombe confidence interval for the absolute rate difference. Power uses the control rate and planned practical threshold, not the observed lift.")
