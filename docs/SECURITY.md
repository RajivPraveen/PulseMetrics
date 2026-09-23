# Security and access

The included Docker setup is for a local machine. The database and dashboard bind to `127.0.0.1` so they are not exposed to other machines by default.

## Dashboard roles

- **Admin:** all five pages, including revenue and acquisition economics.
- **Analyst:** engagement, retention, and experimentation pages.

Credentials are read from `.env`; no password is committed. The app checks the role before rendering each page. This is a local access layer, not an organization identity system.

## Before shared deployment

Put the dashboard behind SSO and HTTPS, use a read-only PostgreSQL account for dashboard queries, store secrets in a secret manager, restrict database access to private networks, and add centralized audit logs. The local `pulse` database account is used by ingestion, dbt, and dashboard for convenience; it should be split into least-privilege roles before deployment.

The sample exports are synthetic. Do not replace them with real customer data in a public repository. `.env`, generated source files, logs, and dbt output are ignored by Git; verify `git status` before every push.
