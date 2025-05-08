# YouTube Downloader

A FastAPI-based web application that allows users to download YouTube videos in both video and audio formats.

## Features

- Download YouTube videos in MP4 format
- Download audio in MP3 format
- Simple and clean user interface
- Fast and efficient downloads

## Requirements

- Python 3.8 or higher
- FFmpeg (for audio conversion)

## Installation

1. Clone the repository:
```bash
git clone <your-repository-url>
cd youtube_downloader
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Linux/Mac
source venv/bin/activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Install FFmpeg:
- Windows: Download from https://ffmpeg.org/download.html and add to PATH
- Linux: `sudo apt-get install ffmpeg`
- Mac: `brew install ffmpeg`

## Running the Application

1. Start the server:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

2. Open your browser and navigate to:
```
http://localhost:8000
```

## Deployment

For production deployment, it's recommended to:
1. Use a production-grade ASGI server like Gunicorn
2. Set up a reverse proxy (like Nginx)
3. Use environment variables for configuration
4. Implement proper security measures

## License

MIT License 