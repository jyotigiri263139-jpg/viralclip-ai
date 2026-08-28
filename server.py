from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

import os
import shutil
import subprocess
import uuid
import glob

import yt_dlp


# =========================================================
# APP
# =========================================================

app = FastAPI(title="ViralClip AI")


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# FOLDERS
# =========================================================

UPLOAD_FOLDER = "uploads"
CLIPS_FOLDER = "clips"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CLIPS_FOLDER, exist_ok=True)


# =========================================================
# STATIC CLIPS
# =========================================================

app.mount(
    "/clips",
    StaticFiles(directory=CLIPS_FOLDER),
    name="clips"
)


# =========================================================
# WEBSITE
# =========================================================

@app.get("/")
def home():
    return FileResponse("index.html")


@app.get("/style.css")
def style_css():
    return FileResponse(
        "style.css",
        media_type="text/css"
    )


@app.get("/script.js")
def script_js():
    return FileResponse(
        "script.js",
        media_type="application/javascript"
    )


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "message": "ViralClip AI is running 🚀"
    }


# =========================================================
# CREATE CLIP WITH FFMPEG
# =========================================================

def create_clip(
    video_path,
    start_time,
    duration,
    clip_number
):

    output_name = (
        f"{uuid.uuid4().hex}"
        f"_clip_{clip_number}.mp4"
    )

    output_path = os.path.join(
        CLIPS_FOLDER,
        output_name
    )

    command = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start_time),
        "-i",
        video_path,
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-c:a",
        "aac",
        output_path
    ]

    print(
        f"🎬 Creating Clip {clip_number}: "
        f"{start_time}s - "
        f"{start_time + duration}s"
    )

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:

            print("❌ FFmpeg error:")
            print(result.stderr)

            return None

        if not os.path.exists(
            output_path
        ):

            print(
                "❌ Output file not created."
            )

            return None

        print(
            f"✅ Clip {clip_number} created"
        )

        return output_name

    except subprocess.TimeoutExpired:

        print(
            f"⏰ Clip {clip_number} timed out"
        )

        return None

    except Exception as e:

        print(
            f"❌ Clip error: {e}"
        )

        return None


# =========================================================
# CREATE 3 CLIPS
# =========================================================

def generate_three_clips(video_path):

    clips = []

    # Current free version:
    # first 30 sec -> 3 clips
    clip_settings = [
        (0, 10),
        (10, 10),
        (20, 10)
    ]

    for index, (
        start_time,
        duration
    ) in enumerate(
        clip_settings,
        start=1
    ):

        output_name = create_clip(
            video_path,
            start_time,
            duration,
            index
        )

        if output_name:

            clips.append(
                f"/clips/{output_name}"
            )

    return clips


# =========================================================
# UPLOAD FROM COMPUTER
# =========================================================

@app.post("/upload")
async def upload_video(
    file: UploadFile = File(...)
):

    original_name = (
        file.filename
        or "video.mp4"
    )

    extension = (
        os.path.splitext(
            original_name
        )[1]
        or ".mp4"
    )

    unique_name = (
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    video_path = os.path.join(
        UPLOAD_FOLDER,
        unique_name
    )

    print("\n================================")
    print("📥 COMPUTER VIDEO RECEIVED")
    print(
        "File:",
        original_name
    )
    print("================================")

    try:

        with open(
            video_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

    except Exception as e:

        print(
            "❌ Save error:",
            e
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Could not save video.",
                "clips": []
            }
        )

    print(
        "✅ Video saved:",
        video_path
    )

    clips = generate_three_clips(
        video_path
    )

    print(
        "✅ TOTAL CLIPS:",
        len(clips)
    )

    if not clips:

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": (
                    "No clips created. "
                    "FFmpeg processing failed."
                ),
                "clips": []
            }
        )

    return {
        "success": True,
        "source": "upload",
        "filename": original_name,
        "message": (
            "Computer video processed 🎬"
        ),
        "clips": clips
    }


# =========================================================
# DOWNLOAD FROM YOUTUBE
# =========================================================

@app.post("/youtube")
async def youtube_video(
    url: str = Form(...)
):

    url = url.strip()

    print("\n================================")
    print("🔗 YOUTUBE VIDEO REQUEST")
    print("URL:", url)
    print("================================")

    if not url:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Please enter a YouTube URL.",
                "clips": []
            }
        )

    if (
        "youtube.com" not in url
        and "youtu.be" not in url
    ):

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Invalid YouTube URL.",
                "clips": []
            }
        )

    video_id = uuid.uuid4().hex

    output_template = os.path.join(
        UPLOAD_FOLDER,
        f"{video_id}.%(ext)s"
    )

    ydl_options = {
        "format": (
            "bv*[ext=mp4]+ba[ext=m4a]"
            "/b[ext=mp4]"
            "/b"
        ),
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
    }

    try:

        print(
            "⬇️ Downloading YouTube video..."
        )

        with yt_dlp.YoutubeDL(
            ydl_options
        ) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            title = (
                info.get("title")
                or "YouTube Video"
            )

        # Find downloaded video
        possible_files = []

        for file_path in glob.glob(
            os.path.join(
                UPLOAD_FOLDER,
                f"{video_id}.*"
            )
        ):

            lower = file_path.lower()

            if lower.endswith(
                (
                    ".mp4",
                    ".webm",
                    ".mkv",
                    ".mov"
                )
            ):

                possible_files.append(
                    file_path
                )

        if not possible_files:

            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": (
                        "YouTube video download "
                        "completed but file was not found."
                    ),
                    "clips": []
                }
            )

        video_path = possible_files[0]

        print(
            "✅ YouTube video downloaded:",
            video_path
        )


        # =====================================
        # CREATE CLIPS
        # =====================================

        clips = generate_three_clips(
            video_path
        )


        print(
            "✅ TOTAL YOUTUBE CLIPS:",
            len(clips)
        )


        if not clips:

            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": (
                        "YouTube video downloaded, "
                        "but clips could not be created."
                    ),
                    "clips": []
                }
            )


        return {
            "success": True,
            "source": "youtube",
            "title": title,
            "message": (
                "YouTube video processed 🎬"
            ),
            "clips": clips
        }


    except yt_dlp.utils.DownloadError as e:

        print(
            "❌ YouTube download error:"
        )

        print(e)

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": (
                    "YouTube video download failed: "
                    + str(e)
                ),
                "clips": []
            }
        )


    except Exception as e:

        print(
            "❌ YouTube processing error:"
        )

        print(e)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": str(e),
                "clips": []
            }
        )