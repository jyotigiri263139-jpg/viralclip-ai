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


app = FastAPI(title="ViralClip AI")


# ============================================
# CORS
# ============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# FOLDERS
# ============================================

UPLOAD_FOLDER = "uploads"
CLIPS_FOLDER = "clips"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CLIPS_FOLDER, exist_ok=True)


# ============================================
# STATIC CLIPS
# ============================================

app.mount(
    "/clips",
    StaticFiles(directory=CLIPS_FOLDER),
    name="clips"
)


# ============================================
# WEBSITE
# ============================================

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


# ============================================
# HEALTH
# ============================================

@app.get("/health")
def health():
    return {
        "success": True,
        "status": "ok",
        "message": "ViralClip AI is running 🚀"
    }


# ============================================
# GET VIDEO DURATION
# ============================================

def get_video_duration(video_path):

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None

        return float(result.stdout.strip())

    except Exception:
        return None


# ============================================
# CREATE CLIP
# ============================================

def create_clip(
    video_path,
    start_time,
    duration,
    clip_number
):

    output_name = (
        f"{uuid.uuid4().hex}"
        f"_viral_{clip_number}.mp4"
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
        f"🎬 Clip {clip_number}: "
        f"{start_time:.1f}s - "
        f"{start_time + duration:.1f}s"
    )

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=180
        )

        if result.returncode != 0:
            print(result.stderr)
            return None

        if not os.path.exists(output_path):
            return None

        return output_name

    except Exception as e:

        print(
            "❌ FFmpeg error:",
            e
        )

        return None


# ============================================
# DYNAMIC CLIP GENERATION
# ============================================

def generate_dynamic_clips(video_path):

    duration = get_video_duration(
        video_path
    )

    if not duration:
        raise Exception(
            "Video duration could not be detected."
        )

    print(
        f"⏱️ Video duration: {duration:.1f}s"
    )

    clips = []
    moments = []

    # ----------------------------------------
    # Dynamic segment sizes
    # ----------------------------------------

    if duration <= 20:

        segments = [
            (0, duration)
        ]

    elif duration <= 40:

        segments = [
            (0, duration / 2),
            (duration / 2, duration / 2)
        ]

    elif duration <= 90:

        # 3 meaningful sections
        part = duration / 3

        segments = [
            (0, part),
            (part, part),
            (part * 2, duration - part * 2)
        ]

    else:

        # For longer videos, create
        # variable-length sections.

        segments = []

        cursor = 0

        index = 0

        lengths = [
            18,
            24,
            30,
            22,
            28,
            20,
            32,
            25,
            18,
            30
        ]

        while (
            cursor < duration
            and index < len(lengths)
        ):

            length = lengths[index]

            remaining = duration - cursor

            actual_length = min(
                length,
                remaining
            )

            if actual_length >= 8:

                segments.append(
                    (
                        cursor,
                        actual_length
                    )
                )

            cursor += actual_length
            index += 1


    # ----------------------------------------
    # Create clips
    # ----------------------------------------

    for clip_number, (
        start_time,
        clip_duration
    ) in enumerate(
        segments,
        start=1
    ):

        output_name = create_clip(
            video_path,
            start_time,
            clip_duration,
            clip_number
        )

        if output_name:

            clips.append(
                f"/clips/{output_name}"
            )

            moments.append({
                "start": round(
                    start_time,
                    2
                ),
                "end": round(
                    start_time + clip_duration,
                    2
                ),
                "score": 50,
                "reason": (
                    "Dynamic video segment"
                )
            })

    return clips, moments


# ============================================
# COMPUTER UPLOAD
# ============================================

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

    print(
        "\n📥 COMPUTER VIDEO:",
        original_name
    )

    try:

        with open(
            video_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

        clips, moments = (
            generate_dynamic_clips(
                video_path
            )
        )

        return {
            "success": True,
            "source": "upload",
            "filename": original_name,
            "clips": clips,
            "moments": moments,
            "message": (
                f"{len(clips)} dynamic clips created 🎬"
            )
        }

    except Exception as e:

        print(
            "❌ Upload processing error:",
            e
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": str(e),
                "clips": [],
                "moments": []
            }
        )


# ============================================
# YOUTUBE
# ============================================

@app.post("/youtube")
async def youtube_video(
    url: str = Form(...)
):

    url = url.strip()

    if not url:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Please enter a YouTube URL.",
                "clips": [],
                "moments": []
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

        possible_files = glob.glob(
            os.path.join(
                UPLOAD_FOLDER,
                f"{video_id}.*"
            )
        )

        video_files = [
            path
            for path in possible_files
            if path.lower().endswith(
                (
                    ".mp4",
                    ".mkv",
                    ".webm",
                    ".mov"
                )
            )
        ]

        if not video_files:
            raise Exception(
                "Downloaded video file not found."
            )

        video_path = video_files[0]

        print(
            "✅ YouTube download complete."
        )

        clips, moments = (
            generate_dynamic_clips(
                video_path
            )
        )

        return {
            "success": True,
            "source": "youtube",
            "title": title,
            "clips": clips,
            "moments": moments,
            "message": (
                f"{len(clips)} dynamic clips created 🎬"
            )
        }

    except Exception as e:

        print(
            "❌ YouTube processing error:",
            e
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": str(e),
                "clips": [],
                "moments": []
            }
        )