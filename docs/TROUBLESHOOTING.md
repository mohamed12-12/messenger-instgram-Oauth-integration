# Troubleshooting Guide

This guide covers the most common issues when using the integration.

## OAuth Problems

### `CSRF Error. Please try again.`

Cause:

- OAuth state in session no longer matches the callback state

What to do:

1. Start the connect flow again from the app
2. Avoid opening the callback URL manually
3. Make sure session cookies are not blocked

### `Missing Facebook login code`

Cause:

- Meta did not return the authorization code

What to do:

1. Restart the OAuth flow
2. Confirm the callback URL exactly matches Meta configuration

## Messenger Connection Problems

### No Facebook Pages returned

Cause:

- The logged-in user did not grant access to the required page
- The user does not manage a page available to the app

What to do:

1. Re-run OAuth
2. Make sure the page is selected in the Meta dialog
3. Confirm the app has the required page permissions

### Page token missing after connect

Cause:

- Meta returned a page entry without an `access_token`

What to do:

1. Reconnect the page
2. Re-check the granted permissions
3. Inspect `/api/debug/<page_id>`

## Instagram Connection Problems

### No Instagram Business Account found linked to your pages

Cause:

- The selected Facebook Pages do not have an Instagram business account linked

What to do:

1. Link the Instagram Business or Creator account to a Facebook Page
2. Re-run `/instagram/connect`

### `IGAA` token errors

Cause:

- You are using an Instagram Basic Display token instead of a Page-based Graph token

What to do:

1. Reconnect using the project’s Instagram OAuth flow
2. Do not paste an IG Basic token into this app expecting messaging or comments to work

## Webhook Problems

### Webhook verification fails

Cause:

- Verify token mismatch
- Wrong callback URL

What to do:

1. Confirm Meta callback URL is correct
2. Confirm `VERIFY_TOKEN` in `.env` matches the Meta webhook form
3. Test the public deployed URL directly

### Webhook verifies but no events arrive

Cause:

- Page not subscribed
- App still in the wrong mode or missing permissions
- Meta is posting to a different URL than expected

What to do:

1. Open `/api/check-subscription`
2. Open `/api/messenger-debug`
3. Open `/api/instagram-debug`
4. Check `/api/webhook-debug`

## Messaging Problems

### Manual send returns no page token found

Cause:

- The page/account was not connected properly
- Token persistence file is missing or stale

What to do:

1. Reconnect via OAuth
2. Confirm `page_tokens.json` exists locally
3. Check the dashboard debug panel

### Messages are sent but not shown in feed

Cause:

- The token send succeeded but recent event storage did not update as expected

What to do:

1. Check `recent_messages.json`
2. Check page-specific `messages_<page_id>.json`
3. Check browser network requests to `/api/recent-messages`

## Instagram Comments Problems

### Comments API returns permissions error

Cause:

- Missing Instagram comments permission or wrong token type

What to do:

1. Reconnect using the Instagram OAuth flow
2. Confirm the app has `instagram_manage_comments`
3. Confirm the connected account is a supported business account

### Hide or delete comment fails

Cause:

- Meta rejected the action for permissions, ownership, or policy reasons

What to do:

1. Inspect the API response from `/api/instagram/hide-comment` or `/api/instagram/delete-comment`
2. Check the returned `meta_error` payload
3. Confirm the page token belongs to the page that owns the media

## Useful Helper Scripts

[verify_token.py](</c:/Users/Mo/Desktop/nanovate tech/Projects/messenger-instgram-Oauth-integration/verify_token.py>)

- Checks the configured token against Meta Graph API

[verify_ig_basic.py](</c:/Users/Mo/Desktop/nanovate tech/Projects/messenger-instgram-Oauth-integration/verify_ig_basic.py>)

- Checks whether a token is an Instagram Basic token
