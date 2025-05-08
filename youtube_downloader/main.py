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
        <meta name="description" content="Download YouTube videos and audio easily with our free online YouTube downloader. Fast, secure, and no registration required.">
        <meta name="theme-color" content="#ff0000">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <title>YouTube Downloader - Download Videos & Audio</title>
        <link rel="stylesheet" href="/static/style.css">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23ff0000'%3E%3Cpath d='M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z'/%3E%3C/svg%3E">
    </head>
    <body>
        <div class="container">
            <h1>YouTube Downloader</h1>
            <div class="input-group">
                <input type="text" id="url" placeholder="Paste YouTube URL here" autocomplete="off" spellcheck="false">
                <div class="select-wrapper">
                    <select id="format">
                        <option value="video">Video with Audio</option>
                        <option value="audio">Audio Only (MP3)</option>
                    </select>
                </div>
                <button onclick="downloadVideo()">Download Now</button>
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

        # Configure yt-dlp options based on format
        if format == "audio":
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': f'temp_{uuid.uuid4()}.%(ext)s',
                'quiet': True,
                'no_warnings': True,
            }
            file_extension = 'mp3'
            media_type = 'audio/mpeg'
        else:
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',  # Best quality with both video and audio
                'merge_output_format': 'mp4',
                'outtmpl': f'temp_{uuid.uuid4()}.%(ext)s',
                'quiet': True,
                'no_warnings': True,
            }
            file_extension = 'mp4'
            media_type = 'video/mp4'

        # Download the video/audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'download')
            temp_filename = ydl.prepare_filename(info)
            
            # For audio downloads, the filename will have .mp3 extension
            if format == "audio":
                temp_filename = temp_filename.rsplit('.', 1)[0] + '.mp3'

        # Return the file
        return FileResponse(
            temp_filename,
            media_type=media_type,
            filename=f"{title}.{file_extension}",
            background=lambda: os.remove(temp_filename)
        )
    except Exception as e:
        error_message = str(e)
        if "Video unavailable" in error_message:
            raise HTTPException(status_code=404, detail="Video is unavailable or private")
        elif "Sign in to confirm your age" in error_message:
            raise HTTPException(status_code=403, detail="Age-restricted video")
        else:
            raise HTTPException(status_code=500, detail=f"Error downloading video: {error_message}") 