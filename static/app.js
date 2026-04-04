// app.js — RecAPI Frontend

// ── COPY TO CLIPBOARD ──
function copyKey(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast("API key copied to clipboard!");
  });
}

function copyCode(btn) {
  const pre = btn.closest(".code-block").querySelector("pre");
  navigator.clipboard.writeText(pre.innerText).then(() => {
    const original = btn.innerText;
    btn.innerText = "Copied!";
    setTimeout(() => btn.innerText = original, 2000);
  });
}

// ── SHOW / HIDE API KEY ──
function toggleKey(fullKey) {
  const el  = document.getElementById("api-key-masked");
  const btn = el.nextElementSibling;
  if (btn.innerText === "Show") {
    el.innerText = fullKey;
    btn.innerText = "Hide";
  } else {
    el.innerText = fullKey.slice(0, 8) + "••••••••••••••••••••••••";
    btn.innerText = "Show";
  }
}

// ── LANGUAGE SWITCHER ──
function switchLang(lang, clickedBtn) {
  // Update active tab
  document.querySelectorAll(".lang-tab").forEach(
    btn => btn.classList.remove("active")
  );
  clickedBtn.classList.add("active");

  // Show matching code blocks, hide others
  document.querySelectorAll(".code-block").forEach(block => {
    if (block.classList.contains(`lang-${lang}`)) {
      block.style.display = "block";
    } else {
      // Only hide if it belongs to a language class
      const hasLangClass = [...block.classList].some(
        c => c.startsWith("lang-")
      );
      if (hasLangClass) block.style.display = "none";
    }
  });
}

// ── FILE UPLOAD — show filename ──
function showFileName(input) {
  const label = document.getElementById("file-name");
  if (input.files && input.files[0]) {
    label.innerText = input.files[0].name;
  }
}

// ── DRAG AND DROP ──
const uploadZone = document.getElementById("upload-zone");
if (uploadZone) {
  uploadZone.addEventListener("dragover", e => {
    e.preventDefault();
    uploadZone.style.borderColor = "var(--accent)";
  });
  uploadZone.addEventListener("dragleave", () => {
    uploadZone.style.borderColor = "";
  });
  uploadZone.addEventListener("drop", e => {
    e.preventDefault();
    uploadZone.style.borderColor = "";
    const file = e.dataTransfer.files[0];
    if (file) {
      const input = document.getElementById("file-input");
      const dt    = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      document.getElementById("file-name").innerText = file.name;
    }
  });
}

// ── TOAST NOTIFICATION ──
function showToast(message) {
  const toast = document.createElement("div");
  toast.className = "flash flash-success";
  toast.style.cssText = `
    position: fixed; bottom: 24px; right: 24px;
    z-index: 999; animation: slideIn 0.2s ease;
  `;
  toast.innerHTML = `${message}
    <span class="flash-close"
          onclick="this.parentElement.remove()">×</span>`;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// ── AUTO DISMISS FLASH MESSAGES ──
setTimeout(() => {
  document.querySelectorAll(".flash").forEach(el => el.remove());
}, 5000);