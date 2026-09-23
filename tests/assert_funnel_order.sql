select month_start
from {{ ref('mart_funnel_monthly') }}
where signups > website_visitors or trials > signups
   or activated > trials or paid_30d > trials
