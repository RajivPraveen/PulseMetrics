with revenue as (
    select month_start, sum(mrr) as mrr,
           count(*) filter (where mrr > 0) as paid_customers,
           count(*) filter (where new_mrr > 0) as new_paid_customers,
           count(*) filter (where churned_mrr > 0) as churned_customers,
           sum(new_mrr) as new_mrr, sum(expansion_mrr) as expansion_mrr,
           sum(contraction_mrr) as contraction_mrr, sum(churned_mrr) as churned_mrr,
           sum(prior_mrr) as starting_mrr,
           sum(sessions) as sessions
    from {{ ref('fct_customer_month') }} group by 1
), spend as (
    select month_start, sum(spend) as marketing_spend
    from {{ source('raw', 'marketing_spend') }} group by 1
), engagement as (
    select date_trunc('month', activity_date)::date as month_start,
           round(avg(dau), 1) as avg_dau, max(mau) as mau,
           round(avg(dau_mau), 4) as avg_dau_mau
    from {{ ref('mart_engagement_daily') }} group by 1
)
select r.*, r.mrr * 12 as arr, s.marketing_spend,
       f.signups, f.trials, f.activated, f.paid_30d,
       e.avg_dau, e.mau, e.avg_dau_mau,
       round(r.churned_customers::numeric / nullif(lag(r.paid_customers) over (order by r.month_start), 0), 4) as logo_churn_rate,
       round(r.churned_mrr / nullif(r.starting_mrr, 0), 4) as gross_revenue_churn_rate,
       round((r.starting_mrr + r.expansion_mrr - r.contraction_mrr - r.churned_mrr)
           / nullif(r.starting_mrr, 0), 4) as net_revenue_retention,
       round(s.marketing_spend / nullif(r.new_paid_customers, 0), 2) as cac,
       round(r.mrr / nullif(r.paid_customers, 0), 2) as arpa,
       round((r.mrr / nullif(r.paid_customers, 0)) /
             nullif(r.churned_customers::numeric / nullif(lag(r.paid_customers) over (order by r.month_start), 0), 0), 2) as estimated_ltv,
       round(f.activated::numeric / nullif(f.trials, 0), 4) as activation_rate,
       round(f.paid_30d::numeric / nullif(f.trials, 0), 4) as trial_to_paid_rate
from revenue r
left join spend s using (month_start)
left join {{ ref('mart_funnel_monthly') }} f using (month_start)
left join engagement e using (month_start)
