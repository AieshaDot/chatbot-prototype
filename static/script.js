let botMarkdownBuffer = "";
let typingIndex = 0;
let typingTimer = null;

function bindCannedQuestionEvents() {
  const chatInput = document.getElementById("chatInput");
  const submitBtn = document.getElementById("submitBtn");

  document.querySelectorAll(".question").forEach((btn) => {
    // 🔁 Remove any previous listener
    const newBtn = btn.cloneNode(true);
    btn.parentNode.replaceChild(newBtn, btn);

    newBtn.addEventListener("click", () => {
      chatInput.value = newBtn.textContent;

      // Let sendMessage run before resetting input
      submitBtn.click();

      setTimeout(() => {
        chatInput.value = "";
        chatInput.blur();
      }, 100);

      setTimeout(scrollToBottom, 400);
    });
  });
}

document.addEventListener("DOMContentLoaded", function () {
  const chatInput = document.getElementById("chatInput");
  const submitBtn = document.getElementById("submitBtn");

    // Enter key submits message
    chatInput.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });

    // Submit button
    submitBtn.addEventListener("click", function () {
      sendMessage();
    });

      // Canned questions
      bindCannedQuestionEvents();

      const clearBtn = document.getElementById("clearChat");
      if (clearBtn) {
        clearBtn.addEventListener("click", function (e) {
          e.preventDefault();
          window.location.reload();  // 🔁 reloads the full page
        });
      }
    });


async function sendMessage(optionalMessage = null) {
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
      // const response = await fetch("/chat", {
      const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // body: JSON.stringify({ message }),
      //body: JSON.stringify({ query: message }),
      body: JSON.stringify({ message: message }),
    });

    if (!response.ok || !response.body) {
      throw new Error("Network response was not ok.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let chunk;

    // Clear previous bot message placeholder
    createBotMessagePlaceholder();

    while (!(chunk = await reader.read()).done) {
      const text = decoder.decode(chunk.value, { stream: true });
      botMarkdownBuffer += text;
      restartTyping();
    }
    // ✅ Ensure scroll AFTER bot message is fully streamed
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
        const parsed = marked.parse(text);  // ✅ Markdown to HTML
        messageElem.innerHTML = `
           <div class="message-text">${marked.parse(text)}</div>
             <div class="copy-btn-container">
             <button class="copy-btn" aria-label="Copy to clipboard">
                <i class="fa fa-copy"></i>
             <span>Copy</span>
             </button>
          </div>
        `;
      } else {
        messageElem.innerText = text;
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
    // botBubble.innerHTML = marked.parse(currentText);
    botBubble.innerHTML = marked.parse(botMarkdownBuffer);
    botBubble.scrollTop = botBubble.scrollHeight;


    typingIndex++;
    typingTimer = setTimeout(typeNextChunk, 15); // ⏱️ Adjust typing speed here

    // ✅ scroll every few chunks
    if (typingIndex % 5 === 0) scrollToBottom();
  } else {
    scrollToBottom();
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

function scrollToBottom() {
  const chatWindow = document.getElementById("chatWindow");
  if (chatWindow) {
    chatWindow.scrollTo({ top: chatWindow.scrollHeight, behavior: "smooth" });
  }
}

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

// Option A: classic check
const uploadForm = document.getElementById("uploadForm");
if (uploadForm) {
  uploadForm.addEventListener("submit", async function (e) {
    e.preventDefault();                         // don’t forget this
    const formData = new FormData(this);

    try {
      const response = await fetch("/upload-doc", {
        method: "POST",
        body: formData,
      });
      const result = await response.json();
      const statusEl = document.getElementById("uploadStatus");
      if (statusEl) statusEl.innerText = result.message || result.error;
    } catch (err) {
      console.error("Upload failed:", err);
    }
  }); // closes addEventListener
}    // closes the if(uploadForm)

window.addEventListener("load", () => {
  const chatWindow = document.getElementById("chatWindow");
  if (chatWindow) {
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }
});

function ensureChatScrollOnResize() {
  const chatWindow = document.getElementById("chatWindow");
  if (chatWindow) {
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }
}

window.addEventListener("resize", ensureChatScrollOnResize);
window.addEventListener("orientationchange", ensureChatScrollOnResize);