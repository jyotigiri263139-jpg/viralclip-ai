const videoInput = document.getElementById("videoInput");
const videoPreview = document.getElementById("videoPreview");
const previewBox = document.getElementById("previewBox");
const fileName = document.getElementById("fileName");

const generateBtn = document.getElementById("generateBtn");

const loading = document.getElementById("loading");
const loadingTitle = document.getElementById("loadingTitle");
const loadingText = document.getElementById("loadingText");

const clipsSection = document.getElementById("clipsSection");
const clipsContainer = document.getElementById("clipsContainer");
const clipsMessage = document.getElementById("clipsMessage");


// ================================
// VIDEO SELECT
// ================================

videoInput.addEventListener("change", function () {

    const file = videoInput.files[0];

    if (!file) return;

    fileName.textContent = "Selected: " + file.name;

    const videoURL = URL.createObjectURL(file);

    videoPreview.src = videoURL;
    videoPreview.load();

    previewBox.style.display = "block";
    loading.style.display = "none";

    clipsSection.style.display = "none";
    clipsContainer.innerHTML = "";
    clipsMessage.textContent = "";

    generateBtn.disabled = false;
    generateBtn.textContent = "🚀 Generate Viral Clips";
    generateBtn.style.opacity = "1";
    generateBtn.style.cursor = "pointer";
});


// ================================
// YOUTUBE
// ================================

const youtubeBtn = document.getElementById("youtubeBtn");
const youtubeUrl = document.getElementById("youtubeUrl");
const youtubeStatus = document.getElementById("youtubeStatus");

if (youtubeBtn) {

    youtubeBtn.addEventListener("click", function (event) {

        event.preventDefault();

        const url = youtubeUrl.value.trim();

        if (!url) {
            youtubeStatus.textContent =
                "Please paste a YouTube link.";
            return;
        }

        if (
            !url.includes("youtube.com") &&
            !url.includes("youtu.be")
        ) {
            youtubeStatus.textContent =
                "Please enter a valid YouTube link.";
            return;
        }

        youtubeStatus.textContent =
            "✅ YouTube link received.";

    });
}


// ================================
// UPLOAD TO BACKEND
// ================================

async function uploadVideoToBackend(file) {

    const formData = new FormData();

    formData.append("file", file);

    const response = await fetch(
        "http://127.0.0.1:8000/upload",
        {
            method: "POST",
            body: formData
        }
    );

    const text = await response.text();

    console.log("Backend status:", response.status);
    console.log("Backend response:", text);

    if (!response.ok) {
        throw new Error(
            "Backend error " +
            response.status +
            ": " +
            text
        );
    }

    try {
        return JSON.parse(text);
    } catch (error) {
        throw new Error(
            "Backend response JSON nahi hai: " + text
        );
    }
}


// ================================
// SHOW CLIPS
// ================================

function showClips(clips) {

    clipsContainer.innerHTML = "";

    clips.forEach(function (clip, index) {

        const clipURL =
            "http://127.0.0.1:8000" + clip;

        const card = document.createElement("div");

        card.style.cssText = `
            background:white;
            margin-top:25px;
            padding:20px;
            border-radius:16px;
            text-align:center;
        `;

        card.innerHTML = `
            <h3>🔥 Viral Clip ${index + 1}</h3>

            <p style="color:#666;margin-top:8px;">
                10 second short clip
            </p>

            <video
                controls
                playsinline
                preload="metadata"
                style="
                    width:100%;
                    max-width:500px;
                    margin-top:15px;
                    border-radius:12px;
                    background:#000;
                "
            >
                <source
                    src="${clipURL}"
                    type="video/mp4"
                >
            </video>

            <br><br>

            <a
                href="${clipURL}"
                target="_blank"
                rel="noopener noreferrer"
                style="
                    display:inline-block;
                    padding:12px 20px;
                    background:#ff1744;
                    color:white;
                    text-decoration:none;
                    border-radius:10px;
                    margin:5px;
                "
            >
                ▶ Open Clip
            </a>

            <a
                href="${clipURL}"
                download
                style="
                    display:inline-block;
                    padding:12px 20px;
                    background:#111;
                    color:white;
                    text-decoration:none;
                    border-radius:10px;
                    margin:5px;
                "
            >
                ⬇️ Download
            </a>
        `;

        clipsContainer.appendChild(card);
    });

    clipsMessage.textContent =
        clips.length + " clips successfully created 🎬";

    clipsSection.style.display = "block";

    setTimeout(function () {
        clipsSection.scrollIntoView({
            behavior: "smooth"
        });
    }, 300);
}


// ================================
// GENERATE
// ================================

generateBtn.addEventListener(
    "click",
    async function (event) {

        event.preventDefault();

        if (generateBtn.disabled) {
            return;
        }

        const file = videoInput.files[0];

        if (!file) {
            alert("Please select a video first.");
            return;
        }

        generateBtn.disabled = true;
        generateBtn.textContent = "⏳ Processing...";
        generateBtn.style.opacity = "0.6";

        loading.style.display = "block";

        loadingTitle.textContent =
            "📤 Uploading video...";

        loadingText.textContent =
            "Please wait while clips are being created.";

        clipsSection.style.display = "none";

        try {

            const result =
                await uploadVideoToBackend(file);

            console.log("RESULT:", result);

            if (
                !result ||
                !Array.isArray(result.clips)
            ) {
                throw new Error(
                    "Backend ne clips list nahi bheji."
                );
            }

            if (result.clips.length === 0) {

                loadingTitle.textContent =
                    "⚠️ No clips created";

                loadingText.textContent =
                    "Backend se 0 clips mili.";

                generateBtn.disabled = false;
                generateBtn.textContent =
                    "🚀 Generate Viral Clips";
                generateBtn.style.opacity = "1";

                return;
            }

            loadingTitle.textContent =
                "✅ Clips Ready!";

            loadingText.textContent =
                "Your clips have been created 🎬";

            showClips(result.clips);

            generateBtn.disabled = false;
            generateBtn.textContent =
                "🚀 Generate Again";
            generateBtn.style.opacity = "1";
            generateBtn.style.cursor = "pointer";

        } catch (error) {

            console.error("FINAL ERROR:", error);

            loadingTitle.textContent =
                "❌ Error";

            loadingText.textContent =
                error.message;

            generateBtn.disabled = false;
            generateBtn.textContent =
                "🚀 Try Again";
            generateBtn.style.opacity = "1";
            generateBtn.style.cursor = "pointer";
        }
    }
);