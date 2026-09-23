with activation as (
    select e.customer_id, min(e.occurred_at) as activated_at
    from {{ ref('stg_events') }} e
    where e.event_name = 'activated'
    group by 1
), paid as (
    select customer_id, min(started_at) as first_paid_at
    from {{ source('raw', 'subscription_periods') }}
    group by 1
), support as (
    select customer_id, count(*) as ticket_count,
           count(*) filter (where status = 'open') as open_tickets
    from {{ source('raw', 'support_tickets') }} group by 1
)
select c.*, a.activated_at, p.first_paid_at,
       coalesce(s.ticket_count, 0) as ticket_count,
       coalesce(s.open_tickets, 0) as open_tickets,
       (a.activated_at >= c.trial_started_at and
        a.activated_at < c.trial_started_at + interval '7 days') as activated_within_7d,
       (p.first_paid_at >= c.trial_started_at and
        p.first_paid_at < c.trial_started_at + interval '30 days') as paid_within_30d
from {{ ref('stg_customers') }} c
left join activation a using (customer_id)
left join paid p using (customer_id)
left join support s using (customer_id)
