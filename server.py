from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import os
import shutil
import subprocess
import uuid
import re

import whisper
from dotenv import load_dotenv


# ============================================
# LOAD ENV
# ============================================

load_dotenv()


# ============================================
# WHISPER MODEL
# ============================================

print("🤖 Loading Whisper model...")

whisper_model = whisper.load_model("tiny")

print("✅ Whisper model loaded.")


# ============================================
# APP
# ============================================

app = FastAPI()


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

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

os.makedirs(
    CLIPS_FOLDER,
    exist_ok=True
)


# ============================================
# SERVE CLIPS
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

    return FileResponse(
        "index.html"
    )


@app.get("/style.css")
def css_file():

    return FileResponse(
        "style.css",
        media_type="text/css"
    )


@app.get("/script.js")
def js_file():

    return FileResponse(
        "script.js",
        media_type="application/javascript"
    )


# ============================================
# FREE VIRAL MOMENT DETECTION
# ============================================

def find_free_viral_moments(segments):

    if not segments:
        return []


    # Words/phrases often associated with
    # interesting moments.
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
        "important",
        "important",
        "why",
        "how",
        "secret",
        "best",
        "never",
        "always",
        "wow",
        "really",
        "surprise"
    ]


    candidates = []


    for segment in segments:

        text = segment.get(
            "text",
            ""
        ).strip()

        start = float(
            segment.get(
                "start",
                0
            )
        )

        end = float(
            segment.get(
                "end",
                start + 3
            )
        )


        if not text:
            continue


        duration = max(
            1,
            end - start
        )


        words = text.split()

        word_count = len(words)


        # Basic score
        score = 0


        # More spoken content
        score += min(
            word_count * 2,
            30
        )


        # Keyword bonus
        lower_text = text.lower()

        for keyword in keywords:

            if keyword.lower() in lower_text:

                score += 12


        # Slight bonus for longer useful sentences
        if word_count >= 8:
            score += 10

        if word_count >= 15:
            score += 10


        candidates.append({
            "start": start,
            "end": end,
            "score": score,
            "text": text
        })


    # Highest score first
    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )


    selected = []


    # Select non-overlapping moments
    for candidate in candidates:

        start = candidate["start"]
        end = candidate["end"]


        # Make clip around the selected speech
        clip_start = max(
            0,
            start - 3
        )

        clip_end = end + 5


        # Keep clips between 8 and 20 seconds
        duration = clip_end - clip_start


        if duration < 8:

            clip_end = clip_start + 8


        if duration > 20:

            clip_end = clip_start + 20


        # Check overlap
        overlap = False

        for previous in selected:

            if not (
                clip_end <= previous["start"]
                or
                clip_start >= previous["end"]
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
            "reason": candidate["text"]
        })


        if len(selected) == 3:
            break


    # If not enough interesting moments,
    # fill remaining clips from transcript
    if len(selected) < 3:

        for segment in segments:

            start = float(
                segment.get(
                    "start",
                    0
                )
            )

            end = float(
                segment.get(
                    "end",
                    start + 10
                )
            )


            clip_start = max(
                0,
                start
            )

            clip_end = min(
                end + 5,
                clip_start + 15
            )


            overlap = False

            for previous in selected:

                if not (
                    clip_end <= previous["start"]
                    or
                    clip_start >= previous["end"]
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
                "score": 50,
                "reason": "Interesting speech segment"
            })


            if len(selected) == 3:
                break


    selected.sort(
        key=lambda x: x["score"],
        reverse=True
    )


    return selected


# ============================================
# CREATE CLIP
# ============================================

def create_clip(
    video_path,
    start,
    end,
    index
):

    duration = max(
        1,
        end - start
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
        str(start),

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


    print("\n================================")
    print("📥 VIDEO RECEIVED")
    print(
        "File:",
        original_name
    )
    print("================================")


    # ========================================
    # SAVE VIDEO
    # ========================================

    with open(
        video_path,
        "wb"
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )


    print(
        "✅ Video saved:",
        video_path
    )


    try:

        # ====================================
        # WHISPER TRANSCRIPTION
        # ====================================

        print(
            "🎤 Transcribing video locally..."
        )


        transcript = whisper_model.transcribe(
            video_path,
            fp16=False
        )


        segments = transcript.get(
            "segments",
            []
        )


        print(
            "✅ Transcript created."
        )


        if not segments:

            return {
                "success": False,
                "message": (
                    "No speech detected."
                ),
                "clips": []
            }


        # ====================================
        # FREE VIRAL SELECTION
        # ====================================

        print(
            "🧠 Finding interesting moments..."
        )


        moments = find_free_viral_moments(
            segments
        )


        print(
            "✅ Selected moments:"
        )

        print(
            moments
        )


        # ====================================
        # CREATE CLIPS
        # ====================================

        clips = []
        scores = []


        for index, moment in enumerate(
            moments,
            start=1
        ):

            print(
                f"🎬 Creating Clip {index}: "
                f"{moment['start']}s - "
                f"{moment['end']}s"
            )


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

                scores.append(
                    moment["score"]
                )


                print(
                    f"✅ Clip {index} created"
                )


        print(
            "✅ TOTAL CLIPS:",
            len(clips)
        )


        return {
            "success": True,
            "message": (
                "Free AI-style viral clips "
                "created 🎬🔥"
            ),
            "filename": original_name,
            "clips": clips,
            "scores": scores,
            "moments": moments
        }


    except Exception as e:

        print(
            "❌ PROCESSING ERROR:"
        )

        print(e)


        return {
            "success": False,
            "message": str(e),
            "clips": []
        }