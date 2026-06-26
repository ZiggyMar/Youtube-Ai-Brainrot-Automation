"""
youtube_uploader.py
Uploads rendered Shorts to the (brand) channel and SCHEDULES them on the proven weekly
EST blueprint - max 1 published per day. Videos are uploaded as `private` with a future
`publishAt`, so YouTube publishes them on schedule even if the server is offline at that moment.

Auth: OAuth (token.pickle). Authenticate ONCE locally selecting the BRAND channel, then copy
token.pickle to the server (the server is headless and cannot open a browser).

CLI:
  --auth-only   authenticate and exit (use locally to mint token.pickle)
  --watch       run forever, scheduling any ready videos as they appear
  (no args)     process the ready folder once and exit
"""
import os
import sys
import json
import time
import random
import pickle
import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
sys.path.insert(0, CORE_DIR)
import notifier  # noqa: E402

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
READY_DIR = os.path.join(OUTPUT_DIR, "ready_to_post")
POSTED_DIR = os.path.join(OUTPUT_DIR, "posted")
CLIENT_SECRETS_FILE = os.path.join(PROJECT_ROOT, "client_secrets.json")
TOKEN_FILE = os.path.join(PROJECT_ROOT, "token.pickle")
UPLOAD_LOG_FILE = os.path.join(DATA_DIR, "upload_log.json")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",  # lets us confirm WHICH channel a token is for
]
TZ = ZoneInfo(os.environ.get("TIMEZONE", "America/Toronto"))

# === Multi-channel registry ===========================================================
# Each channel = its OWN OAuth token + upload log + in-video subscribe-CTA overlay.
# A channel is only ACTIVE once its token file exists (minted locally via --auth-only),
# so the pipeline behaves exactly as before until FactZap's token is added, then it
# auto-scales to one freshly-generated video per channel per day.
CHANNELS = {
    "mmstorybook": {
        "name": "MM Storybook",
        "token_file": os.path.join(PROJECT_ROOT, "token.pickle"),
        "log_file": os.path.join(DATA_DIR, "upload_log.json"),
        "cta": "subscribe_cta",            # assets/overlays/<cta>.mp4
        # 1 post/day at 6:00 AM — owner's A/B test (morning drop vs the old 6 PM evening
        # slot); a 6 AM release gives the Short a full active day to be tested/accumulate.
        # (Set "blueprint" to revert to the proven varying-weekday evening times.)
        "schedule": [(6, 0)],
    },
    "factzap": {
        "name": "FactZap",
        "token_file": os.path.join(PROJECT_ROOT, "token_factzap.pickle"),
        "log_file": os.path.join(DATA_DIR, "upload_log_factzap.json"),
        "cta": "subscribe_cta_factzap",
        # 2 posts/day to force volume on the throttled OG channel: late morning + evening.
        "schedule": [(11, 0), (19, 0)],
    },
    "quizzap": {
        "name": "QuizZap",
        "token_file": os.path.join(PROJECT_ROOT, "token_quizzap.pickle"),
        "log_file": os.path.join(DATA_DIR, "upload_log_quizzap.json"),
        "cta": "subscribe_cta_quizzap",
        # Brand-new clean channel — the control in the 3-channel experiment. 1 post/day at 6 AM.
        "schedule": [(6, 0)],
        # SLOW IGNITION: held out of the daemon's auto cycle for the first few days so the
        # fresh channel isn't day-one auto-blasted (spam signal). Flip to True to go daily.
        "auto_post": False,
    },
}
DEFAULT_CHANNEL = "mmstorybook"


def channel_posts_per_day(cfg):
    sched = cfg.get("schedule", "blueprint")
    return 1 if sched == "blueprint" else len(sched)


def enabled_channels():
    """(key, cfg) the DAEMON auto-posts to: token exists AND auto_post not disabled.
    A channel can be registered + tokened but held out of the auto cycle (auto_post=False)
    e.g. a brand-new channel doing a slow, hand-controlled ignition. Manual posts via
    YouTubeUploader(cfg) ignore this flag."""
    return [(k, c) for k, c in CHANNELS.items()
            if os.path.exists(c["token_file"]) and c.get("auto_post", True)]

# === Proven weekly EST blueprint: (hour, minute) local upload-target per weekday ===
# Monday=0 ... Sunday=6. One published video per day at these high-traffic windows.
BLUEPRINT = {
    0: (18, 0),   # Monday    6:00 PM
    1: (19, 0),   # Tuesday   7:00 PM
    2: (17, 0),   # Wednesday 5:00 PM
    3: (20, 0),   # Thursday  8:00 PM
    4: (16, 0),   # Friday    4:00 PM (best day for Shorts)
    5: (11, 0),   # Saturday 11:00 AM
    6: (14, 0),   # Sunday    2:00 PM
}

# === Proven metadata (from FactZapTV's top videos) ===
DESCRIPTION_TEMPLATE = """GOODLUCK!

SUBSCRIBE TO HELP US REACH 100K!

-- Tags --

spongebob,spongebob squarepants,spongebob episodes,spongebob music,plankton spongebob,squidward spongebob,patrick spongebob,spongebob nick,spongebob quiz,spongebob video games,spongebob shorts,spongebob quizzes,spongebob megaquiz,spongebob game show,spongebob game,spongebob kids,spongebob meme,brainrot,brain teaser,mind games,dont say the same thing,quiz,trivia,challenge,shorts"""

TAGS_LIST = [
    "spongebob", "spongebob squarepants", "spongebob episodes", "spongebob music",
    "plankton spongebob", "squidward spongebob", "patrick spongebob", "spongebob nick",
    "spongebob quiz", "spongebob shorts", "spongebob quizzes", "spongebob megaquiz",
    "spongebob game show", "spongebob game", "spongebob kids", "spongebob meme",
    "brainrot", "brain teaser", "mind games", "dont say the same thing",
    "quiz", "trivia", "challenge", "shorts",
]


def cap_tags(tags, limit=480):
    """YouTube tags total must stay under ~500 chars (commas count)."""
    out, total = [], 0
    for t in tags:
        add = len(t) + (1 if out else 0)
        if total + add > limit:
            break
        out.append(t)
        total += add
    return out


class YouTubeUploader:
    def __init__(self, channel=None):
        # channel: a CHANNELS[*] cfg dict. Defaults to the primary channel for backward compat.
        cfg = channel or CHANNELS[DEFAULT_CHANNEL]
        self.name = cfg["name"]
        self.token_file = cfg["token_file"]
        self.log_file = cfg["log_file"]
        self.schedule = cfg.get("schedule", "blueprint")  # "blueprint" or [(h,m),...]
        self.youtube = self.authenticate()
        self.log = self.load_log()

    def authenticate(self):
        TOKEN_FILE = self.token_file
        creds = None
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, "rb") as f:
                    creds = pickle.load(f)
            except Exception:
                creds = None

        if creds and creds.valid:
            return build("youtube", "v3", credentials=creds)

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(TOKEN_FILE, "wb") as f:
                    pickle.dump(creds, f)
                return build("youtube", "v3", credentials=creds)
            except Exception as e:
                print(f"⚠️ Token refresh failed: {e}")

        # Need fresh browser auth. Only works where a browser is available (i.e. locally).
        if not os.path.exists(CLIENT_SECRETS_FILE):
            msg = "Missing client_secrets.json (download OAuth client from Google Cloud)."
            print(f"❌ {msg}")
            notifier.error("YouTube auth failed", msg)
            return None
        if not sys.stdout.isatty() and os.environ.get("DISPLAY") is None and os.name != "nt":
            msg = ("No valid token.pickle and no browser available (headless server). "
                   "Run `python core/youtube_uploader.py --auth-only` LOCALLY, select the BRAND "
                   "channel, then copy token.pickle to the server.")
            print(f"❌ {msg}")
            notifier.error("YouTube auth needs a browser", msg)
            return None
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        print(f"\n🔐 A browser will open. Sign in and SELECT THE CHANNEL FOR: {self.name}.\n")
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
        return build("youtube", "v3", credentials=creds)

    def load_log(self):
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"last_scheduled_time": None, "uploaded": []}

    def save_log(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(self.log, f, indent=2)

    def _slots_for(self, day):
        """Sorted list of (hour, minute) target times for this channel on `day`."""
        if self.schedule == "blueprint":
            return [BLUEPRINT[day.weekday()]]
        return sorted(self.schedule)

    def _taken_slots(self):
        """Set of (date_iso, slot_index) already filled — each logged publish time is matched
        to its NEAREST slot for that day, so jitter (±5min) doesn't confuse the mapping."""
        taken = set()
        for v in self.log.get("uploaded", []):
            t = v.get("publish_at")
            if not t:
                continue
            try:
                dt = datetime.datetime.fromisoformat(t)
            except ValueError:
                continue
            slots = self._slots_for(dt.date())
            mins = dt.hour * 60 + dt.minute
            idx = min(range(len(slots)), key=lambda i: abs(mins - (slots[i][0] * 60 + slots[i][1])))
            taken.add((dt.date().isoformat(), idx))
        return taken

    def next_slot(self):
        """Next free posting slot in TZ, strictly future. Supports N posts/day: each day exposes
        len(slots) targets; a specific slot is skipped once a video is already scheduled into it."""
        now = datetime.datetime.now(TZ)
        taken = self._taken_slots()

        day = now.date()
        for _ in range(60):  # look ahead up to 60 days
            slots = self._slots_for(day)
            for idx, (h, m) in enumerate(slots):
                slot = datetime.datetime(day.year, day.month, day.day, h, m, tzinfo=TZ)
                if slot <= now + datetime.timedelta(minutes=10):
                    continue            # this time already passed
                if (day.isoformat(), idx) in taken:
                    continue            # this exact slot already filled
                return slot
            day += datetime.timedelta(days=1)
        return now + datetime.timedelta(days=1)

    def upload(self, path):
        if not self.youtube:
            return "AUTH_ERROR"
        filename = os.path.basename(path)
        title = os.path.splitext(filename)[0][:95]  # YouTube title cap 100
        slot_local = self.next_slot()
        # Human-like jitter (±~5 min) so publishes aren't robotically on the exact minute.
        slot_local += datetime.timedelta(minutes=random.randint(-5, 5), seconds=random.randint(0, 59))
        if slot_local <= datetime.datetime.now(TZ) + datetime.timedelta(minutes=5):
            slot_local += datetime.timedelta(minutes=10)
        publish_at_utc = slot_local.astimezone(datetime.timezone.utc)

        body = {
            "snippet": {
                "title": title,
                "description": DESCRIPTION_TEMPLATE,
                "tags": cap_tags(TAGS_LIST),
                "categoryId": "24",  # Entertainment
            },
            "status": {
                "privacyStatus": "private",
                "publishAt": publish_at_utc.isoformat().replace("+00:00", "Z"),
                "selfDeclaredMadeForKids": False,
            },
        }
        print(f"🚀 Uploading: {filename}")
        print(f"   📅 Scheduled: {slot_local.strftime('%a %Y-%m-%d %I:%M %p %Z')}")
        try:
            media = MediaFileUpload(path, chunksize=-1, resumable=True, mimetype="video/mp4")
            req = self.youtube.videos().insert(part="snippet,status", body=body, media_body=media)
            resp = None
            while resp is None:
                status, resp = req.next_chunk()
                if status:
                    print(f"   ...{int(status.progress()*100)}%")
            vid = resp.get("id")
            print(f"✅ Scheduled! https://youtu.be/{vid}")
            self.log["last_scheduled_time"] = slot_local.isoformat()
            self.log["uploaded"].append({
                "video_id": vid, "filename": filename, "title": title,
                "publish_at": slot_local.isoformat(),
            })
            self.save_log()
            notifier.success(
                f"Video scheduled — {self.name}",
                f"**{title}**\nPublishes: {slot_local.strftime('%a %b %d, %I:%M %p %Z')}\nhttps://youtu.be/{vid}",
            )
            return vid
        except HttpError as e:
            reason = (e.content or b"").decode("utf-8", "ignore")
            if e.resp.status in (403, 429) and ("quota" in reason.lower() or "uploadLimit" in reason):
                print("🛑 Quota / upload limit reached.")
                notifier.warn("YouTube quota reached", "Will retry on the next cycle.")
                return "QUOTA"
            print(f"❌ HTTP error: {e}")
            notifier.error("Upload failed (HTTP)", str(e)[:500])
            return "ERROR"
        except Exception as e:
            print(f"❌ Upload error: {e}")
            notifier.error("Upload failed", str(e)[:500])
            return "ERROR"

    def process_ready(self):
        if not os.path.isdir(READY_DIR):
            return
        vids = sorted(
            [f for f in os.listdir(READY_DIR) if f.endswith(".mp4")],
            key=lambda x: os.path.getmtime(os.path.join(READY_DIR, x)),
        )
        if not vids:
            print("ℹ️ No videos ready to post.")
            return
        os.makedirs(POSTED_DIR, exist_ok=True)
        for v in vids:
            path = os.path.join(READY_DIR, v)
            result = self.upload(path)
            if result == "QUOTA":
                return "STOP"
            if result in ("ERROR", "AUTH_ERROR"):
                print(f"⚠️ Skipping {v} (will retry next cycle).")
                continue
            # Success: move out of ready so it isn't re-uploaded; archiver handles the rest.
            try:
                import shutil
                shutil.move(path, os.path.join(POSTED_DIR, v))
            except Exception as e:
                print(f"⚠️ Could not move {v}: {e}")
            time.sleep(3)

    def watch(self, interval=300):
        print("👀 Uploader watching ready_to_post/ ...")
        while True:
            try:
                if self.process_ready() == "STOP":
                    print("🛑 Pausing 1h after quota.")
                    time.sleep(3600)
                    continue
            except Exception as e:
                notifier.error("Uploader loop error", str(e)[:500])
            time.sleep(interval)


def _channel_from_argv():
    """--channel <key> selects which channel registry entry to use (default primary)."""
    if "--channel" in sys.argv:
        i = sys.argv.index("--channel")
        if i + 1 < len(sys.argv):
            key = sys.argv[i + 1]
            if key in CHANNELS:
                return CHANNELS[key]
            print(f"❌ Unknown channel '{key}'. Valid: {', '.join(CHANNELS)}")
            sys.exit(1)
    return CHANNELS[DEFAULT_CHANNEL]


def main():
    cfg = _channel_from_argv()
    if "--auth-only" in sys.argv:
        # Force a FRESH browser flow so the account/brand chooser reappears every time.
        try:
            if os.path.exists(cfg["token_file"]):
                os.remove(cfg["token_file"])
        except Exception:
            pass
        up = YouTubeUploader(cfg)
        if up.youtube:
            print(f"✅ Authentication successful — {os.path.basename(up.token_file)} saved for {up.name}.")
            # Confirm exactly WHICH YouTube channel this token controls.
            try:
                r = up.youtube.channels().list(part="snippet,statistics", mine=True).execute()
                items = r.get("items", [])
                if not items:
                    print("   ⚠️ No channel returned for this account.")
                for it in items:
                    title = it["snippet"]["title"]
                    subs = it.get("statistics", {}).get("subscriberCount", "?")
                    print("   " + "=" * 50)
                    print(f"   📺 THIS TOKEN CONTROLS:  {title}")
                    print(f"      Subscribers: {subs}   |   id: {it['id']}")
                    print("   " + "=" * 50)
                    print("   >>> If that's NOT FactZap (35,900 subs), re-run and pick a different brand account.")
            except Exception as e:
                print(f"   (couldn't read channel identity: {str(e)[:160]})")
        else:
            print("❌ Authentication failed.")
        return
    up = YouTubeUploader(cfg)
    if not up.youtube:
        return
    if "--watch" in sys.argv:
        up.watch()
    else:
        up.process_ready()


if __name__ == "__main__":
    main()
