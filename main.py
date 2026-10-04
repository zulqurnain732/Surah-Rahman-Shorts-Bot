import os
import sys
import json
import random
import subprocess
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

VIDEO_URL = "https://www.youtube.com/watch?v=Fd0Dipj3E84"
TRACKER_FILE = "tracker.json"
COOKIES_FILE = "cookies.txt"

def load_tracker():
    if not os.path.exists(TRACKER_FILE):
        return {"uploaded_count": 0, "used_timestamps": []}
    with open(TRACKER_FILE, "r") as f:
        return json.load(f)

def save_tracker(data):
    with open(TRACKER_FILE, "w") as f:
        json.dump(data, f, indent=2)

def download_source():
    output_template = "source_video.%(ext)s"
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "-o", output_template
    ]
    if os.path.exists(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
        cmd.extend(["--cookies", COOKIES_FILE])
    cmd.append(VIDEO_URL)
    
    subprocess.run(cmd, check=True)
    for f in os.listdir("."):
        if f.startswith("source_video."):
            return f
    raise FileNotFoundError("Video download verify nahi ho saki.")

def get_duration(file_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=True)
    return float(res.stdout.strip())

def make_short(input_file, used_starts):
    total_dur = get_duration(input_file)
    clip_dur = 50  # Shorts ki duration 50 seconds

    max_start = int(total_dur - clip_dur - 5)
    start_time = random.randint(10, max_start)
    
    # Check karein pichle cut se door ho
    attempts = 0
    while any(abs(start_time - u) < 60 for u in used_starts) and attempts < 20:
        start_time = random.randint(10, max_start)
        attempts += 1
        
    out_file = "final_short.mp4"
    print(f"Cutting clip from {start_time}s to 9:16 vertical crop...")

    # Scale and center crop to 9:16 (1080x1920)
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", input_file,
        "-t", str(clip_dur),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "128k",
        out_file
    ]
    subprocess.run(cmd, check=True)
    return out_file, start_time

def get_metadata(part_no):
    titles = [
        f"Most Beautiful Surah Ar-Rahman Tilawat | Part {part_no} #Shorts",
        f"Heart Touching Quran Recitation - Surah Rahman Part {part_no} #Shorts",
        f"Surah Ar Rahman Beautiful Voice | Part {part_no} #Shorts",
        f"Peaceful Quran Status - Surah Rahman Part {part_no} #Shorts"
    ]
    
    title = titles[(part_no - 1) % len(titles)]
    
    description = (
        "Beautiful and heart touching recitation of Surah Ar-Rahman (سورة الرحمن).\n"
        "Listen and share with others for Sadqah-e-Jariyah.\n\n"
        "#SurahRahman #Quran #Tilawat #Shorts #IslamicStatus #QuranRecitation"
    )
    
    tags = [
        "Surah Rahman", "Surah Ar Rahman", "Quran Tilawat", 
        "Heart Touching Quran Recitation", "Quran Shorts", 
        "Islamic Status", "Surah Rahman Full", "Peaceful Quran Status"
    ]
    
    return title, description, tags

def upload_short(file_path, title, description, tags):
    token_str = os.environ.get("YOUTUBE_TOKEN_JSON")
    if not token_str:
        raise ValueError("YOUTUBE_TOKEN_JSON secret missing hai!")

    creds = Credentials.from_authorized_user_info(json.loads(token_str))
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise ValueError("Token expire ho gaya hai.")

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True)
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = req.execute()
    print(f"Successfully Uploaded! Video ID: {resp.get('id')}")

if __name__ == "__main__":
    tracker = load_tracker()
    count = tracker.get("uploaded_count", 0)

    if count >= 4:
        print("Total 4 shorts upload ho chuke hain. Process completed.")
        sys.exit(0)

    print(f"Current upload task: Short #{count + 1} of 4")

    source = download_source()
    short_file, cut_start = make_short(source, tracker.get("used_timestamps", []))
    
    title, desc, tags = get_metadata(count + 1)
    upload_short(short_file, title, desc, tags)

    tracker["uploaded_count"] = count + 1
    tracker["used_timestamps"].append(cut_start)
    save_tracker(tracker)
    print("Tracker updated successfully.")
