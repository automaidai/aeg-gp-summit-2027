# AEG Global Partnerships Summit 2027

An English, responsive event companion for **11–13 January 2027**, ROBINSON Fleesensee. Prepared for Vercel. Uses the supplied GP27 artwork, original pink `#ef87b5`, red `#bd1622`, dark `#211d13`, a continuous pink canvas, poster-style cards with sharp black frames, pink/red/black surfaces and GP27 motifs, and bundled Gilroy fonts.

## What is delivered

- App-style desktop sidebar and fixed mobile bottom navigation.
- Home with large original GP27 logo and countdown.
- Three-day agenda with automatic Google Sheet CSV refresh every 30 seconds while the agenda is open.
- Stay, explicit F&B inclusion slots, arrival and departure guides.
- Speaker profile layout with portrait, biography and LinkedIn link when supplied.
- Photo wall: local demo immediately; shared uploads and private storage once configured.
- Ten team views and search by participant name or team.
- Coffee versus beer + wine contest, total split, undo, shared atomic logging when configured.
- Thai and Katie contact cards with photo, email and phone fields.
- Ten video slots with server-enforced scheduled link release.
- Home-screen manifest, app icon and install guidance. This is an online companion; offline access and push notifications are not implemented.

## Preview locally

Python 3.9 or later is enough, with no package installation:

```sh
cd summit-2027
python3 dev.py
```

Open http://127.0.0.1:4173. The preview banner is intentional. With no backend credentials, photos and drink counts are saved only in that browser, and the agenda is clearly labelled as illustrative. No sample speakers, attendee names, contact addresses, F&B promises or travel times are invented.

## Deploy on Vercel

1. Put the contents of this project in a Git repository and import it into Vercel.
2. Choose Framework Preset **Other**, set the root directory to this folder, and leave the build command empty. `vercel.json` sets `public` as the output directory. The root `api/app.py` is a Vercel Python function. Python 3.12 is pinned in `.python-version`.
3. Deploy. With no credentials the result is an explicit design/demo preview.
4. To enable shared features, complete the Supabase steps below, add the environment variables to Vercel, and redeploy.

The static interface and API are served from the same origin. No Node.js build is required. Vercel deployment itself has not been performed or verified in this handoff.

Runtime reference: https://vercel.com/docs/functions/runtimes/python
Configuration reference: https://vercel.com/docs/project-configuration/vercel-json

## Enable shared photos and drink counts

1. Create a Supabase project, then run `backend/schema.sql` once in its SQL editor. This creates the tables, narrowly scoped server-only RPC functions, and a **private** `summit-photos` bucket. Do not run the initial schema repeatedly against an existing production database.
2. In Vercel environment settings, add:

| Variable | Value |
|---|---|
| `SUPABASE_URL` | Project URL from Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side service-role key; never expose in `public/` |
| `EVENT_ACCESS_CODE` | Event code distributed to attendees by the organisers |
| `SESSION_SECRET` | A random secret with at least 32 bytes of entropy |
| `GOOGLE_SHEET_CSV_URL` | Optional published Google Sheet CSV URL |

All four core variables must be present for live mode. No real credentials are included. Create `SESSION_SECRET` using your preferred secret generator. This project does not automatically load `.env` locally; export local environment variables before starting `dev.py`.

Attendees enter the event code in the photo, drink or video area. It creates a signed, HTTP-only browser session. Production cookies are Secure and SameSite=Lax. This is a shared event-code gate, not individual employee SSO. The code must be treated as access to the attendee gallery. Own-upload deletion is tied to the browser session, not the display name. Organisers can moderate or remove any photo through the Supabase dashboard.

Uploads are resized to a maximum 1600 px in the browser and re-encoded as JPEG, removing original file metadata. The API rejects non-JPEG data and files over 2.5 MB. A private bucket serves one-hour signed image links only after event-code access. The gallery shows the latest 100 images. There is a 10-second per-session upload interval and a 30-second drink interval. Drink writes use an atomic database lock, and the live contest only accepts logs on 11–13 January 2027 in Europe/Berlin time. Returning attendees can undo their most recent log during the current page session.

No shared-storage end-to-end check has been run because no Supabase account or credentials were supplied. Run the acceptance checklist below after configuration. Storage billing, retention and attendee distribution remain with the event organisers.

## Connect the Google Sheet

Create a dedicated sheet tab containing **only publishable event programme data**. Use these exact lower-case headers:

```csv
date,time,title,location,type,speaker
2027-01-11,15:00,Confirmed session title,Confirmed room,Session,Confirmed speaker
```

- `date`: ISO date, one of `2027-01-11`, `2027-01-12`, `2027-01-13`.
- `time`: zero-padded `HH:MM`, Germany local time (CET).
- All six headers are required; `location`, `type`, `speaker` cells may be empty.
- Publish the dedicated tab to the web as CSV. Put its `https://docs.google.com/.../pub?...&output=csv` URL in `GOOGLE_SHEET_CSV_URL`.
- The API reads it on demand; visitors refresh every 30 seconds. Google's publication cache can introduce additional delay.
- Missing or invalid sources produce a visible warning and explicitly labelled sample content. An empty valid day displays “not published yet”. The API never pretends sample entries are confirmed.

The Google Sheet is not connected yet. A published CSV is public to anyone who has its URL; do not include internal attendee data in that tab. If a private sheet is needed, replace this adapter with an authenticated server-side Google Sheets integration.

## Update content

Edit `public/config.js` for:

- Confirmed F&B inclusions and exclusions (currently all pending).
- Arrival/departure arrangements, transfer details and room arrangements.
- Speaker name, role, company, bio, photo URL, LinkedIn URL.
- Thai and Katie's portraits, confirmed contact names, email addresses and phone numbers.
- Ten team names and participant arrays. Search works immediately once names are entered.

Use `/assets/...` paths for local portraits. Supplied brand files are in `public/assets`; original design references are retained separately under `reference/` and excluded from deployment and the handoff ZIP. The supplied font EULA is retained with the fonts. The supplied AEG Global Partnerships EPS paths are preserved as a sharp SVG in the desktop and mobile header (white on the dark sidebar, black on pink). The exact supplied GP27 logo is used as image artwork.

## Release team videos

Edit `backend/content.json`, not a public JavaScript file. For each team set an HTTPS video-file URL and a timezone-qualified release time:

```json
{
  "team_id": 1,
  "title": "Team 01",
  "url": "https://your-video-host.example/team-01.mp4",
  "release_at": "2027-01-13T10:30:00+01:00"
}
```

Redeploy when changing these values. A missing URL or release time leaves the video locked. Before release, the server omits the URL entirely from its response. After release, attendees can play it with native mobile controls. Use a direct MP4/WebM media URL, not a YouTube watch-page URL. Time gating hides the app's link until release; it does not enforce access on the external video host. Use a protected media host if the file itself must be confidential. There is no organiser admin dashboard; manual releases are file edits plus redeployment.

## Validation

Run:

```sh
python3 -m unittest discover -s tests -v
```

Eight automated checks cover demo/live separation, unauthenticated access, cross-origin mutations, signed-cookie tampering, video release boundaries, own-photo deletion, service-error redaction and the missing-sheet state.

Local browser checks completed: desktop and 390 px mobile layout, agenda day switching, coffee logging and undo, photo upload/render/remove, and team search. The preview uses sample content and browser-local demo records. Server-side live storage, SQL execution against Supabase, video-host playback and Vercel deployment still need checking with real service configuration.

### Live acceptance checklist

- Confirm all pending content and replace the illustrative agenda using the real sheet.
- In two separate browsers, sign in with the event code. Upload a photo in one; verify it appears in the other, and only the original session can delete it.
- On event dates, log coffee/beer/wine and verify shared counts and undo; confirm rate limits with rapid duplicate clicks.
- Test a video with a future release and a past release; verify only released URLs appear in API output.
- Verify a failed backend connection produces a visible error and does not switch a live session to local demo data.
- Verify contact links, participant assignments and all media on iOS and Android.

Hotel/address reference: https://www.robinson.com/en/en/resort-holiday/germany/fleesensee/club-details/
