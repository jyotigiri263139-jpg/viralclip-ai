from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

import os
import shutil
import subprocess
import uuid
import glob

import whisper
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


app.mount(
    "/clips",
    StaticFiles(directory=CLIPS_FOLDER),
    name="clips"
)


# =========================================================
# WHISPER
# =========================================================

print("🤖 Loading Whisper...")

whisper_model = whisper.load_model("tiny")

print("✅ Whisper loaded")


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
# GET INTERESTING MOMENTS
# =========================================================

def find_dynamic_moments(segments):

    if not segments:
        return []


    # Words that often appear around hooks,
    # reactions, surprises or important statements.
    keywords = [
        "लेकिन",
        "क्यों",
        "कैसे",
        "सच",
        "गलत",
        "देखो",
        "वाह",
        "अरे",
        "मतलब",
        "कभी",
        "पहली",
        "पहले",
        "सबसे",
        "याद",
        "पता",
        "important",
        "why",
        "how",
        "secret",
        "best",
        "never",
        "always",
        "really",
        "wow",
        "surprise",
    ]


    candidates = []


    for segment in segments:

        text = (
            segment.get("text", "")
            .strip()
        )

        if not text:
            continue


        start = float(
            segment.get("start", 0)
        )

        end = float(
            segment.get("end", start + 2)
        )


        duration = max(
            0.5,
            end - start
        )


        words = text.split()

        score = 0


        # More words in a segment = more information
        score += min(
            len(words) * 2,
            30
        )


        # Keyword bonus
        lower_text = text.lower()

        for word in keywords:

            if word.lower() in lower_text:
                score += 12


        # Longer sentence bonus
        if len(words) >= 8:
            score += 10

        if len(words) >= 15:
            score += 10


        # Slight duration bonus
        if duration >= 2:
            score += 5


        candidates.append({
            "start": start,
            "end": end,
            "score": score,
            "text": text,
        })


    # Highest score first
    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )


    # =====================================================
    # BUILD VARIABLE-LENGTH CLIPS
    # =====================================================

    selected = []


    for candidate in candidates:

        center = (
            candidate["start"] +
            candidate["end"]
        ) / 2


        # Start a little before the interesting line
        clip_start = max(
            0,
            candidate["start"] - 3
        )


        # End a little after it
        clip_end = (
            candidate["end"] + 5
        )


        # Now absorb nearby speech.
        # This makes duration dynamic instead of fixed.
        for segment in segments:

            s = float(
                segment.get("start", 0)
            )

            e = float(
                segment.get(
                    "end",
                    s + 1
                )
            )


            # Nearby segment
            if (
                s <= clip_end + 2
                and
                e >= clip_start - 2
            ):

                if s < clip_start:
                    clip_start = s

                if e > clip_end:
                    clip_end = e


        # Keep reasonable short-form length,
        # but DO NOT force 10 seconds.
        #
        # Small climax:
        # 8-12 sec
        #
        # Normal:
        # 15-30 sec
        #
        # Story climax:
        # up to 45 sec

        duration = (
            clip_end - clip_start
        )


        if duration < 6:

            clip_start = max(
                0,
                center - 3
            )

            clip_end = (
                clip_start + 6
            )


        if duration > 45:

            clip_start = max(
                0,
                center - 20
            )

            clip_end = (
                clip_start + 45
            )


        # =================================================
        # REMOVE OVERLAPPING CLIPS
        # =================================================

        overlap = False


        for old in selected:

            if not (
                clip_end <= old["start"]
                or
                clip_start >= old["end"]
            ):

                overlap = True
                break


        if overlap:
            continue


        selected.append({
            "start": round(
                clip_start,
                2
            ),
            "end": round(
                clip_end,
                2
            ),
            "score": candidate["score"],
            "reason": candidate["text"],
        })


        # We don't force exactly 3.
        #
        # More moments = more clips.
        #
        # To avoid generating hundreds of tiny clips,
        # stop after 10 strong moments.
        if len(selected) >= 10:
            break


    # Highest score first
    selected.sort(
        key=lambda x: x["score"],
        reverse=True
    )


    return selected


# =========================================================
# CREATE CLIP
# =========================================================

def create_clip(
    video_path,
    start_time,
    end_time,
    index
):

    duration = max(
        1,
        end_time - start_time
    )


    output_name = (
        f"{uuid.uuid4().hex}"
        f"_viral_{index}.mp4"
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
        f"🎬 Clip {index}: "
        f"{start_time:.1f}s → "
        f"{end_time:.1f}s "
        f"({duration:.1f}s)"
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

            return None


        return output_name


    except Exception as e:

        print(
            "❌ Clip creation error:",
            e
        )

        return None


# =========================================================
# PROCESS VIDEO
# =========================================================

def process_video(video_path):

    print(
        "🎤 Creating transcript..."
    )


    transcript = whisper_model.transcribe(
        video_path,
        fp16=False
    )


    segments = transcript.get(
        "segments",
        []
    )


    if not segments:

        return {
            "clips": [],
            "moments": []
        }


    print(
        "✅ Transcript created"
    )


    print(
        "🧠 Finding dynamic climax moments..."
    )


    moments = find_dynamic_moments(
        segments
    )


    print(
        "✅ Interesting moments:",
        len(moments)
    )


    clips = []


    for index, moment in enumerate(
        moments,
        start=1
    ):

        output_name = create_clip(
            video_path,
            moment["start"],
            moment["end"],
            index
        )


        if output_name:

            clips.append(
                f"/clips/{output_name}"
            )


    return {
        "clips": clips,
        "moments": moments
    }


# =========================================================
# COMPUTER UPLOAD
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
        "\n📥 VIDEO RECEIVED:",
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


        result = process_video(
            video_path
        )


        clips = result["clips"]


        return {
            "success": True,
            "message": (
                f"{len(clips)} dynamic clips created 🎬"
            ),
            "filename": original_name,
            "clips": clips,
            "moments": result["moments"]
        }


    except Exception as e:

        print(
            "❌ PROCESSING ERROR:",
            e
        )


        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": str(e),
                "clips": []
            }
        )


# =========================================================
# YOUTUBE
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
                "message": (
                    "Please enter a YouTube URL."
                ),
                "clips": []
            }
        )


    print(
        "\n🔗 YOUTUBE URL:",
        url
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
            "⬇️ Downloading YouTube..."
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
            "✅ YouTube downloaded"
        )


        result = process_video(
            video_path
        )


        clips = result["clips"]


        return {
            "success": True,
            "source": "youtube",
            "title": title,
            "message": (
                f"{len(clips)} dynamic clips created 🎬"
            ),
            "clips": clips,
            "moments": result["moments"]
        }


    except Exception as e:

        print(
            "❌ YOUTUBE ERROR:",
            e
        )


        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": str(e),
                "clips": []
            }
        )