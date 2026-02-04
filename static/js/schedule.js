(() => {
    const modalEl = document.getElementById("cameraModal");
    const video = document.getElementById("scheduleVideo");
    const statusEl = document.getElementById("recognitionStatus");
    const listEl = document.getElementById("recognizedList");

    if (!modalEl || !video || !statusEl || !listEl) {
        return;
    }

    const modal = new bootstrap.Modal(modalEl);
    const recognizedSet = new Set();

    let stream = null;
    let captureTimer = null;
    let activeScheduleId = null;

    const setStatus = (message, level = "secondary") => {
        statusEl.textContent = message;
        statusEl.className = `alert alert-${level}`;
    };

    const stopCamera = () => {
        if (captureTimer) {
            clearInterval(captureTimer);
            captureTimer = null;
        }
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
        video.srcObject = null;
        activeScheduleId = null;
        recognizedSet.clear();
        listEl.innerHTML = "";
        setStatus("Camera stopped.", "secondary");
    };

    const captureAndSend = async () => {
        if (!activeScheduleId || !video.videoWidth) {
            return;
        }

        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL("image/jpeg");

        try {
            const response = await fetch("/recognize", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    image: dataUrl,
                    schedule_id: activeScheduleId
                })
            });
            let payload = {};
            let text = "";
            try {
                payload = await response.json();
            } catch (parseErr) {
                text = await response.text();
            }

            if (!response.ok) {
                setStatus(payload.message || text || "Recognition failed.", "danger");
                return;
            }

            if (Array.isArray(payload.recognized) && payload.recognized.length > 0) {
                payload.recognized.forEach(name => {
                    if (recognizedSet.has(name)) {
                        return;
                    }
                    recognizedSet.add(name);
                    const item = document.createElement("li");
                    item.className = "list-group-item list-group-item-success";
                    item.textContent = name;
                    listEl.prepend(item);
                });
                setStatus(`Marked present: ${payload.recognized.join(", ")}`, "success");
            } else {
                setStatus(payload.message || "No match yet.", "secondary");
            }
        } catch (err) {
            setStatus("Network error while recognizing.", "danger");
        }
    };

    const startCamera = async scheduleId => {
        activeScheduleId = scheduleId;
        recognizedSet.clear();
        listEl.innerHTML = "";
        setStatus("Starting camera...", "secondary");
        modal.show();

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            setStatus("Camera API not available. Use HTTPS or localhost.", "danger");
            return;
        }

        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = stream;
            await video.play();
            setStatus("Recognition running...", "secondary");
            captureTimer = setInterval(captureAndSend, 2000);
        } catch (err) {
            setStatus("Unable to access the camera.", "danger");
        }
    };

    document.querySelectorAll(".start-camera").forEach(button => {
        button.addEventListener("click", () => {
            const scheduleId = button.dataset.scheduleId;
            if (!scheduleId) {
                setStatus("Missing schedule id.", "danger");
                return;
            }
            startCamera(scheduleId);
        });
    });

    modalEl.addEventListener("hidden.bs.modal", stopCamera);
})();
