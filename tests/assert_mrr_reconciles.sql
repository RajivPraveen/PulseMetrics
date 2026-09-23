select k.month_start, k.mrr as mart_mrr, sum(f.mrr) as fact_mrr
from {{ ref('mart_monthly_kpis') }} k
join {{ ref('fct_customer_month') }} f using (month_start)
group by 1, 2
having k.mrr <> sum(f.mrr)
