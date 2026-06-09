# Maintenance Template

This document is the handoff guide for the integration package. It helps the team
understand where each responsibility lives before wiring it into the dashboard.

## Project Summary

- Product: Meta Messenger and Instagram OAuth integration
- Backend: Flask
- Purpose: connect Meta accounts, receive webhooks, store recent events, and support manual dashboard actions
- Scope: integration only

## File Map

| File | Responsibility |
| --- | --- |
| `app.py` | Main Flask app, helpers, routes, webhook handlers, persistence helpers |
| `templates/*.html` | UI for landing pages, dashboards, success screens, and comment management |
| `requirements.txt` | Python dependencies |
| `Procfile` | Deployment entrypoint |
| `gunicorn.conf.py` | Gunicorn runtime configuration |
| `.ebextensions/` | AWS Elastic Beanstalk deployment config |
| `.env.example` | Example environment variables |

## `app.py` Structure

The file is grouped in the following order:

1. Environment and application setup
2. Persistent storage paths and shared constants
3. In-memory runtime state
4. Storage helpers
5. Message persistence helpers
6. Meta Graph API helpers
7. OAuth and dashboard routes
8. Instagram routes
9. API endpoints for dashboards and debug tools
10. Messenger and Instagram webhook handlers
11. Compliance endpoints

## Integration Notes

- Keep the existing route names stable when wiring the dashboard.
- Treat generated JSON files as local integration storage.
- Webhook endpoints only verify, log, and persist events.
- Manual send endpoints send exactly the operator-provided message text.
- No automatic reply workflow is part of this package.

## What The Team Should Review First

- OAuth callback flow for Messenger
- OAuth callback flow for Instagram
- Webhook verification and event parsing
- Message persistence format
- Instagram comments API endpoints
- Manual Messenger and Instagram send endpoints

## Deployment Checklist

- Confirm all required Meta app permissions are approved
- Confirm `META_APP_ID`, `META_APP_SECRET`, and callback URLs are set correctly
- Confirm the webhook verification token matches the Meta configuration
- Confirm storage files are writable in the target environment
- Confirm the dashboard reads the expected route outputs and JSON payloads

## Notes For Future Splitting

If the codebase is later split into modules, the most natural boundaries are:

- `config.py` for environment values and constants
- `storage.py` for JSON persistence helpers
- `graph_api.py` for Meta HTTP helpers
- `routes/` for Flask route groups
