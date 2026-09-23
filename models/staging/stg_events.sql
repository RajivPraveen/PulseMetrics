select event_id, customer_id, occurred_at, event_name, session_id, feature
from {{ source('raw', 'product_events') }}
