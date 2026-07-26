# Meta App Review: instagram_content_publish

This project demonstrates `instagram_content_publish` from the Instagram dashboard.

## Permission Use

Nanovate uses `instagram_content_publish` so an authorized operator can publish an image post with a caption to the connected Instagram professional account.

The app does not publish without an explicit dashboard action. The reviewer can see the connected Instagram account, enter a public image URL, write a caption, publish the post, and view the returned Instagram media ID or permalink.

## Reviewer Video Steps

1. Open `/instagram/connect`.
2. Complete Meta login and grant the requested Instagram permissions.
3. Select the Business/Page that is linked to the Instagram professional account.
4. Open `/instagram/dashboard/<ig_account_id>`.
5. Confirm the dashboard shows the Instagram username and account ID.
6. In `Instagram Content Publishing`, paste a public image URL.
7. Write a short review caption.
8. Click `Publish Instagram Post`.
9. Show the success state with `instagram_content_publish`, the media ID, and the permalink when Meta returns one.
10. Open the published Instagram post from the permalink or from Instagram.

## What Meta Should See

- Connected Instagram professional account username
- Instagram account ID
- Public image URL field
- Caption field
- Explicit `Publish Instagram Post` button
- Published media ID or permalink

## Notes

- Instagram content publishing through the Graph API requires media content. This demo supports image posts with a public URL and caption.
- After deploying this change, reconnect the Instagram account so the saved token includes `instagram_content_publish`.
