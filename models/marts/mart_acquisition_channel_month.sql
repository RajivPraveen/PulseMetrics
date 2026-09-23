with spend as (
    select month_start, channel, sum(spend) as spend, sum(clicks) as clicks,
           sum(impressions) as impressions
    from {{ source('raw', 'marketing_spend') }} group by 1, 2
), acquired as (
    select date_trunc('month', first_paid_at)::date as month_start, channel,
           count(*) as new_paid_customers
    from {{ ref('dim_customer') }} where first_paid_at is not null group by 1, 2
), revenue as (
    select date_trunc('month', i.invoiced_at)::date as month_start, c.channel,
           sum(i.amount) as recognized_revenue
    from {{ source('raw', 'invoices') }} i
    join {{ ref('dim_customer') }} c using (customer_id)
    group by 1, 2
)
select s.*, coalesce(a.new_paid_customers, 0) as new_paid_customers,
       coalesce(r.recognized_revenue, 0) as recognized_revenue,
       round(s.spend / nullif(a.new_paid_customers, 0), 2) as cac,
       round(r.recognized_revenue / nullif(s.spend, 0), 3) as roas
from spend s
left join acquired a using (month_start, channel)
left join revenue r using (month_start, channel)
