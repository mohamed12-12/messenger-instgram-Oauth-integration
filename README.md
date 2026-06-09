# Messenger and Instagram OAuth Integration

Flask-based Meta integration for connecting Facebook Messenger and Instagram Business accounts. It handles OAuth, page/account token storage, webhook verification, inbound event capture, manual outbound messaging, and Instagram comment management.

This package is intentionally integration-only.

## What it does

- Connects a Facebook Page through Meta OAuth
- Connects an Instagram professional account through the Meta page flow
- Subscribes connected pages to Meta webhooks
- Records inbound Messenger and Instagram webhook events
- Lets operators manually send Messenger and Instagram messages
- Lets operators fetch, reply to, hide, and delete Instagram comments
- Provides debug endpoints for token, subscription, and webhook checks

## Main Features

### Messenger integration

- Page selection after OAuth login
- Webhook verification and event processing
- Manual message sending from the dashboard
- Message and subscription debug endpoints

### Instagram integration

- Instagram account connection through Meta OAuth
- Inbox-style dashboard for Instagram conversation events
- Comment fetching, replying, hiding, and deleting
- Manual Instagram message sending
- Separate storage per connected Instagram account

### Operational tooling

- JSON file-based storage for tokens and recent events
- Webhook debug logging
- Deployment-ready Gunicorn and AWS Elastic Beanstalk configuration

## Tech Stack

- Python 3
- Flask
- Requests
- python-dotenv
- Gunicorn

## Project Structure

- `app.py` - main Flask application, OAuth flow, webhooks, dashboards, APIs
- `templates/` - HTML templates for dashboards and auth screens
- `requirements.txt` - Python dependencies
- `Procfile` - process definition for deployment platforms
- `gunicorn.conf.py` - Gunicorn runtime settings
- `.ebextensions/` - AWS Elastic Beanstalk configuration
- `.env.example` - example environment variables

## Local Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Copy `.env.example` to `.env` and fill in the real values before running the app.

## Required Environment Variables

- `META_APP_ID`
- `META_APP_SECRET`
- `REDIRECT_URI`
- `INSTAGRAM_REDIRECT_URI`
- `FLASK_SECRET_KEY`
- `VERIFY_TOKEN`

## Required Meta Setup

- Meta developer app
- Facebook Login enabled
- Messenger permissions for the connected Page
- Instagram Graph API permissions for professional accounts
- Public HTTPS callback URL for OAuth and webhooks
- Webhook URL pointing to the deployed app

The app uses Meta Graph API v22.0.

## Useful Endpoints

- `/` - Messenger connect page
- `/connect` - Messenger OAuth start
- `/auth/callback` - Messenger OAuth callback
- `/dashboard` - Messenger dashboard
- `/instagram/connect` - Instagram OAuth start
- `/instagram/auth/callback` - Instagram OAuth callback
- `/instagram/dashboard` - Instagram dashboard
- `/instagram/comments/<ig_account_id>` - Instagram comments dashboard
- `/webhook` - Messenger webhook verification and events
- `/messenger` - alternate Messenger webhook endpoint
- `/instagram/webhook` - Instagram webhook verification and events
- `/api/...` - debugging and operational APIs

## Security Notes

- Never commit `.env`, access tokens, or generated JSON storage files
- Use a strong `FLASK_SECRET_KEY`
- Keep `VERIFY_TOKEN` unique per environment
- Use HTTPS for OAuth redirects and webhook endpoints
