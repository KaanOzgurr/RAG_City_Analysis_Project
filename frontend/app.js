const chatBox = document.getElementById("chatBox");
const queryInput = document.getElementById("queryInput");
const sendBtn = document.getElementById("sendBtn");
const catButtons = document.querySelectorAll(".cat-btn");

let selectedCategory = "";
let messageCounter = 0;

catButtons.forEach(btn => {
    btn.addEventListener("click", () => {
        catButtons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        selectedCategory = btn.dataset.cat;
    });
});

function addMessage(text, sender, sources = [], msgId = null) {
    const div = document.createElement("div");
    div.className = `message ${sender}`;
    div.textContent = text;

    if (sources.length > 0) {
        const srcDiv = document.createElement("div");
        srcDiv.className = "sources";
        srcDiv.textContent = "Kaynak: " + sources.join(", ");
        div.appendChild(srcDiv);
    }

    if (sender === "assistant" && msgId !== null) {
        const fbDiv = document.createElement("div");
        fbDiv.className = "feedback";

        const upBtn = document.createElement("button");
        upBtn.textContent = "👍";
        const downBtn = document.createElement("button");
        downBtn.textContent = "👎";

        upBtn.addEventListener("click", () => sendFeedback(msgId, "up", upBtn, downBtn));
        downBtn.addEventListener("click", () => sendFeedback(msgId, "down", upBtn, downBtn));

        fbDiv.appendChild(upBtn);
        fbDiv.appendChild(downBtn);
        div.appendChild(fbDiv);
    }

    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendFeedback(msgId, value, upBtn, downBtn) {
    upBtn.classList.remove("selected");
    downBtn.classList.remove("selected");
    if (value === "up") upBtn.classList.add("selected");
    if (value === "down") downBtn.classList.add("selected");

    try {
        await fetch("http://localhost:8000/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message_id: msgId, value: value })
        });
    } catch (err) {
        console.error("Geri bildirim gonderilemedi:", err);
    }
}

async function sendQuery() {
    const query = queryInput.value.trim();
    if (!query) return;

    addMessage(query, "user");
    queryInput.value = "";
    sendBtn.disabled = true;
    sendBtn.textContent = "Düşünüyor...";

    try {
        const response = await fetch("http://localhost:8000/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: query, category: selectedCategory || null })
        });

        const data = await response.json();
        messageCounter++;
        addMessage(data.answer, "assistant", data.sources || [], messageCounter);
    } catch (err) {
        addMessage("Bağlantı hatası: " + err.message, "assistant");
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = "Sor";
    }
}

sendBtn.addEventListener("click", sendQuery);
queryInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendQuery();
});