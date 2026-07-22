# Meta App Review: `pages_read_user_content`

This project now has a reviewer-visible flow for `pages_read_user_content`.

## What changed

- Messenger OAuth requests `pages_read_user_content`.
- The dependency `pages_show_list` is already requested.
- The app calls Page user-content Graph edges after a Page is connected.
- The Messenger dashboard shows the result in the Facebook Page Comments section.

## App Review use case text

Use this in the `pages_read_user_content` permission request:

> Nanovate uses `pages_read_user_content` to let an authorized Page admin view user-generated content for Page management. After the admin connects their Facebook Page, the app retrieves recent Page posts, user comments on those posts, Page ratings/recommendations, and posts that tag the Page. The dashboard displays the Page name, post context, comment author, comment text, comment time, ratings/recommendations, and tagged posts. The admin can also delete a user comment from a Page post when needed for Page management.

## Screencast steps

Record one continuous video:

1. Start logged out of the Nanovate test project.
2. Open `/` and click the Facebook connect button.
3. Complete Meta Login with a test user who can manage the target Page.
4. Show that the app requests Page permissions including `pages_read_user_content`.
5. Select the Business Portfolio if Meta shows that step.
6. Select the Facebook Page.
7. Open `/dashboard/<page_id>`.
8. Open the `Facebook Page Comments` section.
9. Show the note that the screen uses `pages_read_user_content` to read Page posts, user comments, Page ratings/recommendations, tagged posts, and delete user comments for Page management.
10. Click `Refresh Comments`.
11. Show the app displaying Page posts, user comments, ratings/recommendations, and posts tagging the Page.
12. Show a comment with Page name, related post, comment author, comment text, comment time, and comment ID.
13. If safe for the test Page, click `Delete comment` on a test comment and show the success message.

## Test setup checklist

- The Meta test user is assigned to the app as a role user or is allowed to test the app.
- The test user can manage the Page selected in the flow.
- The selected Page has at least one feed item or comment that can appear in the dashboard.
- Add one test comment and, when available, one recommendation/rating or tagged post before recording.
- The app has `pages_read_engagement`, `pages_read_user_content`, and `pages_show_list` in the OAuth scope.
- The video, written use case, and live app all show the same feature.
- Create a fresh Facebook comment before the video if you need to show newly synchronized data.

## Current implementation

- OAuth scope: `SCOPES` in `app.py`
- Graph read helper: `fetch_page_user_content` in `app.py`
- API route: `GET /api/page-user-content`
- Dashboard UI: `templates/dashboard.html`
