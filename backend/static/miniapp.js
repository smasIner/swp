// Configuration
const API_BASE_URL = "";
const HIGHLIGHT_COLOR = "#FFEB3B"; // Yellow highlight color
const WORD_PADDING = 50; // ms padding around word timing

// DOM Elements
const textContainer = document.getElementById("text-container");
const playButton = document.getElementById("play-button");
const audioPlayer = document.getElementById("audio-player");
const errorMessage = document.getElementById("error-message");
const matchStatus = document.getElementById("match-status");

// State
let wordTimings = [];
let currentWordIndex = 0;
let words = [];
let isPlaying = false;

// Initialize Telegram WebApp
const tg = window.Telegram?.WebApp;
if (tg) {
    tg.expand(); // Expand the WebApp to full height
    tg.enableClosingConfirmation(); // Prevent accidental closing
}

// Get IDs from URL
const urlParams = new URLSearchParams(window.location.search);
const documentId = urlParams.get("document_id");
const recordingId = urlParams.get("recording_id");

// Validate required parameters
if (!documentId || !recordingId) {
    showError("Document ID and Recording ID are required.");
    throw new Error("Missing required parameters");
}

// Load recording data
loadRecording(documentId, recordingId);

// Play button handler
playButton.addEventListener("click", togglePlayback);

// Audio player event listeners
audioPlayer.addEventListener("timeupdate", updateHighlight);
audioPlayer.addEventListener("ended", onPlaybackEnd);
audioPlayer.addEventListener("play", () => { isPlaying = true; });
audioPlayer.addEventListener("pause", () => { isPlaying = false; });

// Main function to load recording data
async function loadRecording(docId, recId) {
    try {
        const response = await fetch(`${API_BASE_URL}/recordings/${docId}/${recId}`);

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();

        // Set match status
        matchStatus.textContent = data.content_match ? "✅ Content matches" : "❌ Content doesn't match";

        if (!data.content_match) {
            showError("Playback is blocked due to content mismatch.");
            return;
        }

        // Set audio source
        audioPlayer.src = `/${data.audio_path}`;
        wordTimings = data.word_timings || [];

        // Prepare text content
        words = data.transcribed_text.split(/\s+/);
        renderText(words);

        // Enable play button
        playButton.disabled = false;

    } catch (error) {
        showError(`Failed to load recording: ${error.message}`);
        console.error("Loading error:", error);
    }
}

// Render text with clickable words
function renderText(words) {
    textContainer.innerHTML = "";

    words.forEach((word, index) => {
        const wordSpan = document.createElement("span");
        wordSpan.className = "word";
        wordSpan.textContent = word;
        wordSpan.dataset.index = index;

        // Add click handler to seek to word
        wordSpan.addEventListener("click", () => {
            if (index < wordTimings.length && wordTimings[index].start !== undefined) {
                const startTime = Math.max(0, wordTimings[index].start - (WORD_PADDING/1000));
                audioPlayer.currentTime = startTime;
                if (!isPlaying) {
                    audioPlayer.play();
                }
            }
        });

        textContainer.appendChild(wordSpan);
        // Add space after word except the last one
        if (index < words.length - 1) {
            textContainer.appendChild(document.createTextNode(" "));
        }
    });
}

// Update word highlighting based on audio position
function updateHighlight() {
    const currentTime = audioPlayer.currentTime * 1000; // Convert to ms
    let newWordIndex = -1;

    // Find the current word
    for (let i = 0; i < wordTimings.length; i++) {
        const word = wordTimings[i];
        if (word.start !== undefined && word.end !== undefined) {
            // Add some padding to the word timing
            const start = word.start * 1000 - WORD_PADDING;
            const end = word.end * 1000 + WORD_PADDING;

            if (currentTime >= start && currentTime <= end) {
                newWordIndex = i;
                break;
            }
        }
    }

    // Only update if word changed
    if (newWordIndex !== currentWordIndex) {
        // Remove old highlight
        if (currentWordIndex >= 0) {
            const prevWord = textContainer.querySelector(`.word[data-index="${currentWordIndex}"]`);
            if (prevWord) {
                prevWord.style.backgroundColor = "";
                prevWord.style.color = "";
                prevWord.classList.remove("active");
            }
        }

        // Add new highlight
        if (newWordIndex >= 0) {
            const currentWord = textContainer.querySelector(`.word[data-index="${newWordIndex}"]`);
            if (currentWord) {
                currentWord.style.backgroundColor = HIGHLIGHT_COLOR;
                currentWord.style.color = "#000";
                currentWord.classList.add("active");

                // Simple scroll into view (basic implementation)
                currentWord.scrollIntoView({
                    behavior: "smooth",
                    block: "center",
                    inline: "center"
                });
            }
        }

        currentWordIndex = newWordIndex;
    }
}

function togglePlayback() {
    if (audioPlayer.paused) {
        audioPlayer.play().catch(error => {
            showError(`Playback failed: ${error.message}`);
        });
        playButton.textContent = "Pause";
    } else {
        audioPlayer.pause();
        playButton.textContent = "Play";
    }
}

function onPlaybackEnd() {
    playButton.textContent = "Play";
    if (currentWordIndex >= 0) {
        const lastWord = textContainer.querySelector(`.word[data-index="${currentWordIndex}"]`);
        if (lastWord) {
            lastWord.style.backgroundColor = "";
            lastWord.style.color = "";
            lastWord.classList.remove("active");
        }
    }
    currentWordIndex = -1;
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = "block";
    playButton.disabled = true;
}