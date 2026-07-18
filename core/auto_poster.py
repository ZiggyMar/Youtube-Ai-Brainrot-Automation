import os
import json
import datetime
import time
import random
import schedule
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Configuration
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
CLIENT_SECRETS_FILE = os.path.join(PROJECT_ROOT, "client_secrets.json")
TOKEN_FILE = os.path.join(PROJECT_ROOT, "token.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
READY_DIR = os.path.join(OUTPUT_DIR, "Ready To Post")
POSTED_LOG_FILE = os.path.join(PROJECT_ROOT, "data", "posted_log.json")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

class YouTubeUploader:
    """
    Handles authentication and video uploads to the YouTube API.
    Provides methods to refresh OAuth tokens and insert videos.
    """
    def __init__(self):
        self.youtube = None

    def authenticate(self):
        """
        Authenticates with YouTube API via OAuth 2.0.
        Loads existing token or initiates local server flow if missing.
        """
        creds = None
        if os.path.exists(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            except:
                print("⚠️ Invalid token, re-authenticating...")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except:
                    creds = None
            
            if not creds:
                if not os.path.exists(CLIENT_SECRETS_FILE):
                    print(f"❌ Missing {CLIENT_SECRETS_FILE}")
                    return False
                
                flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRETS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())

        try:
            self.youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
            return True
        except Exception as e:
            print(f"❌ YouTube Build Error: {e}")
            return False

    def upload_video(self, file_path, title, description, tags, category_id="24"):
        if not self.youtube:
            if not self.authenticate(): return False

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category_id
            },
            "status": {
                "privacyStatus": "public", 
                "selfDeclaredMadeForKids": False
            }
        }

        try:
            print(f"🚀 Uploading {title}...")
            # MediaFileUpload requires googleapiclient.http
            from googleapiclient.http import MediaFileUpload
            
            media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
            request = self.youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"   Uploading... {int(status.progress() * 100)}%")
            
            print(f"✅ Upload Complete! Video ID: {response.get('id')}")
            return response.get('id')
        except Exception as e:
            print(f"❌ Upload Failed: {e}")
            return None

class Scheduler:
    """
    Manages the scheduling and execution of automated video uploads.
    Polls the ready directory and triggers YouTube uploads based on time slots.
    """
    def __init__(self):
        self.uploader = YouTubeUploader()
        self.posted_log = self.load_log()
        
        # Global Best Times (Simplified for automation)
        # We will pick a few slots per day to check for posting
        self.schedule_slots = {
            "Monday": ["07:00", "12:00", "20:00"],
            "Tuesday": ["07:00", "12:00", "17:00", "21:00"],
            "Wednesday": ["12:00", "15:00", "18:00"],
            "Thursday": ["19:00", "20:00", "22:00"],
            "Friday": ["07:00", "12:00", "17:00", "21:00"],
            "Saturday": ["09:00", "15:00", "22:00"],
            "Sunday": ["10:00", "16:00", "21:00"]
        }

    def load_log(self):
        if os.path.exists(POSTED_LOG_FILE):
            try:
                with open(POSTED_LOG_FILE, "r") as f:
                    return json.load(f)
            except: pass
        return {"history": []}

    def save_log(self):
        with open(POSTED_LOG_FILE, "w") as f:
            json.dump(self.posted_log, f, indent=2)

    def get_next_video(self):
        if not os.path.exists(READY_DIR): return None
        files = [f for f in os.listdir(READY_DIR) if f.endswith(".mp4")]
        if not files: return None
        # Pick oldest first? Or random? Let's do random to mix it up, or oldest to keep order.
        # Oldest makes sense for "series".
        files.sort(key=lambda x: os.path.getmtime(os.path.join(READY_DIR, x)))
        return os.path.join(READY_DIR, files[0])

    def post_job(self):
        print("⏰ Checking schedule for posting...")
        
        # Check daily limit (e.g., max 5 per day)
        today_str = datetime.date.today().isoformat()
        today_posts = [p for p in self.posted_log["history"] if p["date"] == today_str]
        if len(today_posts) >= 5:
            print("⚠️ Daily limit reached (5 videos). Skipping.")
            return

        video_path = self.get_next_video()
        if not video_path:
            print("ℹ️ No videos ready to post.")
            return

        filename = os.path.basename(video_path)
        title = os.path.splitext(filename)[0]
        
        # Clean title for upload
        # Remove file extension and maybe some underscores if any
        # But user said "name of mp4 is already the title"
        
        # Add hashtags
        tags = ["SpongeBob", "Shorts", "GenAI", "Quiz"]
        description = f"{title}\n\n#Spongebob #Shorts #GenAI #Quiz #Comedy"
        
        video_id = self.uploader.upload_video(video_path, title, description, tags)
        
        if video_id:
            # Move to "Posted" folder or delete?
            # User said "log the days".
            # Let's move to a "Posted" folder to avoid re-posting
            posted_dir = os.path.join(OUTPUT_DIR, "Posted")
            os.makedirs(posted_dir, exist_ok=True)
            try:
                os.rename(video_path, os.path.join(posted_dir, filename))
            except: pass
            
            self.posted_log["history"].append({
                "date": today_str,
                "time": datetime.datetime.now().isoformat(),
                "video": filename,
                "video_id": video_id
            })
            self.save_log()

    def setup_schedule(self):
        print("📅 Setting up Global Best Times Schedule...")
        
        # We can't easily map "Monday" to schedule library without a loop
        # schedule.every().monday.at("07:00").do(...)
        
        days_map = {
            "Monday": schedule.every().monday,
            "Tuesday": schedule.every().tuesday,
            "Wednesday": schedule.every().wednesday,
            "Thursday": schedule.every().thursday,
            "Friday": schedule.every().friday,
            "Saturday": schedule.every().saturday,
            "Sunday": schedule.every().sunday
        }
        
        for day_name, times in self.schedule_slots.items():
            for t in times:
                days_map[day_name].at(t).do(self.post_job)
                print(f"   -> Scheduled {day_name} at {t}")
        
        print("✅ Schedule Active.")
