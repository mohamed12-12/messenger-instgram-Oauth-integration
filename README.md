# Messenger, Instagram, and WhatsApp OAuth Integration

Production-oriented Flask integration for connecting Facebook Messenger and Instagram Business accounts to a custom dashboard.

The app handles:

- Meta OAuth for Facebook Pages and Instagram Business accounts
- Meta OAuth for WhatsApp Business demo connections
- Page/account token capture and local token persistence
- Messenger and Instagram webhook verification
- WhatsApp webhook verification
- Inbound event capture and recent message storage
- Manual outbound messaging from the dashboard
- Instagram comment fetch, reply, hide, and delete workflows
- Debug endpoints for subscription and webhook troubleshooting

This repository is intentionally integration-only. It does not generate AI replies or run any LLM workflow.

## Who this project is for

This project is useful if you need:

- A working Meta integration starter for Messenger and Instagram
- A dashboard for operators to inspect events and send manual replies
- A backend that can be deployed first, then integrated into a larger internal product later

## Documentation Map

- [Setup Guide](</c:/Users/Mo/Desktop/nanovate tech/Projects/messenger-instgram-Oauth-integration/docs/SETUP_GUIDE.md>)
- [API Reference](</c:/Users/Mo/Desktop/nanovate tech/Projects/messenger-instgram-Oauth-integration/docs/API_REFERENCE.md>)
- [Troubleshooting Guide](</c:/Users/Mo/Desktop/nanovate tech/Projects/messenger-instgram-Oauth-integration/docs/TROUBLESHOOTING.md>)

## Core Features

### Messenger

- Connect a Facebook Page through OAuth
- Select the page to connect after login
- Subscribe the page to webhook fields required for Messenger events
- View recent page events in the Messenger dashboard
- Send manual outbound messages to a recipient PSID

### Instagram

- Connect an Instagram Business account through the Facebook Page flow
- Detect the Instagram business account attached to a selected page
- Receive Instagram webhook events
- View recent Instagram conversation events in the dashboard
- Send manual outbound Instagram messages to a recipient PSID
- Manage Instagram comments from the comments dashboard

### WhatsApp

- Connect a WhatsApp Business Account from the main page
- Store the connected business, WABA, and phone number IDs in local JSON
- Verify the WhatsApp webhook with a dedicated verify token
- Send manual outbound WhatsApp test messages from the dashboard

### Operations and Debugging

- Persist recent events in JSON files on disk
- Persist page/account tokens locally in JSON
- Inspect webhook receipts and saved page status through debug endpoints
- Verify page subscription state from Meta

## Project Structure

- `app.py` - Main Flask application and all routes/helpers
- `templates/` - HTML templates for Messenger and Instagram dashboards
- `.env.example` - Environment variable template
- `requirements.txt` - Python dependencies
- `Procfile` - Runtime command used in deployment platforms
- `gunicorn.conf.py` - Gunicorn configuration
- `.ebextensions/` - AWS Elastic Beanstalk configuration
- `verify_token.py` - Helper script for checking a token against Meta Graph API
- `verify_ig_basic.py` - Helper script for checking an Instagram Basic token

## Quick Start

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then:

1. Copy `.env.example` to `.env`
2. Fill in the Meta app values
3. Expose the app on a public HTTPS URL
4. Configure the callback URLs and webhooks in Meta

Full instructions live in the [Setup Guide](</c:/Users/Mo/Desktop/nanovate tech/Projects/messenger-instgram-Oauth-integration/docs/SETUP_GUIDE.md>).

## Required Environment Variables

These are the app-critical values:

- `META_APP_ID`
- `META_APP_SECRET`
- `FLASK_SECRET_KEY`
- `VERIFY_TOKEN`
- `REDIRECT_URI`
- `INSTAGRAM_REDIRECT_URI`
- `WHATSAPP_REDIRECT_URI`
- `WHATSAPP_VERIFY_TOKEN`

These are documented reference URLs for deployment and Meta setup:

- `APP_BASE_URL`
- `MESSENGER_WEBHOOK_URL`
- `MESSENGER_DASHBOARD_URL`
- `INSTAGRAM_WEBHOOK_URL`
- `INSTAGRAM_DASHBOARD_URL`
- `INSTAGRAM_COMMENTS_URL`

Important note:
The current code directly reads `META_APP_ID`, `META_APP_SECRET`, `FLASK_SECRET_KEY`, `VERIFY_TOKEN`, `REDIRECT_URI`, `INSTAGRAM_REDIRECT_URI`, `WHATSAPP_REDIRECT_URI`, and `WHATSAPP_VERIFY_TOKEN`.
The other URL-style env vars are documentation-friendly deployment references for your team.

## Main User Flows

### Messenger connection flow

1. Open `/`
2. Click `Connect with Facebook`
3. Finish the Meta login flow
4. Select the page returned by Meta
5. The app stores the page token and subscribes the page to webhooks
6. Open `/dashboard/<page_id>` to manage that page

### Instagram connection flow

1. Open `/instagram/connect`
2. Finish the Meta login flow
3. The app fetches the user pages
4. The app searches for a page with `instagram_business_account`
5. The Instagram account ID and page token are stored locally
6. Open `/instagram/dashboard/<ig_account_id>` to manage messaging
7. Open `/instagram/comments/<ig_account_id>` to manage comments

### WhatsApp connection flow

1. Open `/`
2. Click `Connect with WhatsApp`
3. Finish the Meta login flow with WhatsApp permissions
4. The app exchanges the code for a user access token
5. The app fetches the first accessible Business Manager, WABA, and phone number from Meta
6. The app stores the connection in `whatsapp_connection.json`
7. Open `/whatsapp/dashboard` to inspect the connected account and send a test message

## Storage Model

The app stores integration data on disk using JSON files in the project root.

Generated files include:

- `page_tokens.json` - saved page or Instagram page tokens
- `config.json` - saved page/account display context
- `recent_messages.json` - recent cross-page message history
- `messages_<page_id>.json` - Messenger events for a specific page
- `instagram_messages_<ig_account_id>.json` - Instagram events for a specific account
- `webhook_debug.json` - last raw webhook payload
- `webhook_<page_id>.json` - last webhook payload for a specific page/account
- `whatsapp_connection.json` - saved WhatsApp business, WABA, phone number, and access token
- `whatsapp_webhook_debug.json` - last raw WhatsApp webhook payload

These files should not be committed.

## Local Development Notes

- The Flask app defaults to `PORT=5000` when run directly
- The `Procfile` runs Gunicorn on port `5003`
- Gunicorn config is included for deployment environments
- Webhook testing requires a public HTTPS URL

## WhatsApp Setup and Testing

Add these environment variables to `.env`:

- `WHATSAPP_REDIRECT_URI=https://your-domain.com/whatsapp/callback`
- `WHATSAPP_VERIFY_TOKEN=your-demo-verify-token`

In the Meta App dashboard:

1. Add the WhatsApp product to the app.
2. Add `https://your-domain.com/whatsapp/callback` as a valid OAuth redirect URI.
3. Configure `https://your-domain.com/whatsapp/webhook` as the WhatsApp webhook callback URL.
4. Use the same `WHATSAPP_VERIFY_TOKEN` value during webhook verification.
5. Make sure the test user has access to the Business Manager, WhatsApp Business Account, and phone number.

For demo testing:

1. Run `python app.py`
2. Open `/` and confirm `Connect with WhatsApp` appears beside the other connect actions
3. Complete `/whatsapp/connect`
4. Confirm `/whatsapp/dashboard` shows the WABA ID, phone number ID, and display phone number
5. Send a test message from the dashboard to a valid WhatsApp recipient in international format
6. Verify the webhook from Meta against `/whatsapp/webhook`

## Security Notes

- Never commit `.env`, tokens, or generated JSON storage files
- Use a strong `FLASK_SECRET_KEY`
- Keep `VERIFY_TOKEN` unique per environment
- Only use HTTPS for OAuth redirects and webhook endpoints
- Treat the saved token files as sensitive credentials

## Deployment Notes

- The app is compatible with Gunicorn deployments
- AWS Elastic Beanstalk config is already included
- Cloud logs should include stdout/stderr from Gunicorn

Deployment details are documented in the [Setup Guide](</c:/Users/Mo/Desktop/nanovate tech/Projects/messenger-instgram-Oauth-integration/docs/SETUP_GUIDE.md>).
