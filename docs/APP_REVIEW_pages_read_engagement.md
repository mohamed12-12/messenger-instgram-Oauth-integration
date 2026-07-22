# Meta App Review: `pages_read_engagement`

This project now has a reviewer-visible flow for `pages_read_engagement`.

## What changed

- Messenger OAuth already requests `pages_read_engagement`.
- The dashboard has a simple `Page Engagement` section.
- The app reads Page metadata and recent post engagement counts from the connected Facebook Page.

## App Review use case text

Use this in the `pages_read_engagement` permission request:

> Nanovate uses `pages_read_engagement` to let an authorized Page admin view basic Page engagement and recent post engagement inside the Nanovate dashboard. After the admin connects their Facebook Page, Nanovate reads Page metadata and recent post engagement counts such as reactions, comments, and shares using the connected Page access token. This helps the Page admin understand which Page posts are receiving engagement before managing posts and comments.

## Screencast steps

Record one continuous video:

1. Start logged out of the Nanovate test project.
2. Open `/` and click the Facebook connect button.
3. Complete Meta Login with a test user who can manage the target Page.
4. Show that the app requests Page permissions including `pages_read_engagement`.
5. Select the Business Portfolio if Meta shows that step.
6. Select the Facebook Page.
7. Open `/dashboard/<page_id>`.
8. Find the `Page Engagement` section.
9. Click `Refresh Engagement`.
10. Show the Page-level engagement fields and recent post reactions, comments, and shares.
11. Open one Facebook post if needed to show that the engagement belongs to the connected Page.

## Test setup checklist

- The Meta test user can manage the selected Facebook Page.
- The selected Page has recent posts.
- The selected Page has at least one post with reactions, comments, or shares if possible.
- The app has `pages_read_engagement` and `pages_show_list` in the OAuth scope.
- Reconnect Facebook after deployment if the current Page token was created before the permission was requested.

## Current implementation

- OAuth scope: `SCOPES` in `app.py`
- Graph helper: `fetch_page_engagement_summary`
- API route: `GET /api/page-engagement`
- Dashboard UI: `templates/dashboard.html`
