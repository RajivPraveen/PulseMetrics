select month_start
from {{ ref('mart_monthly_kpis') }}
where mrr < 0 or new_mrr < 0 or expansion_mrr < 0
   or contraction_mrr < 0 or churned_mrr < 0
   or paid_customers < 0 or marketing_spend < 0
