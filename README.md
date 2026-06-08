# Messenger and Instagram OAuth Integration

Flask-based customer messaging platform that connects a Meta app to both Facebook Messenger and Instagram. It supports OAuth-based page/account connection, webhook handling, automated replies, human-agent escalation, and Instagram comment management from a single dashboard.

## What it does

- Connects a Facebook Page through Meta OAuth
- Connects an Instagram professional account through the same Meta flow
- Subscribes pages to webhooks for inbound Messenger and Instagram events
- Sends automated replies using rule-based intent handling and optional Gemini-backed generation
- Escalates conversations to a human agent when needed
- Lets operators reply to, hide, and delete Instagram comments
- Tracks recent messages, webhook activity, and conversation state for debugging

## Main Features

### Messenger integration
- Page selection after OAuth login
- Webhook verification and event processing
- Automated replies with escalation logic
- Human agent handoff and thread control endpoints
- Debug endpoints for message and subscription inspection

### Instagram integration
- Instagram account connection through Meta OAuth
- Inbox-style dashboard for Instagram conversations
- Comment fetching, replying, hiding, and deleting
- Manual and automatic message replies
- Separate dashboards and storage per connected account

### Operational tooling
- JSON file-based storage for tokens, messages, and conversation state
- Webhook debug logging
- Email alerts for human-agent escalations
- Deployment-ready Gunicorn and AWS Elastic Beanstalk configuration

## Tech Stack

- Python 3
- Flask
- Requests
- python-dotenv
- Gunicorn

## Project Structure

- `app.py` - main Flask application, OAuth flow, webhooks, dashboards, APIs
- `templates/` - HTML templates for the dashboards and auth screens
- `requirements.txt` - Python dependencies
- `Procfile` - process definition for deployment platforms
- `gunicorn.conf.py` - Gunicorn runtime settings
- `.ebextensions/` - AWS Elastic Beanstalk configuration
- `.env.example` - example environment variables

## Local Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd messenger-instgram-Oauth-integration
```

### 2. Create a virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and fill in the real values:

```env
META_APP_ID=your_meta_app_id_here
META_APP_SECRET=your_meta_app_secret_here
REDIRECT_URI=https://your-domain.com/auth/callback
FLASK_SECRET_KEY=generate_a_random_secret_key_here
VERIFY_TOKEN=choose_any_secret_verify_token_here
INSTAGRAM_REDIRECT_URI=https://your-domain.com/instagram/auth/callback
APP_BASE_URL=https://your-domain.com
SMTP_HOST=smtp.your-provider.com
SMTP_PORT=587
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_email_password
HUMAN_AGENT_ALERT_TO=alerts@example.com
```

### 5. Run the app

```bash
python app.py
```

If your local entrypoint differs, start the Flask app using the command defined in your deployment setup.

## Required Meta Setup

Before connecting the app, you will need:

- A Meta developer app
- Facebook Login enabled
- Messenger permissions approved or in development mode for test users
- Instagram Graph API permissions for professional accounts
- A public HTTPS callback URL for OAuth and webhooks
- A webhook URL pointing to your deployed app

The app uses Meta Graph API v22.0.

## Environment Variables

The most important variables are:

- `META_APP_ID`
- `META_APP_SECRET`
- `REDIRECT_URI`
- `INSTAGRAM_REDIRECT_URI`
- `FLASK_SECRET_KEY`
- `VERIFY_TOKEN`
- `APP_BASE_URL`
- `GEMINI_API_KEY`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `HUMAN_AGENT_ALERT_TO`

## Deployment Notes

- `Procfile` starts the app with Gunicorn on port `5003`
- `gunicorn.conf.py` contains production-friendly worker and logging settings
- The app is compatible with AWS Elastic Beanstalk deployment
- Keep `.env` and token storage files out of GitHub

## Security Notes

- Never commit `.env`, access tokens, or generated JSON storage files
- Use a strong `FLASK_SECRET_KEY`
- Keep `VERIFY_TOKEN` unique per environment
- Use HTTPS for OAuth redirects and webhook endpoints

## Useful Endpoints

- `/` - landing page
- `/connect` - Messenger OAuth start
- `/auth/callback` - Messenger OAuth callback
- `/dashboard` - Messenger dashboard
- `/instagram/connect` - Instagram OAuth start
- `/instagram/auth/callback` - Instagram OAuth callback
- `/instagram/dashboard` - Instagram dashboard
- `/instagram/comments/<ig_account_id>` - Instagram comments dashboard
- `/webhook` - webhook verification and events
- `/messenger` - alternate webhook endpoint
- `/api/...` - debugging and operational APIs

## Notes

This repository is set up for a production-style Meta integration workflow, not a toy demo. It includes message persistence, webhook diagnostics, and human-agent escalation so it can be used as a base for a real support or sales automation system.
