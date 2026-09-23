with cohorts as (
    select customer_id, date_trunc('month', first_paid_at)::date as cohort_month
    from {{ ref('dim_customer') }} where first_paid_at is not null
), sizes as (
    select cohort_month, count(*) as cohort_size from cohorts group by 1
), retention as (
    select c.cohort_month, f.month_start,
           ((extract(year from f.month_start) - extract(year from c.cohort_month)) * 12
             + extract(month from f.month_start) - extract(month from c.cohort_month))::int as month_number,
           count(*) filter (where f.mrr > 0) as retained_customers
    from cohorts c join {{ ref('fct_customer_month') }} f using (customer_id)
    where f.month_start >= c.cohort_month
    group by 1, 2, 3
)
select r.*, s.cohort_size,
       round(r.retained_customers::numeric / nullif(s.cohort_size, 0), 4) as retention_rate
from retention r join sizes s using (cohort_month)
