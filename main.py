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
            # Common options for both video and audio
            common_opts = {
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'ignoreerrors': True,
                'no_color': True,
                'geo_bypass': True,
                'geo_verification_proxy': None,
                'socket_timeout': 30,
                'retries': 10,
                'extractor_args': {
                    'youtube': {
                        'skip': ['dash', 'hls'],
                        'player_client': ['android', 'web'],
                        'player_skip': ['js', 'configs', 'webpage'],
                    }
                },
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            }

            if format == "audio":
                # Audio download options with high quality
                ydl_opts = {
                    **common_opts,
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '320',  # Highest quality MP3
                    }],
                    'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                }
                file_extension = 'mp3'
                media_type = 'audio/mpeg'
            else:
                # Video download options with highest quality
                ydl_opts = {
                    **common_opts,
                    'format': 'bestvideo[height>=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height>=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'merge_output_format': 'mp4',
                    'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                }
                file_extension = 'mp4'
                media_type = 'video/mp4'

            # Download the video/audio
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    # First try to get video info without downloading
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        raise HTTPException(status_code=404, detail="Could not extract video information")
                    
                    # Now download the video
                    info = ydl.extract_info(url, download=True)
                    if not info:
                        raise HTTPException(status_code=404, detail="Could not download video")
                    
                    # Get the title and clean it
                    title = info.get('title', 'download')
                    if not title:
                        title = 'download'
                    title = re.sub(r'[^\w\-_\. ]', '_', title)
                    
                    # Get the filename
                    temp_filename = ydl.prepare_filename(info)
                    if not temp_filename:
                        raise HTTPException(status_code=500, detail="Could not prepare filename")
                    
                    # For audio downloads, the filename will have .mp3 extension
                    if format == "audio":
                        temp_filename = temp_filename.rsplit('.', 1)[0] + '.mp3'
                    
                    # Check if the file exists
                    if not os.path.exists(temp_filename):
                        raise HTTPException(status_code=500, detail="Downloaded file not found")

                    # Return the file
                    return FileResponse(
                        temp_filename,
                        media_type=media_type,
                        filename=f"{title}.{file_extension}",
                        background=lambda: cleanup_files(temp_dir)
                    )
                except yt_dlp.utils.DownloadError as e:
                    raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")

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