# Meta App Review: `read_insights`

This project now has a reviewer-visible flow for `read_insights`.

## What changed

- Messenger OAuth requests `read_insights`.
- The dashboard has a simple `Page Insights` section.
- The app reads Page and post analytics metrics through the Graph API `/insights` edge.

## App Review use case text

Use this in the `read_insights` permission request:

> Nanovate uses `read_insights` to let an authorized Page admin view Page and post analytics inside the Nanovate dashboard. After the admin connects their Facebook Page, Nanovate reads available Page insights and recent post insights through Meta's Insights API using the connected Page access token. This helps the Page admin understand aggregate performance metrics, such as post engagements, reaction metrics, post activity, and click metrics, before deciding what Page content to manage or publish.

## Screencast steps

Record one continuous video:

1. Start logged out of the Nanovate test project.
2. Open `/` and click the Facebook connect button.
3. Complete Meta Login with a test user who can manage the target Page.
4. Show that the app requests Page permissions including `read_insights`.
5. Select the Business Portfolio if Meta shows that step.
6. Select the Facebook Page.
7. Open `/dashboard/<page_id>`.
8. Find the `Page Insights` section.
9. Click `Refresh Insights`.
10. Show Page-level insight metrics loaded from Meta.
11. Show recent post insight metrics loaded from Meta.

## Test setup checklist

- The Meta test user can manage the selected Facebook Page.
- The selected Page has recent Page activity and recent posts.
- The app has `read_insights`, `pages_read_engagement`, and `pages_show_list` in the OAuth scope.
- Reconnect Facebook after deployment so the Page token includes `read_insights`.
- If Meta marks one metric unavailable, show another available metric in the same section.

## Current implementation

- OAuth scope: `SCOPES` in `app.py`
- Graph helper: `fetch_page_insights_summary`
- API route: `GET /api/page-insights`
- Dashboard UI: `templates/dashboard.html`
