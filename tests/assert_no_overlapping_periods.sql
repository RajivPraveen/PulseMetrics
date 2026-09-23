select a.period_id, b.period_id as conflicting_period_id
from {{ source('raw', 'subscription_periods') }} a
join {{ source('raw', 'subscription_periods') }} b
  on a.customer_id = b.customer_id and a.period_id < b.period_id
 and a.started_at < coalesce(b.ended_at, 'infinity'::timestamptz)
 and b.started_at < coalesce(a.ended_at, 'infinity'::timestamptz)
