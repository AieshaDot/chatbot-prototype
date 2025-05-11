
let botMarkdownBuffer = "";
let typingIndex = 0;
let typingTimer = null;

function bindCannedQuestionEvents() {
  const chatInput = document.getElementById("chatInput");
  document.querySelectorAll(".question").forEach((btn) => {
    btn.addEventListener("click", () => {
      chatInput.value = btn.textContent;
      sendMessage();
      setTimeout(scrollToBottom, 400);
    });
  });
}

document.addEventListener("DOMContentLoaded", function () {
  const chatInput = document.getElementById("chatInput");
  const submitBtn = document.getElementById("submitBtn");

  chatInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  submitBtn.addEventListener("click", function () {
    sendMessage();
  });

  bindCannedQuestionEvents();

  const clearBtn = document.getElementById("clearChat");
  if (clearBtn) {
    clearBtn.addEventListener("click", function (e) {
      e.preventDefault();
      const chatWindow = document.getElementById("chatWindow");
      chatWindow.innerHTML = "";
      bindCannedQuestionEvents();  // rebind after clear
    });
  }
});

async function sendMessage() {
  const inputField = document.getElementById("chatInput");
  const message = inputField.value.trim();
  if (!message) return;

  appendMessage("user", message);
  scrollToBottom();
  document.getElementById("typingIndicator").style.display = "block";
  inputField.value = "";
  botMarkdownBuffer = "";
  typingIndex = 0;

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: message }),
    });

    if (!response.ok || !response.body) {
      throw new Error("Network response was not ok.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let chunk;

    createBotMessagePlaceholder();

    while (!(chunk = await reader.read()).done) {
      const text = decoder.decode(chunk.value, { stream: true });
      botMarkdownBuffer += text;
      restartTyping();
    }

    scrollToBottom();
  } catch (error) {
    console.error("Streaming fetch failed:", error);
    appendMessage("bot", "⚠️ Oops! Something went wrong.");
  }
}

function appendMessage(sender, text) {
  const chatWindow = document.getElementById("chatWindow");
  const messageElem = document.createElement("div");
  messageElem.classList.add("message", sender);

  if (sender === "bot") {
    const parsed = marked.parse(text);
    messageElem.innerHTML = `
      <div class="message-text">${parsed}</div>
      <div class="copy-btn-container">
        <button class="copy-btn" aria-label="Copy to clipboard">
          <i class="fa fa-copy"></i>
          <span>Copy</span>
        </button>
      </div>
    `;
  } else {
    messageElem.textContent = text;
  }

  chatWindow.appendChild(messageElem);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function createBotMessagePlaceholder() {
  let existing = document.querySelector(".message.bot:last-of-type");
  if (!existing) {
    const chatWindow = document.getElementById("chatWindow");
    const messageElem = document.createElement("div");
    messageElem.classList.add("message", "bot");
    messageElem.innerHTML = `
      <div class="message-text"></div>
      <button class="copy-btn" aria-label="Copy response">📋</button>
    `;
    chatWindow.appendChild(messageElem);
  }
}

function restartTyping() {
  if (typingTimer) clearTimeout(typingTimer);
  typeNextChunk();
  scrollToBottom();
  document.getElementById("typingIndicator").style.display = "none";
}

function typeNextChunk() {
  const botBubble = document.querySelector(".message.bot:last-of-type .message-text");
  if (!botBubble) return;

  if (typingIndex <= botMarkdownBuffer.length) {
    const currentText = botMarkdownBuffer.slice(0, typingIndex);
    botBubble.innerHTML = marked.parse(botMarkdownBuffer);
    botBubble.scrollTop = botBubble.scrollHeight;

    typingIndex++;
    typingTimer = setTimeout(typeNextChunk, 15);
    if (typingIndex % 5 === 0) scrollToBottom();
  } else {
    scrollToBottom();
  }
}

function scrollToBottom() {
  const chatWindow = document.getElementById("chatWindow");
  if (chatWindow) {
    chatWindow.scrollTo({ top: chatWindow.scrollHeight, behavior: "smooth" });
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const main = document.querySelector('.home-wrapper .main');
  if (main && window.innerWidth > 768) {
    main.style.marginLeft = '240px';
  }
  const hamburger = document.getElementById("hamburger");
  const sidebar = document.querySelector(".sidebar");
  const overlay = document.getElementById("sidebarOverlay");

  hamburger?.addEventListener("click", () => {
    sidebar.classList.toggle("sidebar-open");
    overlay.style.display = sidebar.classList.contains("sidebar-open") ? "block" : "none";
  });

  overlay?.addEventListener("click", () => {
    sidebar.classList.remove("sidebar-open");
    overlay.style.display = "none";
  });
});

window.addEventListener("load", () => {
  document.body.classList.add("ready");
});

function enforceMainLayout() {
  const main = document.querySelector('.home-wrapper .main');
  if (main) {
    if (window.innerWidth > 768) {
      main.style.marginLeft = '240px';
    } else {
      main.style.marginLeft = '0';
    }
  }
}

window.addEventListener('load', enforceMainLayout);
window.addEventListener('resize', enforceMainLayout);

document.addEventListener("click", function (e) {
  if (e.target.classList.contains("copy-btn")) {
    const messageDiv = e.target.previousElementSibling;
    if (messageDiv) {
      const text = messageDiv.innerText;
      navigator.clipboard.writeText(text).then(() => {
        e.target.textContent = "✅";
        setTimeout(() => (e.target.textContent = "📋"), 1000);
      });
    }
  }
});

document.getElementById("uploadForm")?.addEventListener("submit", async function (e) {
  e.preventDefault();
  const formData = new FormData(this);

  const response = await fetch("/upload-doc", {
    method: "POST",
    body: formData,
  });

  const result = await response.json();
  document.getElementById("uploadStatus").innerText = result.message || result.error;
});
