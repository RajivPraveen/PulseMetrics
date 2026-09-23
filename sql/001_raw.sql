CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS control;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS control.ingestion_state (
  source_name text PRIMARY KEY,
  watermark timestamptz NOT NULL,
  loaded_at timestamptz NOT NULL DEFAULT now(),
  row_count bigint NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS raw.customers (
  customer_id bigint PRIMARY KEY, signup_at timestamptz NOT NULL,
  trial_started_at timestamptz, account_name text NOT NULL,
  segment text NOT NULL, country text NOT NULL, channel text NOT NULL,
  experiment_variant text NOT NULL CHECK (experiment_variant IN ('control','treatment')),
  source_updated_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS raw.web_visits (
  visit_id bigint PRIMARY KEY, visitor_id text NOT NULL, customer_id bigint,
  visited_at timestamptz NOT NULL, channel text NOT NULL,
  source_updated_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS raw.subscription_periods (
  period_id bigint PRIMARY KEY, customer_id bigint NOT NULL,
  started_at timestamptz NOT NULL, ended_at timestamptz,
  plan text NOT NULL, mrr numeric(12,2) NOT NULL CHECK (mrr >= 0),
  source_updated_at timestamptz NOT NULL,
  CHECK (ended_at IS NULL OR ended_at > started_at)
);
CREATE TABLE IF NOT EXISTS raw.invoices (
  invoice_id bigint PRIMARY KEY, customer_id bigint NOT NULL,
  period_id bigint NOT NULL, invoiced_at timestamptz NOT NULL,
  amount numeric(12,2) NOT NULL, invoice_type text NOT NULL,
  source_updated_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS raw.product_events (
  event_id bigint PRIMARY KEY, customer_id bigint NOT NULL,
  occurred_at timestamptz NOT NULL, event_name text NOT NULL,
  session_id text NOT NULL, feature text,
  source_updated_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_events_customer_time ON raw.product_events (customer_id, occurred_at);
CREATE TABLE IF NOT EXISTS raw.marketing_spend (
  spend_id bigint PRIMARY KEY, month_start date NOT NULL, channel text NOT NULL,
  spend numeric(12,2) NOT NULL, impressions integer NOT NULL, clicks integer NOT NULL,
  source_updated_at timestamptz NOT NULL,
  UNIQUE (month_start, channel)
);
CREATE TABLE IF NOT EXISTS raw.support_tickets (
  ticket_id bigint PRIMARY KEY, customer_id bigint NOT NULL,
  opened_at timestamptz NOT NULL, status text NOT NULL, priority text NOT NULL,
  source_updated_at timestamptz NOT NULL
);
