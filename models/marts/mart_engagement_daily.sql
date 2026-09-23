with activity as (
    select distinct customer_id, occurred_at::date as activity_date
    from {{ ref('stg_events') }} where event_name = 'session_started'
), dates as (
    select generate_series(min(activity_date), max(activity_date), interval '1 day')::date as activity_date
    from activity
)
select d.activity_date,
       count(distinct a.customer_id) filter (where a.activity_date = d.activity_date) as dau,
       count(distinct a.customer_id) filter (where a.activity_date >= d.activity_date - 6) as wau,
       count(distinct a.customer_id) as mau,
       round(count(distinct a.customer_id) filter (where a.activity_date = d.activity_date)::numeric
           / nullif(count(distinct a.customer_id), 0), 4) as dau_mau
from dates d
left join activity a on a.activity_date between d.activity_date - 29 and d.activity_date
group by 1
