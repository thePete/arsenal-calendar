# Arsenal FC calendar (.ics)

Auto-updating calendar of Arsenal fixtures (Premier League, Champions League, FA Cup, Carabao Cup) with US TV listings, built from ESPN's public data every 6 hours by GitHub Actions.

- Event title: `⚽ Arsenal vs Spurs (H)` / `⚽ Brighton vs Arsenal (A)`. Scores are never shown, even for finished games.
- Location field: TV channel(s), or `TBD` until the broadcaster is announced.
- Matches vs Leeds United get an alert 3 days before kickoff (change `ALERT_OPPONENTS` in the script).
- Times are stored in UTC, so your calendar app shows your local time.

## Setup

1. Create a new **public** repo (e.g. `arsenal-calendar`) and add these files, keeping the folder structure (`.github/workflows/`, `scripts/`, `docs/`).
2. **Settings → Actions → General → Workflow permissions**: choose **Read and write permissions** and save.
3. **Actions** tab → **Update Arsenal calendar** → **Run workflow**. It should finish green and commit `docs/arsenal.ics`.
4. **Settings → Pages**: Source **Deploy from a branch**, branch `main`, folder `/docs`. Save.
5. After a minute or two, your calendar is at:
   `https://<your-username>.github.io/arsenal-calendar/arsenal.ics`

## Subscribe

- **Apple Calendar (Mac):** File → New Calendar Subscription → paste the URL → set Auto-refresh to "Every hour".
- **iPhone:** Settings → Calendar → Accounts → Add Account → Other → Add Subscribed Calendar.
- **Google Calendar (web):** Other calendars **+** → From URL → paste the URL. (Google refreshes every 12–24 hours.)
- **Outlook:** Add calendar → Subscribe from web.

Use *subscribe*, not *import*; importing makes a one-time copy that won't update.

## Tweaks

Edit the top of `scripts/build_calendar.py`: `COMPETITIONS` to add or remove competitions, `MATCH_LENGTH` for event duration.
