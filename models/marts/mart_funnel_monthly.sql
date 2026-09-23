with visits as (
    select date_trunc('month', visited_at)::date as month_start,
           count(distinct visitor_id) as website_visitors
    from {{ source('raw', 'web_visits') }} group by 1
), cohorts as (
    select date_trunc('month', signup_at)::date as month_start,
           count(*) as signups,
           count(*) filter (where trial_started_at is not null) as trials,
           count(*) filter (where activated_within_7d) as activated,
           count(*) filter (where paid_within_30d) as paid_30d,
           count(*) filter (where first_paid_at is not null and
               first_paid_at + interval '90 days' < current_date and
               exists (select 1 from {{ source('raw', 'subscription_periods') }} p
                       where p.customer_id = c.customer_id
                         and (p.ended_at is null or p.ended_at > first_paid_at + interval '90 days')))
               as retained_90d
    from {{ ref('dim_customer') }} c group by 1
)
select v.month_start, v.website_visitors,
       coalesce(c.signups, 0) as signups, coalesce(c.trials, 0) as trials,
       coalesce(c.activated, 0) as activated, coalesce(c.paid_30d, 0) as paid_30d,
       coalesce(c.retained_90d, 0) as retained_90d,
       round(c.signups::numeric / nullif(v.website_visitors, 0), 4) as visit_to_signup,
       round(c.activated::numeric / nullif(c.trials, 0), 4) as trial_to_activation,
       round(c.paid_30d::numeric / nullif(c.trials, 0), 4) as trial_to_paid
from visits v left join cohorts c using (month_start)
