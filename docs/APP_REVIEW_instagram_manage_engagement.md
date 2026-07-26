# Meta App Review: instagram_manage_engagement

This project demonstrates `instagram_manage_engagement` from the Instagram comments dashboard.

## Permission Use

Nanovate uses `instagram_manage_engagement` so an authorized operator can like and unlike Instagram comments from the moderation interface through the Graph API.

The reviewer can load recent comments, pick a visible Instagram comment, click `Like`, then click `Unlike` on the same comment and watch both actions complete from the dashboard.

## Reviewer Video Steps

1. Open `/instagram/connect`.
2. Complete Meta login and grant the requested Instagram permissions.
3. Select the Business/Page linked to the Instagram professional account.
4. Open `/instagram/comments/<ig_account_id>`.
5. Click `Refresh` to load recent Instagram comments.
6. Show the permission note mentioning `instagram_manage_engagement`.
7. Click `Like` on a comment card.
8. Show the success message.
9. Click `Unlike` on the same comment.
10. Show the success message again.

## What Meta Should See

- Connected Instagram account username
- Instagram account ID
- Real Instagram comment loaded into the dashboard
- `Like` action on the comment
- `Unlike` action on the comment
- Success status after each Graph API request

## Notes

- This flow uses the Instagram Graph API `user_likes` action on the connected Instagram account.
- After deployment, reconnect the Instagram account so the saved token includes `instagram_manage_engagement`.
