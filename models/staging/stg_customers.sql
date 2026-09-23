select customer_id, signup_at, trial_started_at, account_name, segment,
       country, channel, experiment_variant
from {{ source('raw', 'customers') }}
