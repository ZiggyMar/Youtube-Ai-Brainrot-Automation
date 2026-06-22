"""
run_pipeline.py  —  the set-and-forget server daemon.

Every cycle (default once/day) it:
  1. fetches the newest gameplay footage from the source channel (soft-fail),
  2. generates GEN_PER_RUN videos (director -> voicebox -> video_factory) as subprocesses
     (subprocesses free RAM between stages - important on a memory-tight CPU server),
  3. archives each video's script + transcripts (mp4 stays for the uploader),
  4. schedules ready videos onto the weekly EST blueprint (max 1 published/day),
  5. prunes old mp4s, sends a Discord heartbeat, then sleeps until the next cycle.

Designed to be run by systemd with Restart=always so it survives crashes and reboots forever.
Run stages as subprocesses keeps a single hung stage from poisoning the long-lived daemon.
"""
import os
import sys
import time
import subprocess
import datetime

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
sys.path.insert(0, CORE_DIR)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

import notifier   # noqa: E402
import archiver   # noqa: E402

GEN_PER_RUN = int(os.environ.get("GEN_PER_RUN", "1"))
CYCLE_HOURS = float(os.environ.get("CYCLE_HOURS", "24"))
# Fixed wall-clock time (server local) to run the daily cycle. Default 22:00 (10 PM) so the
# render finishes overnight and the fresh video is queued well before the next day's post slot.
RUN_AT_HOUR = int(os.environ.get("RUN_AT_HOUR", "22"))
RUN_AT_MINUTE = int(os.environ.get("RUN_AT_MINUTE", "0"))
PY = sys.executable

# Force UTF-8 so emoji prints never crash under non-UTF8 locales (Windows cp1252).
RUN_ENV = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")


def stage(script, label, args=None):
    """Run a pipeline stage as a subprocess. Returns True on success."""
    print(f"\n{'='*50}\n=== {label} ===\n{'='*50}")
    cmd = [PY, os.path.join(CORE_DIR, script)] + (args or [])
    try:
        subprocess.run(cmd, check=True, cwd=PROJECT_ROOT, env=RUN_ENV)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {script} failed: {e}")
        notifier.error(f"Stage failed: {label}", f"{script} exited {e.returncode}")
        return False


def fetch_footage():
    try:
        stage("footage_fetcher.py", "STAGE 0: FOOTAGE FETCH")
    except Exception as e:
        print(f"⚠️ Footage fetch skipped: {e}")


def generate_one():
    if not stage("director.py", "STAGE 1: WRITE SCRIPT"):
        return False
    if not stage("voicebox.py", "STAGE 2: GENERATE AUDIO"):
        return False
    if not stage("video_factory.py", "STAGE 3: RENDER VIDEO"):
        return False
    try:
        archiver.archive_current_scripts()   # snapshot script+transcripts before next overwrite
    except Exception as e:
        print(f"⚠️ Archive failed: {e}")
    return True


def schedule_ready():
    """Schedule any ready videos onto the blueprint (uploader handles 1/day + brand channel)."""
    try:
        import youtube_uploader
        up = youtube_uploader.YouTubeUploader()
        if not up.youtube:
            notifier.warn("Uploader not authenticated", "No valid token.pickle - videos are rendered and waiting.")
            return
        up.process_ready()
    except Exception as e:
        notifier.error("Scheduling failed", str(e)[:500])


def seconds_until_next_run():
    """Seconds from now until the next RUN_AT_HOUR:RUN_AT_MINUTE (server local time)."""
    now = datetime.datetime.now()
    target = now.replace(hour=RUN_AT_HOUR, minute=RUN_AT_MINUTE, second=0, microsecond=0)
    if target <= now:
        target += datetime.timedelta(days=1)
    return (target - now).total_seconds()


def run_cycle():
    start = datetime.datetime.now()
    print(f"\n🎬 CYCLE START {start.isoformat(timespec='seconds')}")
    fetch_footage()
    made = 0
    for i in range(GEN_PER_RUN):
        print(f"\n--- Generating video {i+1}/{GEN_PER_RUN} ---")
        if generate_one():
            made += 1
    schedule_ready()
    try:
        archiver.prune_posted(days=7)
    except Exception:
        pass
    next_run = (datetime.datetime.now()
                + datetime.timedelta(seconds=seconds_until_next_run()))
    notifier.success(
        "Daily cycle complete",
        f"Generated {made}/{GEN_PER_RUN} video(s) and scheduled the queue. "
        f"Next cycle at {next_run:%Y-%m-%d %H:%M} (server time).",
    )


def main():
    notifier.info(
        "Brainrot daemon started",
        f"Runs daily at {RUN_AT_HOUR:02d}:{RUN_AT_MINUTE:02d} (server time), {GEN_PER_RUN} video(s)/cycle.",
    )
    while True:
        wait_s = seconds_until_next_run()
        print(f"😴 Sleeping {wait_s/3600:.1f}h until next run at "
              f"{RUN_AT_HOUR:02d}:{RUN_AT_MINUTE:02d} server time...")
        time.sleep(wait_s)
        try:
            run_cycle()
        except Exception as e:
            print(f"❌ Cycle error: {e}")
            notifier.error("Cycle crashed", str(e)[:500])
        # Nudge past the target minute so we don't immediately re-trigger the same slot.
        time.sleep(90)


if __name__ == "__main__":
    if "--once" in sys.argv:
        run_cycle()
    else:
        main()
