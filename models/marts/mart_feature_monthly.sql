with usage as (
    select date_trunc('month', occurred_at)::date as month_start, feature,
           count(distinct customer_id) as feature_users,
           count(*) as feature_events
    from {{ ref('stg_events') }}
    where event_name = 'feature_used' and feature is not null
    group by 1, 2
), active as (
    select month_start, count(distinct customer_id) as monthly_active_users
    from {{ ref('fct_customer_month') }} where active_days > 0 group by 1
)
select u.*, a.monthly_active_users,
       round(u.feature_users::numeric / nullif(a.monthly_active_users, 0), 4) as adoption_rate
from usage u join active a using (month_start)
