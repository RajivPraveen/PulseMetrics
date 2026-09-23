with months as (
    select generate_series(
        date_trunc('month', (select min(signup_at) from {{ ref('dim_customer') }}))::date,
        (select max(month_start) from {{ source('raw', 'marketing_spend') }}),
        interval '1 month')::date as month_start
), spine as (
    select c.customer_id, m.month_start
    from {{ ref('dim_customer') }} c
    join months m on m.month_start >= date_trunc('month', c.signup_at)::date
), event_month as (
    select customer_id, date_trunc('month', occurred_at)::date as month_start,
           count(distinct occurred_at::date) filter (where event_name = 'session_started') as active_days,
           count(*) filter (where event_name = 'session_started') as sessions,
           count(distinct feature) filter (where event_name = 'feature_used') as features_used
    from {{ ref('stg_events') }}
    group by 1, 2
), base as (
    select s.customer_id, s.month_start,
           coalesce(p.mrr, 0)::numeric(12,2) as mrr,
           coalesce(e.active_days, 0) as active_days,
           coalesce(e.sessions, 0) as sessions,
           coalesce(e.features_used, 0) as features_used
    from spine s
    left join {{ source('raw', 'subscription_periods') }} p
      on p.customer_id = s.customer_id
     and p.started_at < s.month_start + interval '1 month'
     and (p.ended_at is null or p.ended_at >= s.month_start + interval '1 month')
    left join event_month e
      on e.customer_id = s.customer_id and e.month_start = s.month_start
), lagged as (
    select *, lag(mrr, 1, 0) over (partition by customer_id order by month_start) as prior_mrr
    from base
)
select *,
       case when prior_mrr = 0 and mrr > 0 then mrr else 0 end as new_mrr,
       case when prior_mrr > 0 and mrr > prior_mrr then mrr - prior_mrr else 0 end as expansion_mrr,
       case when prior_mrr > 0 and mrr < prior_mrr and mrr > 0 then prior_mrr - mrr else 0 end as contraction_mrr,
       case when prior_mrr > 0 and mrr = 0 then prior_mrr else 0 end as churned_mrr
from lagged
