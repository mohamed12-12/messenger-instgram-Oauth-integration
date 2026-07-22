# Meta App Review: `pages_read_user_content`

This project now has a reviewer-visible flow for `pages_read_user_content`.

## What changed

- Messenger OAuth requests `pages_read_user_content`.
- The dependency `pages_show_list` is already requested.
- The app calls `GET /{page_id}/feed` after a Page is connected.
- The Messenger dashboard shows the result in the Page User Content Review section.

## App Review use case text

Use this in the `pages_read_user_content` permission request:

> Nanovate uses `pages_read_user_content` to let an authorized Page admin review recent Page feed content and comments inside the Messenger integration dashboard. After the admin connects their Facebook Page, the app calls the Page feed endpoint with the connected Page access token and displays recent feed items and comments so the admin can monitor user-generated Page activity before responding through the messaging workflow.

## Screencast steps

Record one continuous video:

1. Start logged out of the Nanovate test project.
2. Open `/` and click the Facebook connect button.
3. Complete Meta Login with a test user who can manage the target Page.
4. Show that the app requests Page permissions including `pages_read_user_content`.
5. Select the Business Portfolio if Meta shows that step.
6. Select the Facebook Page.
7. Open `/dashboard/<page_id>`.
8. Click `Load Latest Page Feed`.
9. Show the app displaying feed items and recent comments loaded from Meta.

## Test setup checklist

- The Meta test user is assigned to the app as a role user or is allowed to test the app.
- The test user can manage the Page selected in the flow.
- The selected Page has at least one feed item or comment that can appear in the dashboard.
- The app has `pages_read_engagement`, `pages_read_user_content`, and `pages_show_list` in the OAuth scope.
- The video, written use case, and live app all show the same feature.

## Current implementation

- OAuth scope: `SCOPES` in `app.py`
- Graph read helper: `fetch_page_user_content` in `app.py`
- API route: `GET /api/page-user-content`
- Dashboard UI: `templates/dashboard.html`
