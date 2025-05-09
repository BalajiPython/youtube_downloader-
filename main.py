from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import os
import uuid
import re
import logging
import tempfile
from typing import Optional
import shutil
from pathlib import Path
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Mount the static directory for serving static files
static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")
else:
    logger.warning(f"Static directory not found at {static_dir.absolute()}")

# Check if FFmpeg is installed
try:
    import subprocess
    result = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        logger.warning("FFmpeg may not be installed or not in PATH. Audio conversion might fail.")
    else:
        logger.info("FFmpeg found and working.")
except Exception as e:
    logger.warning(f"Error checking FFmpeg: {str(e)}")

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

@app.get("/status")
def server_status():
    """Endpoint to check if the server is up and running"""
    return {"status": "ok", "message": "Server is running"}

@app.get("/download")
async def download_video(request: Request, url: str = Query(..., description="YouTube video URL"), format: str = Query("video", description="Download format: video or audio")):
    try:
        if not is_valid_youtube_url(url):
            logger.warning(f"Invalid URL format: {url}")
            raise HTTPException(status_code=400, detail="Invalid YouTube URL format")

        # Create a unique ID for this download
        download_id = str(uuid.uuid4())
        
        # Create temp directory in the system's temp folder
        temp_dir = os.path.join(tempfile.gettempdir(), f"yt_dl_{download_id}")
        os.makedirs(temp_dir, exist_ok=True)
        logger.info(f"Created temporary directory: {temp_dir}")

        try:
            # Common options for both video and audio
            common_opts = {
                'quiet': False,
                'no_warnings': False,
                'nocheckcertificate': True,
                'ignoreerrors': False,
                'no_color': True,
                'verbose': True,
                'extract_flat': False,
                'socket_timeout': 30,
                'retries': 5,
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': 'https://www.youtube.com/',
                }
            }

            if format == "audio":
                # Audio download options
                ydl_opts = {
                    **common_opts,
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                }
                file_extension = 'mp3'
                media_type = 'audio/mpeg'
            else:
                # Video download options with direct format selection
                ydl_opts = {
                    **common_opts,
                    'format': '22',  # 720p MP4
                }
                file_extension = 'mp4'
                media_type = 'video/mp4'

            logger.info(f"Starting download for URL: {url} with format: {format}")
            
            # Function to attempt download
            async def try_download():
                def download_task():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        try:
                            # First try to get video info
                            info = ydl.extract_info(url, download=False)
                            if not info:
                                raise Exception("Could not extract video information")
                            # Then download
                            return ydl.extract_info(url, download=True)
                        except Exception as e:
                            logger.error(f"Download error: {str(e)}")
                            raise
                
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, download_task)

            # Try downloading
            try:
                logger.info("Starting download...")
                info = await try_download()
                if not info:
                    raise Exception("No information returned from download process")
                logger.info(f"Download completed: {info.get('title')}")
            except Exception as e:
                error_message = str(e)
                logger.error(f"Download failed: {error_message}")
                
                # Check for specific error messages
                if "Failed to extract any player response" in error_message:
                    # Try with a different format
                    logger.info("Trying with alternative format...")
                    try:
                        alt_opts = {**ydl_opts, 'format': '18'}  # 360p MP4
                        with yt_dlp.YoutubeDL(alt_opts) as ydl:
                            info = ydl.extract_info(url, download=True)
                            if info:
                                logger.info("Alternative format download succeeded")
                                return info
                    except Exception as e2:
                        logger.error(f"Alternative format failed: {str(e2)}")
                        raise HTTPException(
                            status_code=503,
                            detail="YouTube has updated their platform. Please try again in a few minutes."
                        )
                elif "Video unavailable" in error_message:
                    raise HTTPException(status_code=404, detail="Video is unavailable or private")
                elif "Sign in to confirm your age" in error_message:
                    raise HTTPException(status_code=403, detail="Age-restricted video")
                elif "Unable to extract" in error_message:
                    raise HTTPException(
                        status_code=503,
                        detail="Unable to access this video. YouTube might be blocking downloads."
                    )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Could not download video. Please try again later or try a different video."
                    )
            
            # Get the title and clean it
            title = info.get('title', 'download').strip()
            if not title:
                title = 'download'
            # Clean title for filename
            title = re.sub(r'[^\w\-_\. ]', '_', title)
            logger.info(f"Video title: {title}")
            
            # Find the downloaded file
            if format == "audio":
                # For audio, find the MP3 file
                file_pattern = "*.mp3"
            else:
                # For video, find the downloaded video file
                file_pattern = "*"
                
            downloaded_files = list(Path(temp_dir).glob(file_pattern))
            
            if not downloaded_files:
                logger.error(f"No files found in {temp_dir}")
                raise HTTPException(status_code=500, detail="Downloaded file not found")
                
            downloaded_file = str(downloaded_files[0])
            logger.info(f"Found downloaded file: {downloaded_file}")
            
            # Ensure the file exists
            if not os.path.exists(downloaded_file):
                logger.error(f"File not found at path: {downloaded_file}")
                raise HTTPException(status_code=500, detail="Downloaded file not found")

            logger.info(f"Download completed successfully: {downloaded_file}")
            
            # Create a copy to avoid deletion issues
            temp_output_file = os.path.join(tempfile.gettempdir(), f"{title}.{file_extension}")
            shutil.copy2(downloaded_file, temp_output_file)
            
            # Define cleanup function
            def cleanup_files():
                try:
                    # Clean up temp directory
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    # Remove output file after it's been sent
                    if os.path.exists(temp_output_file):
                        os.remove(temp_output_file)
                    logger.info(f"Cleaned up temporary files")
                except Exception as e:
                    logger.error(f"Error cleaning up files: {str(e)}")
            
            # Return the file
            return FileResponse(
                temp_output_file,
                media_type=media_type,
                filename=f"{title}.{file_extension}",
                background=cleanup_files
            )

        except Exception as e:
            logger.error(f"Error in download process: {str(e)}")
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e

    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error: {error_message}")
        
        # Provide more specific error messages based on the error
        if "Video unavailable" in error_message:
            raise HTTPException(status_code=404, detail="Video is unavailable or private")
        elif "Sign in to confirm your age" in error_message:
            raise HTTPException(status_code=403, detail="Age-restricted video")
        elif "Unable to extract" in error_message or "Unable to download" in error_message:
            raise HTTPException(status_code=503, detail="Unable to access this video. YouTube might be blocking downloads.")
        else:
            raise HTTPException(status_code=500, detail=f"Error downloading video: {error_message}")

# This helps with debugging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}