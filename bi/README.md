# BI connectivity

The Streamlit app is the runnable five-page dashboard. The dbt marts also serve as clean Power BI and Tableau sources through PostgreSQL. Connect with a **read-only** database account in any shared deployment.

- Executive: `mart_monthly_kpis`, `dim_customer`, `fct_customer_month`
- Acquisition: `mart_funnel_monthly`, `mart_acquisition_channel_month`
- Engagement: `mart_engagement_daily`, `mart_feature_monthly`
- Retention: `mart_cohort_retention`
- Experimentation: `experiment_results` (expand the JSON fields in Power Query)

Starter DAX measures are in `powerbi/Measures.dax`. In Power Query, set month and date keys to Date and money columns to Fixed Decimal. Relationships should flow from a separate calendar dimension to each monthly or daily fact; avoid joining marts directly because their grains differ. In Tableau, use separate data sources for each page or relationships on calendar keys and retain cohort month plus month number as a composite key.
