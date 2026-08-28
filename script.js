const videoInput =
    document.getElementById("videoInput");

const videoPreview =
    document.getElementById("videoPreview");

const previewBox =
    document.getElementById("previewBox");

const fileName =
    document.getElementById("fileName");

const generateBtn =
    document.getElementById("generateBtn");

const loading =
    document.getElementById("loading");

const loadingTitle =
    document.getElementById("loadingTitle");

const loadingText =
    document.getElementById("loadingText");

const clipsSection =
    document.getElementById("clipsSection");

const clipsContainer =
    document.getElementById("clipsContainer");

const clipsMessage =
    document.getElementById("clipsMessage");


// =====================================================
// YOUTUBE PROCESSOR
// =====================================================

const YOUTUBE_PROCESSOR =
    "https://burst-rfc-club-friend.trycloudflare.com";


// =====================================================
// VIDEO SELECT
// =====================================================

if (videoInput) {

    videoInput.addEventListener(
        "change",
        function () {

            const file =
                videoInput.files[0];

            if (!file) {
                return;
            }


            fileName.textContent =
                "Selected: " + file.name;


            const videoURL =
                URL.createObjectURL(file);


            videoPreview.src =
                videoURL;


            videoPreview.load();


            previewBox.style.display =
                "block";


            loading.style.display =
                "none";


            clipsSection.style.display =
                "none";


            clipsContainer.innerHTML =
                "";


            clipsMessage.textContent =
                "";


            generateBtn.disabled =
                false;


            generateBtn.textContent =
                "🚀 Generate Viral Clips";


            generateBtn.style.opacity =
                "1";


            generateBtn.style.cursor =
                "pointer";
        }
    );
}


// =====================================================
// YOUTUBE
// =====================================================

const youtubeBtn =
    document.getElementById(
        "youtubeBtn"
    );

const youtubeUrl =
    document.getElementById(
        "youtubeUrl"
    );

const youtubeStatus =
    document.getElementById(
        "youtubeStatus"
    );


if (youtubeBtn) {

    youtubeBtn.addEventListener(
        "click",
        async function (event) {

            event.preventDefault();


            const url =
                youtubeUrl.value.trim();


            // =========================================
            // CHECK URL
            // =========================================

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


            // =========================================
            // BUTTON
            // =========================================

            youtubeBtn.disabled =
                true;


            youtubeBtn.textContent =
                "⏳ Processing...";


            youtubeStatus.textContent =
                "⬇️ Processing YouTube video...";


            // =========================================
            // LOADING
            // =========================================

            loading.style.display =
                "block";


            loadingTitle.textContent =
                "⬇️ Processing YouTube video...";


            loadingText.textContent =
                "Downloading video and creating clips...";


            clipsSection.style.display =
                "none";


            try {

                // =====================================
                // FORM
                // =====================================

                const formData =
                    new FormData();


                formData.append(
                    "url",
                    url
                );


                // =====================================
                // SEND TO LAPTOP
                // =====================================

                const response =
                    await fetch(
                        YOUTUBE_PROCESSOR +
                        "/youtube",
                        {
                            method: "POST",
                            body: formData
                        }
                    );


                const text =
                    await response.text();


                console.log(
                    "YouTube response:",
                    text
                );


                // =====================================
                // ERROR
                // =====================================

                if (!response.ok) {

                    let errorMessage =
                        "YouTube processing failed.";


                    try {

                        const errorData =
                            JSON.parse(text);


                        errorMessage =
                            errorData.message ||
                            errorMessage;

                    } catch (e) {

                        if (text) {

                            errorMessage =
                                text;
                        }
                    }


                    throw new Error(
                        errorMessage
                    );
                }


                // =====================================
                // JSON
                // =====================================

                const result =
                    JSON.parse(text);


                if (
                    !result ||
                    !Array.isArray(
                        result.clips
                    ) ||
                    result.clips.length === 0
                ) {

                    throw new Error(
                        result.message ||
                        "No clips were created."
                    );
                }


                // =====================================
                // READY
                // =====================================

                loadingTitle.textContent =
                    "✅ YouTube clips ready!";


                loadingText.textContent =
                    "Your clips have been created 🎬";


                // =====================================
                // FIX CLIP URLS
                // =====================================

                const youtubeClips =
                    result.clips.map(
                        function (clip) {

                            return new URL(
                                clip,
                                YOUTUBE_PROCESSOR
                            ).href;
                        }
                    );


                // =====================================
                // SHOW
                // =====================================

                showClips(
                    youtubeClips,
                    result.moments || []
                );


                youtubeStatus.textContent =
                    "✅ YouTube video processed successfully.";


            } catch (error) {

                console.error(
                    "YOUTUBE ERROR:",
                    error
                );


                loadingTitle.textContent =
                    "❌ YouTube Error";


                loadingText.textContent =
                    error.message ||
                    "YouTube processing failed.";


                youtubeStatus.textContent =
                    error.message ||
                    "YouTube processing failed.";


            } finally {

                youtubeBtn.disabled =
                    false;


                youtubeBtn.textContent =
                    "Use YouTube Video";
            }
        }
    );
}


// =====================================================
// COMPUTER UPLOAD
// =====================================================

async function uploadVideoToBackend(
    file
) {

    const formData =
        new FormData();


    formData.append(
        "file",
        file
    );


    const response =
        await fetch(
            "/upload",
            {
                method: "POST",
                body: formData
            }
        );


    const text =
        await response.text();


    console.log(
        "Backend status:",
        response.status
    );


    console.log(
        "Backend response:",
        text
    );


    if (!response.ok) {

        let message =
            "Backend error " +
            response.status;


        try {

            const data =
                JSON.parse(text);


            message =
                data.message ||
                message;

        } catch (e) {

            if (text) {

                message =
                    text;
            }
        }


        throw new Error(
            message
        );
    }


    try {

        return JSON.parse(text);

    } catch (error) {

        throw new Error(
            "Backend response JSON nahi hai."
        );
    }
}


// =====================================================
// SHOW CLIPS
// =====================================================

function showClips(
    clips,
    moments = []
) {

    clipsContainer.innerHTML =
        "";


    clips.forEach(
        function (
            clip,
            index
        ) {

            const clipURL =
                clip;


            // =====================================
            // ACTUAL DURATION
            // =====================================

            let durationText =
                "Dynamic duration";


            if (moments[index]) {

                const start =
                    Number(
                        moments[index].start ||
                        0
                    );


                const end =
                    Number(
                        moments[index].end ||
                        0
                    );


                const duration =
                    Math.max(
                        0,
                        end - start
                    );


                if (duration > 0) {

                    durationText =
                        `${duration.toFixed(1)} seconds`;
                }
            }


            // =====================================
            // CARD
            // =====================================

            const card =
                document.createElement(
                    "div"
                );


            card.style.cssText = `
                background:white;
                margin-top:25px;
                padding:20px;
                border-radius:16px;
                text-align:center;
                box-shadow:
                    0 5px 20px
                    rgba(0,0,0,0.08);
            `;


            // =====================================
            // HTML
            // =====================================

            card.innerHTML = `
                <h3>
                    🔥 Viral Clip ${index + 1}
                </h3>

                <p style="
                    color:#666;
                    margin-top:8px;
                ">
                    🎬 ${durationText}
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

                    Your browser does not support
                    video playback.
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


            clipsContainer.appendChild(
                card
            );
        }
    );


    clipsMessage.textContent =
        clips.length +
        " dynamic clips successfully created 🎬";


    clipsSection.style.display =
        "block";


    setTimeout(
        function () {

            clipsSection.scrollIntoView({
                behavior: "smooth"
            });

        },
        300
    );
}


// =====================================================
// COMPUTER VIDEO GENERATE
// =====================================================

if (generateBtn) {

    generateBtn.addEventListener(
        "click",
        async function (event) {

            event.preventDefault();


            if (
                generateBtn.disabled
            ) {

                return;
            }


            const file =
                videoInput.files[0];


            if (!file) {

                alert(
                    "Please select a video first."
                );

                return;
            }


            // =====================================
            // BUTTON
            // =====================================

            generateBtn.disabled =
                true;


            generateBtn.textContent =
                "⏳ Processing...";


            generateBtn.style.opacity =
                "0.6";


            generateBtn.style.cursor =
                "not-allowed";


            // =====================================
            // LOADING
            // =====================================

            loading.style.display =
                "block";


            loadingTitle.textContent =
                "📤 Uploading video...";


            loadingText.textContent =
                "Creating your dynamic clips...";


            clipsSection.style.display =
                "none";


            try {

                // =================================
                // UPLOAD
                // =================================

                const result =
                    await uploadVideoToBackend(
                        file
                    );


                // =================================
                // CHECK
                // =================================

                if (
                    !result ||
                    !Array.isArray(
                        result.clips
                    ) ||
                    result.clips.length === 0
                ) {

                    throw new Error(
                        result.message ||
                        "No clips created."
                    );
                }


                // =================================
                // READY
                // =================================

                loadingTitle.textContent =
                    "✅ Clips Ready!";


                loadingText.textContent =
                    "Your dynamic clips have been created 🎬";


                // =================================
                // SHOW
                // =================================

                showClips(
                    result.clips,
                    result.moments || []
                );


                // =================================
                // RESET BUTTON
                // =================================

                generateBtn.disabled =
                    false;


                generateBtn.textContent =
                    "🚀 Generate Again";


                generateBtn.style.opacity =
                    "1";


                generateBtn.style.cursor =
                    "pointer";


            } catch (error) {

                console.error(
                    "UPLOAD ERROR:",
                    error
                );


                loadingTitle.textContent =
                    "❌ Error";


                loadingText.textContent =
                    error.message ||
                    "Something went wrong.";


                generateBtn.disabled =
                    false;


                generateBtn.textContent =
                    "🚀 Try Again";


                generateBtn.style.opacity =
                    "1";


                generateBtn.style.cursor =
                    "pointer";
            }
        }
    );
}