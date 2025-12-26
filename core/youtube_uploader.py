import os
import json
import datetime
import pickle
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# Configuration
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')
READY_TO_POST_DIR = os.path.join(OUTPUT_DIR, "ready_to_post")
UPLOAD_LOG_FILE = os.path.join(DATA_DIR, "upload_log.json")
CLIENT_SECRETS_FILE = os.path.join(PROJECT_ROOT, "client_secrets.json")
TOKEN_PICKLE_FILE = os.path.join(PROJECT_ROOT, "token.pickle")

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# YouTube API Scopes
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Global Best Times (EST)
# Monday: 7 AM, 12 PM, 8 PM, 9 PM
# Tuesday: 7 AM, 12 PM, 5 PM, 6 PM, 7 PM, 9 PM, 10 PM, 11 PM
# Wednesday: 12 PM, 3 PM, 4 PM, 5 PM, 6 PM
# Thursday: 7 PM, 8 PM, 9 PM, 10 PM, 11 PM
# Friday: 7 AM, 8 AM, 9 AM, 11 AM, 12 PM, 1 PM, 4 PM, 5 PM, 6 PM, 9 PM, 10 PM, 11 PM
# Saturday: 9 AM, 10 AM, 3 PM, 4 PM, 5 PM, 6 PM, 10 PM, 11 PM, 12 AM
# Sunday: 10 AM, 11 AM, 3 PM, 4 PM, 5 PM, 9 PM

BEST_TIMES = {
    0: [7, 12, 20, 21],          # Monday
    1: [7, 12, 17, 18, 19, 21, 22, 23], # Tuesday
    2: [12, 15, 16, 17, 18],     # Wednesday
    3: [19, 20, 21, 22, 23],     # Thursday
    4: [7, 8, 9, 11, 12, 13, 16, 17, 18, 21, 22, 23], # Friday
    5: [9, 10, 15, 16, 17, 18, 22, 23, 0], # Saturday (0 is midnight)
    6: [10, 11, 15, 16, 17, 21]  # Sunday
}

class YouTubeUploader:
    def __init__(self):
        self.youtube = self.get_authenticated_service()
        self.upload_log = self.load_upload_log()

    def get_authenticated_service(self):
        credentials = None
        if os.path.exists(TOKEN_PICKLE_FILE):
            with open(TOKEN_PICKLE_FILE, 'rb') as token:
                credentials = pickle.load(token)
        
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                if not os.path.exists(CLIENT_SECRETS_FILE):
                    print(f"❌ Error: {CLIENT_SECRETS_FILE} not found. Please follow the instructions in README.md to set up YouTube API.")
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
                credentials = flow.run_local_server(port=0)
            
            with open(TOKEN_PICKLE_FILE, 'wb') as token:
                pickle.dump(credentials, token)
        
        return build("youtube", "v3", credentials=credentials)

    def load_upload_log(self):
        if os.path.exists(UPLOAD_LOG_FILE):
            try:
                with open(UPLOAD_LOG_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"last_scheduled_time": None, "uploaded_videos": []}

    def save_upload_log(self):
        with open(UPLOAD_LOG_FILE, 'w') as f:
            json.dump(self.upload_log, f, indent=2)

    def get_next_scheduled_time(self):
        last_time_str = self.upload_log.get("last_scheduled_time")
        
        if last_time_str:
            last_time = datetime.datetime.fromisoformat(last_time_str)
            # Start searching from the day AFTER the last scheduled video
            start_search = (last_time + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Start from today
            start_search = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Find the next available day and its first valid slot
        current_day = start_search
        for _ in range(60): # Search up to 60 days ahead
            day_of_week = current_day.weekday()
            slots = sorted(BEST_TIMES.get(day_of_week, []))
            
            if slots:
                for hour in slots:
                    # Handle midnight (0) as 24:00 of that day or 00:00 of the next?
                    # The user's list says "12 AM (Midnight)" for Saturday. 
                    # In my BEST_TIMES, Saturday has 0.
                    # Let's treat 0 as 00:00 of that day.
                    scheduled_time = current_day.replace(hour=hour, minute=0, second=0, microsecond=0)
                    
                    # Ensure the slot is in the future
                    if scheduled_time > datetime.datetime.now():
                        return scheduled_time
            
            # Move to next day
            current_day += datetime.timedelta(days=1)
            
        # Extreme fallback
        return datetime.datetime.now() + datetime.timedelta(days=1)

    def upload_video(self, video_path, scheduled_time):
        if not self.youtube:
            return False

        filename = os.path.basename(video_path)
        title = os.path.splitext(filename)[0]
        
        # Add hashtags if not already present
        hashtags = " #Spongebob #shorts #brainrot"
        if "#" not in title:
            title += hashtags
        
        print(f"🚀 Uploading: {filename}")
        print(f"📅 Scheduled for: {scheduled_time.isoformat()}")

        body = {
            "snippet": {
                "title": title,
                "description": title, # Default description
                "categoryId": "24" # Entertainment
            },
            "status": {
                "privacyStatus": "private", # Must be private to schedule
                "publishAt": scheduled_time.isoformat() + "Z", # YouTube expects ISO 8601 with Z
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        
        try:
            request = self.youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"   - Uploaded {int(status.progress() * 100)}%")
            
            print(f"✅ Successfully uploaded and scheduled: {response['id']}")
            
            # Update log
            self.upload_log["last_scheduled_time"] = scheduled_time.isoformat()
            self.upload_log["uploaded_videos"].append({
                "video_id": response["id"],
                "filename": filename,
                "scheduled_time": scheduled_time.isoformat()
            })
            self.save_upload_log()
            
            # Move to a "posted" folder or just delete? 
            # User said "Ready to post folder will hold it like a catalog", 
            # so maybe we should move it to "posted" once done.
            posted_dir = os.path.join(OUTPUT_DIR, "posted")
            os.makedirs(posted_dir, exist_ok=True)
            import shutil
            shutil.move(video_path, os.path.join(posted_dir, filename))
            
            return True
        except Exception as e:
            print(f"❌ Error uploading {filename}: {e}")
            return False

    def process_ready_folder(self):
        if not os.path.exists(READY_TO_POST_DIR):
            print(f"ℹ️ {READY_TO_POST_DIR} does not exist.")
            return

        videos = [f for f in os.listdir(READY_TO_POST_DIR) if f.endswith(".mp4")]
        if not videos:
            print("ℹ️ No videos ready to post.")
            return

        print(f"📂 Found {len(videos)} videos in ready_to_post.")
        
        # YouTube limit: 30 videos per day. 
        # We'll just process what's there, but keep in mind the limit.
        for video in videos:
            video_path = os.path.join(READY_TO_POST_DIR, video)
            next_time = self.get_next_scheduled_time()
            if self.upload_video(video_path, next_time):
                print(f"✅ Processed {video}")
            else:
                print(f"⚠️ Failed to process {video}. Stopping for now.")
                break

def main():
    uploader = YouTubeUploader()
    if uploader.youtube:
        uploader.process_ready_folder()

if __name__ == "__main__":
    main()
