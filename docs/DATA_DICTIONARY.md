# Data dictionary

| Relation | Grain | Key | Description |
| --- | --- | --- | --- |
| `raw.customers` | Account | `customer_id` | Signup, trial, segment, country, original channel and experiment assignment |
| `raw.web_visits` | Visit | `visit_id` | Known and anonymous website visitors |
| `raw.subscription_periods` | Price period | `period_id` | Active interval, plan and monthly run rate; end is exclusive |
| `raw.invoices` | Invoice | `invoice_id` | Simulated billed amounts and new/recurring/expansion classification |
| `raw.product_events` | Event | `event_id` | Signup, trial, activation, session and feature usage events |
| `raw.marketing_spend` | Channel-month | `spend_id` | Spend, clicks and impressions |
| `raw.support_tickets` | Ticket | `ticket_id` | Customer support status and priority |
| `control.ingestion_state` | Source | `source_name` | Last successfully loaded source timestamp and row count |
| `analytics.dim_customer` | Account | `customer_id` | First activation/payment, conversion-window flags and support ticket counts |
| `analytics.fct_customer_month` | Account-month | (`customer_id`, `month_start`) | End-of-month MRR, prior MRR, movements, sessions and feature count |
| `analytics.mart_monthly_kpis` | Month | `month_start` | Executive revenue, acquisition, churn and engagement KPIs |
| `analytics.mart_funnel_monthly` | Signup month | `month_start` | Funnel stage counts and conversion ratios |
| `analytics.mart_acquisition_channel_month` | Channel-month | (`channel`, `month_start`) | CAC, attributed invoice revenue, ROAS |
| `analytics.mart_cohort_retention` | Paid cohort-month age | (`cohort_month`, `month_number`) | Retained customers and retention rate |
| `analytics.mart_engagement_daily` | Day | `activity_date` | Rolling DAU, WAU, MAU and stickiness |
| `analytics.mart_feature_monthly` | Feature-month | (`feature`, `month_start`) | Users, events and adoption rate |
| `analytics.experiment_results` | Experiment | `experiment_name` | Statistical result JSON and computation time |

All timestamps are UTC. `source_updated_at` is the source-side change time used for incremental upserts. New or corrected exports with a later timestamp are loaded; reruns with unchanged exports insert zero rows.
