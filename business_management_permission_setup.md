# Adding `business_management` Permission — Setup Guide

## Problem
The current OAuth flow (Facebook Login for Business) only requests Page-level
permissions:
- `pages_show_list`
- `pages_messaging`
- `pages_manage_metadata`
- `pages_read_engagement` (or similar)

`business_management` is **not included in the scope**, so it never appears in
the consent dialog, and Meta's App Review team cannot see it being used.

---

## Requirements Before Starting

1. **Business Verification must be completed** on the Business Manager that
   owns this app.
   - Go to: `business.facebook.com` → Business Settings → Security Center
   - If not verified, submit verification first — `business_management` will
     be auto-rejected in App Review without this, regardless of the demo.

2. **Test account must be an admin of a real Business Portfolio** (Business
   Manager), not just a Page admin. Without this, the "Choose Business" screen
   will not appear even with the correct scope.

---

## Step 1 — Update the OAuth Scope

### If using direct OAuth URL:
Add `business_management` to the `scope` parameter:

```
https://www.facebook.com/v22.0/dialog/oauth?
client_id=676537285287395
&redirect_uri=https://messenger-integration.nanovate.io/auth/callback
&scope=pages_show_list,pages_messaging,pages_manage_metadata,business_management
&state=RANDOM_STATE_STRING
```

### If using Facebook JS SDK:
```javascript
FB.login(function(response) {
  // handle response
}, {
  scope: 'pages_show_list,pages_messaging,pages_manage_metadata,business_management',
  extras: { feature: 'login_for_business' } // if using Login for Business config
});
```

### If using a server-side SDK (Node/PHP/Python):
Add `business_management` to whatever permissions array/list is passed into
the login URL builder.

---

## Step 2 — Verify the New Consent Screen Appears

After the scope change, log in with a **Business Manager admin test account**
and confirm you now see an additional screen such as:

> **"Choose the Business you want messenger-agent to access"**

This screen must appear in the flow — it is what Meta's reviewer expects to
see in the screencast.

---

## Step 3 — Build a Real Feature That Uses the Permission

Meta rejects `business_management` requests that aren't visibly used in the
product. After the user grants access, call the Graph API and show the result
in the UI. Example:

```javascript
// After OAuth, use the access token to fetch the business
GET https://graph.facebook.com/v22.0/me/businesses
  ?access_token={user_access_token}
```

or, once you have a business_id:

```javascript
GET https://graph.facebook.com/v22.0/{business_id}/owned_pages
  ?access_token={user_access_token}
```

Use this data to populate a screen in your app — e.g., in the
"Connect Your Meta Channels" step — showing:

> "Business: Nanovate → [list of Pages/WABAs under this business]"

Let the user pick the correct asset. **This is the exact use case you will
describe in the App Review submission text**, so the video and the written
description must match.

---

## Step 4 — Record the App Review Screencast

Record one continuous, unedited video:

1. Start logged out of the app.
2. Click "Connect with Facebook" from the Nanovate connect screen.
3. Let the Facebook Login for Business dialog fully load — show the full
   permission list including `business_management`.
4. Log in using the test Business Manager admin account.
5. Show the new **"Choose the Business"** screen and select a business.
6. Show the redirect back to Nanovate.
7. Show the actual feature: the list of assets/pages pulled via the
   `business_management`-scoped API call, and the user selecting one.

---

## Step 5 — Fill the App Review Submission Text

In the "How will you use this permission" field for `business_management`,
write exactly what is shown in the video, for example:

> "After a client authorizes Nanovate via Facebook Login for Business, we call
> the Business Manager API to list the Pages, WhatsApp Business Accounts, and
> Instagram assets owned by their Business Portfolio. This lets the client
> select the correct asset to connect to Nanovate's messaging integration,
> instead of requiring them to manually enter IDs."

---

## Checklist Before Submitting

- [ ] Business Verification completed
- [ ] `business_management` added to OAuth scope
- [ ] Tested with a real Business Manager admin account
- [ ] "Choose the Business" screen confirmed working
- [ ] Feature built that visibly uses the returned business/asset data
- [ ] Screencast recorded showing the full flow end-to-end
- [ ] Submission text matches exactly what's shown in the video
