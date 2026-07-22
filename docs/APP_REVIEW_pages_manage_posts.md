# Meta App Review: `pages_manage_posts`

This project now has a reviewer-visible flow for `pages_manage_posts`.

## What changed

- Messenger OAuth requests `pages_manage_posts`.
- The dashboard has a simple `Create Page Post` section.
- The app publishes a text post to the connected Facebook Page with the Page access token.

## App Review use case text

Use this in the `pages_manage_posts` permission request:

> Nanovate uses `pages_manage_posts` to let an authorized Page admin publish a text post to their connected Facebook Page from the Nanovate dashboard. The admin connects Facebook, selects the Page they manage, writes a post message, clicks Publish Post, and Nanovate publishes the post using the connected Page access token. The dashboard then displays the returned Facebook Post ID and a link to open the published post on Facebook.

## Screencast steps

Record one continuous video:

1. Start logged out of the Nanovate test project.
2. Open `/` and click the Facebook connect button.
3. Complete Meta Login with a test user who can manage the target Page.
4. Show that the app requests Page permissions including `pages_manage_posts`.
5. Select the Business Portfolio if Meta shows that step.
6. Select the Facebook Page.
7. Open `/dashboard/<page_id>`.
8. Find the `Create Page Post` section.
9. Type a short test post.
10. Click `Publish Post`.
11. Show the success message with the returned Post ID.
12. Open the published post on Facebook and show it appears on the connected Page.

## Test setup checklist

- The Meta test user can manage the selected Facebook Page.
- The app has `pages_manage_posts`, `pages_read_engagement`, and `pages_show_list` in the OAuth scope.
- Reconnect Facebook after deploying this change so the Page token includes `pages_manage_posts`.
- Use harmless test post text that is safe to publish publicly on the test Page.

## Current implementation

- OAuth scope: `SCOPES` in `app.py`
- API route: `POST /api/page-posts/publish`
- Dashboard UI: `templates/dashboard.html`
