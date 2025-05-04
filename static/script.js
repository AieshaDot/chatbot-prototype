let botMarkdownBuffer = "";
let typingIndex = 0;
let typingTimer = null;

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
  document.querySelectorAll(".question").forEach((btn) => {
    btn.addEventListener("click", () => {
      chatInput.value = btn.textContent;
      sendMessage();
    });
  });

  // Clear chat
  const clearBtn = document.getElementById("clearChat");
  if (clearBtn) {
    clearBtn.addEventListener("click", function (e) {
      e.preventDefault();
      const chatWindow = document.getElementById("chatWindow");
      chatWindow.innerHTML = "";
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
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
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
    messageElem.innerHTML = text;
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
    messageElem.innerHTML = "";
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
  const botBubble = document.querySelector(".message.bot:last-of-type");
  if (!botBubble) return;

  if (typingIndex <= botMarkdownBuffer.length) {
    const currentText = botMarkdownBuffer.slice(0, typingIndex);
    botBubble.innerHTML = marked.parse(currentText);
    botBubble.scrollTop = botBubble.scrollHeight;

    typingIndex++;
    typingTimer = setTimeout(typeNextChunk, 15); // ⏱️ Adjust typing speed here
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const main = document.querySelector('.home-wrapper .main');
  if (main) {
    main.style.marginLeft = '240px';
  }
});

window.addEventListener("load", () => {
  document.body.classList.add("ready");
});

function enforceMainLayout() {
  const main = document.querySelector('.home-wrapper .main');
  if (main && main.style.marginLeft !== '240px') {
    main.style.marginLeft = '240px';
  }
}

window.addEventListener('load', enforceMainLayout);
window.addEventListener('resize', enforceMainLayout);

function scrollToBottom() {
  const chatWindow = document.getElementById("chatWindow");
  if (chatWindow) {
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }
}