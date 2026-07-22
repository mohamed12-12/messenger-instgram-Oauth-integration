# API Reference

This document summarizes the primary routes and APIs exposed by the app.

## HTML Routes

### Messenger pages

- `GET /` - Messenger landing page
- `GET /connect` - start Messenger OAuth
- `GET /auth/callback` - Messenger OAuth callback
- `GET /connect-page/<page_id>` - connect the selected Facebook Page
- `GET /dashboard`
- `GET /dashboard/<page_id>`

### Instagram pages

- `GET /instagram`
- `GET /instagram/connect` - start Instagram OAuth
- `GET /instagram/auth/callback` - Instagram OAuth callback
- `GET /instagram/dashboard`
- `GET /instagram/dashboard/<ig_account_id>`
- `GET /instagram/comments/<ig_account_id>`

## Webhook Routes

### Messenger

- `GET /webhook`
- `GET /messenger`
- `POST /webhook`
- `POST /messenger`

Purpose:

- verify the Messenger webhook
- receive page and fallback Instagram webhook payloads

### Instagram

- `GET /instagram/webhook`
- `POST /instagram/webhook`

Purpose:

- verify the Instagram webhook
- receive Instagram messaging events

## Messaging Actions

### Page user content review

- `GET /api/page-user-content?page_id=<page_id>`
- `GET /api/page-engagement?page_id=<page_id>`
- `POST /api/page-posts/publish`
- `POST /api/page-user-comment/reply`
- `POST /api/page-user-comment/delete`

Purpose:

- reads recent Page posts, user comments, ratings/recommendations, and tagged posts through the connected Page token
- reads Page metadata and post engagement counts through the connected Page token
- publishes a text post to the connected Facebook Page
- returns simple records with Page, post, author, text, time, and identifiers
- replies to a selected user comment after verifying it belongs to the connected Page
- deletes a selected user comment after verifying it belongs to the connected Page
- demonstrates the `pages_read_user_content` permission for Meta App Review

Success response:

```json
{
  "success": true,
  "page_id": "...",
  "permission_used": "pages_read_user_content",
  "graph_edge": "/<page_id>/feed",
  "posts": [],
  "comments": [],
  "ratings": [],
  "tagged_posts": [],
  "post_count": 0,
  "comment_count": 0,
  "rating_count": 0,
  "tagged_post_count": 0
}
```

### Messenger manual send

- `POST /send-message`

Form fields:

- `recipient_id`
- `message`
- `page_id` optional if session already contains connected page

Success response:

```json
{
  "success": true,
  "result": {
    "message_id": "..."
  }
}
```

### Instagram manual send

- `POST /instagram/send`

Form fields:

- `recipient_psid`
- `message`
- `page_id` optional if session already contains connected Instagram account

## Instagram Comments APIs

### Fetch comments

- `GET /api/instagram/comments?ig_account_id=<id>`

Returns:

- `success`
- `comments`
- optional `message` when no comments are found

### Reply to comment

- `POST /api/instagram/reply-comment`

Request body or form fields:

- `ig_account_id`
- `comment_id`
- `message`

### Hide comment

- `POST /api/instagram/hide-comment`

Request body or form fields:

- `ig_account_id`
- `comment_id`

### Delete comment

- `POST /api/instagram/delete-comment`

Request body or form fields:

- `ig_account_id`
- `comment_id`

## Read APIs

### Messenger recent page messages

- `GET /api/recent-messages?page_id=<page_id>`

### Global recent messages

- `GET /api/messages`

### Recent Instagram messages

- `GET /api/recent-instagram-messages?page_id=<ig_account_id>`

### Webhook hit log

- `GET /api/webhook-last-hit`

### Raw webhook debug payload

- `GET /api/webhook-debug`

### App config

- `GET /api/config`

## Debug APIs

### Page debug

- `GET /api/debug/<page_id>`

Useful fields include:

- `page_token_exists`
- `subscribed_fields`
- `page_message_count`
- `page_has_webhook_hit`
- `page_last_webhook_timestamp`
- `subscription_error`

### Page webhook status

- `GET /api/page-webhook-status/<page_id>`

### Messenger debug

- `GET /api/messenger-debug?page_id=<page_id>`

### Instagram debug

- `GET /api/instagram-debug?page_id=<ig_account_id>`

### Meta subscription check

- `GET /api/check-subscription`

This endpoint checks `me/accounts` using the user access token from session and reports whether returned pages are subscribed.

## Compliance Endpoints

- `POST /instagram/deauth`
- `POST /instagram/data-deletion`

These exist for Meta platform compliance flows.

## Notes on Authentication and State

- Some routes rely on session data after OAuth
- Some routes also accept explicit page/account IDs in the URL or request
- Tokens are persisted to JSON files so dashboard routes can still work after the initial connection flow
