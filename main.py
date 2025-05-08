from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os
import uuid
import re

app = FastAPI()

# Mount the static directory for serving static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# To run this app, use:
# uvicorn main:app --reload

def is_valid_youtube_url(url: str) -> bool:
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    return bool(re.match(youtube_regex, url))

@app.get("/", response_class=HTMLResponse)
def get_home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>YouTube Downloader</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <div class="container">
            <h1>YouTube Downloader</h1>
            <div class="input-group">
                <input type="text" id="url" placeholder="Enter YouTube URL">
                <select id="format">
                    <option value="video">Video with Audio</option>
                    <option value="audio">Audio Only (MP3)</option>
                </select>
                <button onclick="downloadVideo()">Download</button>
            </div>
            <div id="status" class="status"></div>
        </div>
        <script src="/static/script.js"></script>
    </body>
    </html>
    """

@app.get("/download")
def download_video(url: str = Query(..., description="YouTube video URL"), format: str = Query("video", description="Download format: video or audio")):
    try:
        if not is_valid_youtube_url(url):
            raise HTTPException(status_code=400, detail="Invalid YouTube URL format")

        # Create a unique ID for this download
        download_id = str(uuid.uuid4())
        temp_dir = f"temp_{download_id}"
        os.makedirs(temp_dir, exist_ok=True)

        try:
            if format == "audio":
                # Audio download options
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                    'quiet': True,
                    'no_warnings': True,
                }
                file_extension = 'mp3'
                media_type = 'audio/mpeg'
            else:
                # Video download options - using a format that includes both video and audio
                ydl_opts = {
                    'format': 'best[ext=mp4]/best',  # This will get the best quality that includes both video and audio
                    'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                    'quiet': True,
                    'no_warnings': True,
                }
                file_extension = 'mp4'
                media_type = 'video/mp4'

            # Download the video/audio
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'download')
                # Clean the title to make it safe for filenames
                title = re.sub(r'[^\w\-_\. ]', '_', title)
                temp_filename = ydl.prepare_filename(info)
                
                # For audio downloads, the filename will have .mp3 extension
                if format == "audio":
                    temp_filename = temp_filename.rsplit('.', 1)[0] + '.mp3'

            # Return the file
            return FileResponse(
                temp_filename,
                media_type=media_type,
                filename=f"{title}.{file_extension}",
                background=lambda: cleanup_files(temp_dir)
            )

        except Exception as e:
            cleanup_files(temp_dir)
            raise e

    except Exception as e:
        error_message = str(e)
        if "Video unavailable" in error_message:
            raise HTTPException(status_code=404, detail="Video is unavailable or private")
        elif "Sign in to confirm your age" in error_message:
            raise HTTPException(status_code=403, detail="Age-restricted video")
        else:
            raise HTTPException(status_code=500, detail=f"Error downloading video: {error_message}")

def cleanup_files(directory):
    """Clean up temporary files and directory"""
    try:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir(directory)
    except Exception:
        pass  # Ignore cleanup errors 