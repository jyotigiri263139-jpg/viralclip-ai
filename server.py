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
    allow_credentials=False,
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
# WEBSITE FILES
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
        "success": True,
        "status": "ok",
        "message": "ViralClip AI is running 🚀"
    }


# =========================================================
# VIDEO DURATION
# =========================================================

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
            print("❌ ffprobe error:")
            print(result.stderr)
            return None

        value = result.stdout.strip()

        if not value:
            return None

        return float(value)

    except Exception as e:

        print(
            "❌ Duration error:",
            e
        )

        return None


# =========================================================
# CREATE ONE CLIP
# =========================================================

def create_clip(
    video_path,
    start_time,
    clip_duration,
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
        str(clip_duration),

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
        f"{start_time:.1f}s → "
        f"{start_time + clip_duration:.1f}s "
        f"({clip_duration:.1f}s)"
    )

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=180
        )

        if result.returncode != 0:

            print(
                "❌ FFmpeg error:"
            )

            print(
                result.stderr
            )

            return None

        if not os.path.exists(
            output_path
        ):

            print(
                "❌ Clip was not created."
            )

            return None

        print(
            f"✅ Clip {clip_number} ready"
        )

        return output_name

    except subprocess.TimeoutExpired:

        print(
            f"⏰ Clip {clip_number} timed out"
        )

        return None

    except Exception as e:

        print(
            f"❌ Clip {clip_number} error:",
            e
        )

        return None


# =========================================================
# DYNAMIC CLIP PLAN
# =========================================================

def build_clip_plan(video_duration):

    # Very short video
    if video_duration <= 20:

        return [
            {
                "start": 0,
                "duration": video_duration
            }
        ]


    # 20-40 seconds
    if video_duration <= 40:

        part = video_duration / 2

        return [
            {
                "start": 0,
                "duration": part
            },
            {
                "start": part,
                "duration": video_duration - part
            }
        ]


    # 40-90 seconds
    if video_duration <= 90:

        part = video_duration / 3

        return [
            {
                "start": 0,
                "duration": part
            },
            {
                "start": part,
                "duration": part
            },
            {
                "start": part * 2,
                "duration": (
                    video_duration -
                    part * 2
                )
            }
        ]


    # Longer videos
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

    plan = []

    cursor = 0
    index = 0

    while (
        cursor < video_duration
        and index < len(lengths)
    ):

        requested_length = lengths[index]

        remaining = (
            video_duration -
            cursor
        )

        actual_length = min(
            requested_length,
            remaining
        )

        # Ignore tiny ending pieces
        if actual_length >= 8:

            plan.append({
                "start": cursor,
                "duration": actual_length
            })

        cursor += actual_length
        index += 1

    return plan


# =========================================================
# PROCESS VIDEO
# =========================================================

def process_video(video_path):

    duration = get_video_duration(
        video_path
    )

    if not duration:

        raise Exception(
            "Could not detect video duration."
        )

    print(
        f"⏱️ Video duration: "
        f"{duration:.1f} seconds"
    )

    plan = build_clip_plan(
        duration
    )

    print(
        f"🧠 Dynamic clip count: "
        f"{len(plan)}"
    )

    clips = []
    moments = []

    for index, item in enumerate(
        plan,
        start=1
    ):

        start = float(
            item["start"]
        )

        clip_duration = float(
            item["duration"]
        )

        output_name = create_clip(
            video_path,
            start,
            clip_duration,
            index
        )

        if output_name:

            clips.append(
                f"/clips/{output_name}"
            )

            moments.append({
                "start": round(
                    start,
                    2
                ),
                "end": round(
                    start + clip_duration,
                    2
                ),
                "score": 50,
                "reason": (
                    "Dynamic video segment"
                )
            })

    return clips, moments


# =========================================================
# COMPUTER VIDEO UPLOAD
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

    print(
        "\n===================================="
    )

    print(
        "📥 COMPUTER VIDEO RECEIVED"
    )

    print(
        "File:",
        original_name
    )

    print(
        "===================================="
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
            process_video(
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
                f"{len(clips)} "
                f"dynamic clips created 🎬"
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
                "source": "upload",
                "message": str(e),
                "clips": [],
                "moments": []
            }
        )


# =========================================================
# YOUTUBE VIDEO
# =========================================================

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
                "source": "youtube",
                "message": (
                    "Please enter a YouTube URL."
                ),
                "clips": [],
                "moments": []
            }
        )

    if (
        "youtube.com" not in url
        and
        "youtu.be" not in url
    ):

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "source": "youtube",
                "message": (
                    "Please enter a valid YouTube URL."
                ),
                "clips": [],
                "moments": []
            }
        )


    print(
        "\n===================================="
    )

    print(
        "🔗 YOUTUBE REQUEST"
    )

    print(
        url
    )

    print(
        "===================================="
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

        "outtmpl":
            output_template,

        "merge_output_format":
            "mp4",

        "noplaylist":
            True,

        "quiet":
            False,

        "no_warnings":
            False,
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
                "Downloaded video file was not found."
            )


        video_path = (
            video_files[0]
        )


        print(
            "✅ YouTube download completed."
        )


        clips, moments = (
            process_video(
                video_path
            )
        )


        if not clips:

            raise Exception(
                "No clips could be created."
            )


        return {
            "success": True,
            "source": "youtube",
            "title": title,
            "clips": clips,
            "moments": moments,
            "message": (
                f"{len(clips)} "
                f"dynamic clips created 🎬"
            )
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
                "source": "youtube",
                "message": (
                    "YouTube download failed: "
                    + str(e)
                ),
                "clips": [],
                "moments": []
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
                "source": "youtube",
                "message": str(e),
                "clips": [],
                "moments": []
            }
        )