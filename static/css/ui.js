// Button click ripple (subtle effect)
document.addEventListener("click", e => {
    if (e.target.tagName === "BUTTON") {
        e.target.style.transform = "scale(0.96)";
        setTimeout(() => {
            e.target.style.transform = "scale(1)";
        }, 120);
    }
});
