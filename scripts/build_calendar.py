#!/usr/bin/env python3
"""Build an .ics calendar of Arsenal FC fixtures from ESPN's public data.

Standard library only. Times are written in UTC; calendar apps convert
them to the viewer's local time zone automatically.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

TEAM_ID = "359"  # ESPN team id for Arsenal
TEAM_NAME = "Arsenal"
COMPETITIONS = {
    "eng.1": "Premier League",
    "uefa.champions": "Champions League",
    "eng.fa": "FA Cup",
    "eng.league_cup": "Carabao Cup",
}
URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/teams/{team}/schedule"
MATCH_LENGTH = timedelta(hours=2)
# Matches against these opponents get an alert ALERT_BEFORE kickoff (all others get none).
ALERT_OPPONENTS = ["Leeds"]
ALERT_BEFORE = "P3D"  # ISO 8601 duration: 3 days
OUTPUT = os.environ.get("OUTPUT", "docs/arsenal.ics")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "arsenal-ics/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def load_events():
    """Return (events, successful_fetch_count). Fetches past + upcoming per competition."""
    events, ok = {}, 0
    for slug, comp_name in COMPETITIONS.items():
        base = URL.format(slug=slug, team=TEAM_ID)
        for url in (base, base + "?fixture=true"):
            try:
                data = fetch(url)
                ok += 1
            except Exception as e:  # one competition failing shouldn't sink the rest
                print(f"warn: {url}: {e}", file=sys.stderr)
                continue
            for ev in data.get("events", []) or []:
                if ev.get("id"):
                    events[ev["id"]] = (ev, comp_name)
    return list(events.values()), ok


def tv_channels(comp):
    """Pull US TV/streaming names from either broadcast shape ESPN uses."""
    names = []
    for b in comp.get("broadcasts", []) or []:
        if isinstance(b.get("names"), list):  # scoreboard shape
            names += b["names"]
        media = b.get("media") or {}
        if media.get("shortName"):  # schedule shape
            names.append(media["shortName"])
    for b in comp.get("geoBroadcasts", []) or []:
        media = b.get("media") or {}
        if media.get("shortName"):
            names.append(media["shortName"])
    seen, out = set(), []
    for n in names:
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def parse_date(s):
    s = s.replace("Z", "+00:00")
    if len(s) == len("2026-01-01T15:00+00:00"):  # ESPN often omits seconds
        s = s[:16] + ":00" + s[16:]
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def team_name(c):
    t = c.get("team") or {}
    return t.get("shortDisplayName") or t.get("displayName") or "TBD"



def esc(text):
    return (text.replace("\\", "\\\\").replace(";", "\\;")
                .replace(",", "\\,").replace("\n", "\\n"))


def fold(line):
    """Fold lines to 75 octets per RFC 5545."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > (75 if not parts else 74):
            parts.append(cur.decode("utf-8"))
            cur = b""
        cur += b
    parts.append(cur.decode("utf-8"))
    return "\r\n ".join(parts)


def build_vevent(ev, comp_name, stamp):
    comp = (ev.get("competitions") or [{}])[0]
    competitors = comp.get("competitors") or []
    home = next((c for c in competitors if c.get("homeAway") == "home"), None)
    away = next((c for c in competitors if c.get("homeAway") == "away"), None)
    if not home or not away or not ev.get("date"):
        return None

    start = parse_date(ev["date"])
    home_n, away_n = team_name(home), team_name(away)
    is_home = (home.get("team") or {}).get("id") == TEAM_ID or TEAM_NAME in home_n
    opponent = away_n if is_home else home_n

    state = (((comp.get("status") or ev.get("status") or {}).get("type")) or {}).get("state")
    # Title never includes a score, even for finished matches.
    matchup = f"{TEAM_NAME} vs {opponent} (H)" if is_home else f"{opponent} vs {TEAM_NAME} (A)"
    summary = f"⚽ {matchup}"

    tv = tv_channels(comp)
    tv_text = ", ".join(tv) if tv else ("n/a" if state == "post" else "TBD")
    venue = ((comp.get("venue") or ev.get("venue") or {}).get("fullName")) or ""

    desc = [comp_name, f"TV: {tv_text}"]
    if venue:
        desc.append(f"Venue: {venue}")
    if (((comp.get("status") or {}).get("type")) or {}).get("detail") == "TBD":
        desc.append("Kickoff time not yet confirmed")

    lines = [
        "BEGIN:VEVENT",
        f"UID:espn-{ev['id']}@arsenal-ics",
        f"DTSTAMP:{stamp}",
        f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}",
        f"DTEND:{(start + MATCH_LENGTH).strftime('%Y%m%dT%H%M%SZ')}",
        f"SUMMARY:{esc(summary)}",
        f"LOCATION:{esc('📺 ' + tv_text)}",
        f"DESCRIPTION:{esc(chr(10).join(desc))}",
    ]
    if any(k.lower() in opponent.lower() for k in ALERT_OPPONENTS):
        lines += [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{esc(summary + ' in 3 days')}",
            f"TRIGGER:-{ALERT_BEFORE}",
            "END:VALARM",
        ]
    lines.append("END:VEVENT")
    return start, lines


def build_calendar(events):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    built = [v for v in (build_vevent(e, c, stamp) for e, c in events) if v]
    built.sort(key=lambda x: x[0])
    out = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//arsenal-ics//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Arsenal FC",
        "X-WR-CALDESC:Arsenal fixtures with US TV listings (auto-updated)",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]
    for _, lines in built:
        out += lines
    out.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in out) + "\r\n", len(built)


def main():
    if len(sys.argv) > 1:  # local testing: pass JSON files instead of fetching
        events = []
        for path in sys.argv[1:]:
            with open(path) as f:
                events += [(e, "Premier League") for e in json.load(f).get("events", [])]
        ok = 1
    else:
        events, ok = load_events()
    if ok == 0 or not events:
        # Leave the previous calendar in place rather than publishing an empty one.
        sys.exit("error: no fixture data fetched; keeping existing calendar")
    ics, n = build_calendar(events)
    os.makedirs(os.path.dirname(OUTPUT) or ".", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8", newline="") as f:
        f.write(ics)
    print(f"wrote {n} matches to {OUTPUT}")


if __name__ == "__main__":
    main()
