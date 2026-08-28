from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

import os
import shutil
import subprocess
import uuid


# ============================================
# APP
# ============================================

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
# SERVE GENERATED CLIPS
# ============================================

app.mount(
    "/clips",
    StaticFiles(directory=CLIPS_FOLDER),
    name="clips"
)


# ============================================
# HOME
# ============================================

@app.get("/")
def home():
    return FileResponse("index.html")


# ============================================
# CSS
# ============================================

@app.get("/style.css")
def style_css():
    return FileResponse(
        "style.css",
        media_type="text/css"
    )


# ============================================
# JAVASCRIPT
# ============================================

@app.get("/script.js")
def script_js():
    return FileResponse(
        "script.js",
        media_type="application/javascript"
    )


# ============================================
# HEALTH CHECK
# ============================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "message": "ViralClip AI is running 🚀"
    }


# ============================================
# CREATE ONE CLIP
# ============================================

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

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode != 0:
        print("FFmpeg error:")
        print(result.stderr)
        return None

    if not os.path.exists(output_path):
        return None

    return output_name


# ============================================
# UPLOAD VIDEO
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


    print("\n==============================")
    print("📥 VIDEO RECEIVED")
    print(
        "File:",
        original_name
    )
    print("==============================")


    # ========================================
    # SAVE UPLOADED VIDEO
    # ========================================

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
            "❌ Upload save error:",
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


    # ========================================
    # CREATE 3 SHORT CLIPS
    # ========================================

    # Lightweight free version:
    # first 30 seconds in 3 sections

    clip_settings = [
        (0, 10),
        (10, 10),
        (20, 10)
    ]


    clips = []


    for index, (
        start_time,
        duration
    ) in enumerate(
        clip_settings,
        start=1
    ):

        print(
            f"🎬 Creating Clip {index}: "
            f"{start_time}s - "
            f"{start_time + duration}s"
        )


        try:

            output_name = create_clip(
                video_path,
                start_time,
                duration,
                index
            )


            if output_name:

                clip_url = (
                    f"/clips/{output_name}"
                )

                clips.append(
                    clip_url
                )

                print(
                    f"✅ Clip {index} created"
                )

            else:

                print(
                    f"❌ Clip {index} failed"
                )

        except Exception as e:

            print(
                f"❌ Clip {index} error:",
                e
            )


    print(
        "✅ TOTAL CLIPS:",
        len(clips)
    )

    print(
        "==============================\n"
    )


    if not clips:

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": (
                    "No clips were created. "
                    "Check FFmpeg installation."
                ),
                "clips": []
            }
        )


    return {
        "success": True,
        "message": (
            "Clips created successfully 🎬"
        ),
        "filename": original_name,
        "clips": clips
    }