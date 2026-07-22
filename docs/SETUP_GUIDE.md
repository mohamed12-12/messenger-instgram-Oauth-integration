# Setup Guide

This guide walks through everything needed to run and configure the Messenger and Instagram integration.

## 1. Prerequisites

You need:

- Python 3.x
- A Meta developer app
- At least one Facebook Page
- An Instagram Business or Creator account linked to a Facebook Page
- A public HTTPS domain for OAuth callbacks and webhooks

## 2. Install and Run Locally

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

The local app runs on port `5000` unless `PORT` is set.

## 3. Environment Configuration

Start from [`.env.example`](</c:/Users/Mo/Desktop/nanovate tech/Projects/messenger-instgram-Oauth-integration/.env.example>).

Example:

```env
META_APP_ID=your_meta_app_id_here
META_APP_SECRET=your_meta_app_secret_here
FLASK_SECRET_KEY=replace_with_a_long_random_secret
VERIFY_TOKEN=nanovate_messenger_verify_2026
APP_BASE_URL=https://your-domain.com

REDIRECT_URI=https://your-domain.com/auth/callback
MESSENGER_WEBHOOK_URL=https://your-domain.com/webhook
MESSENGER_DASHBOARD_URL=https://your-domain.com/dashboard

INSTAGRAM_REDIRECT_URI=https://your-domain.com/instagram/auth/callback
INSTAGRAM_WEBHOOK_URL=https://your-domain.com/instagram/webhook
INSTAGRAM_DASHBOARD_URL=https://your-domain.com/instagram/dashboard
INSTAGRAM_COMMENTS_URL=https://your-domain.com/instagram/comments/<ig_account_id>

PORT=5000
```

Important:

- `REDIRECT_URI` and `INSTAGRAM_REDIRECT_URI` must exactly match the URLs configured in Meta
- `VERIFY_TOKEN` must exactly match the verify token used when configuring webhooks
- The webhook URL vars are reference values for your team; the current app logic does not read them directly

## 4. Meta App Configuration

### Required products

Enable:

- Facebook Login
- Messenger
- Instagram Graph / Instagram integration features used by your app setup

### App mode

Use `Development` while testing with test users and roles.
Switch to `Live` when you are ready for production usage and webhook subscriptions in production.

### Permissions and scopes used by the app

Messenger flow requests:

- `pages_messaging`
- `pages_manage_metadata`
- `pages_read_engagement`
- `pages_read_user_content`
- `pages_show_list`
- `business_management`

Instagram flow requests:

- `instagram_basic`
- `instagram_manage_messages`
- `instagram_manage_comments`
- `pages_messaging`
- `pages_read_engagement`
- `pages_show_list`
- `pages_manage_metadata`

## 5. OAuth Callback URLs

Configure these in Meta:

- Messenger callback: `https://your-domain.com/auth/callback`
- Instagram callback: `https://your-domain.com/instagram/auth/callback`

Make sure the configured URLs are identical to the values in `.env`.

## 6. Webhook Configuration

### Messenger webhook

Use:

- Callback URL: `https://your-domain.com/webhook`
- Verify token: your `VERIFY_TOKEN`

The app also exposes `/messenger` as an alternate Messenger webhook path.

### Instagram webhook

Use:

- Callback URL: `https://your-domain.com/instagram/webhook`
- Verify token: your `VERIFY_TOKEN`

The webhook verification handlers return the Meta challenge when the verify token matches.

## 7. Messenger Connection Flow

To connect a Facebook Page:

1. Open `/`
2. Click `Connect with Facebook`
3. Complete Meta login and permission grant
4. Select the Facebook Page returned by Meta
5. The app saves the page token locally
6. The app subscribes the page to webhook events
7. Open `/dashboard/<page_id>`

## 8. Instagram Connection Flow

To connect an Instagram Business account:

1. Open `/instagram/connect`
2. Complete Meta login and permission grant
3. The app fetches Facebook Pages available to the user
4. The app checks each page for `instagram_business_account`
5. The first linked Instagram business account is stored locally
6. Open `/instagram/dashboard/<ig_account_id>`

Important:
The Instagram flow depends on an Instagram Business or Creator account being linked to a Facebook Page.

## 9. Dashboard Usage

### Messenger dashboard

URL:

- `/dashboard`
- `/dashboard/<page_id>`

Use it to:

- Send manual messages to a PSID
- View recent page events
- Refresh Facebook Page posts, comments, ratings/recommendations, and tagged posts for App Review testing of `pages_read_user_content`
- Check page subscription and debug state

### Instagram messaging dashboard

URL:

- `/instagram/dashboard`
- `/instagram/dashboard/<ig_account_id>`

Use it to:

- Send manual Instagram messages to a PSID
- View recent Instagram webhook events
- Inspect webhook health

### Instagram comments dashboard

URL:

- `/instagram/comments/<ig_account_id>`

Use it to:

- Load recent comments
- Reply to comments
- Hide comments
- Delete comments

## 10. Deployment

### Procfile

[Procfile](</c:/Users/Mo/Desktop/nanovate tech/Projects/messenger-instgram-Oauth-integration/Procfile>) starts the app with:

```text
web: gunicorn app:app --bind 0.0.0.0:5003 --workers 2 --threads 2 --timeout 60 --access-logfile - --error-logfile -
```

### Gunicorn

[gunicorn.conf.py](</c:/Users/Mo/Desktop/nanovate tech/Projects/messenger-instgram-Oauth-integration/gunicorn.conf.py>) contains production defaults for:

- workers
- threads
- timeouts
- stdout/stderr logging

### AWS Elastic Beanstalk

[01_flask.config](</c:/Users/Mo/Desktop/nanovate tech/Projects/messenger-instgram-Oauth-integration/.ebextensions/01_flask.config>) includes:

- `PYTHONPATH`
- WSGI path
- static file proxy mapping

## 11. Validation Checklist

Before handing off or going live, verify:

1. OAuth callback URLs exactly match Meta settings
2. Verify token matches Meta webhook configuration
3. Messenger page connection works and saves a page token
4. Instagram connection finds the correct business account
5. Messenger webhook verification returns `200`
6. Instagram webhook verification returns `200`
7. Recent events appear in both dashboards
8. Manual Messenger send works
9. Manual Instagram send works
10. Instagram comments load and actions succeed
