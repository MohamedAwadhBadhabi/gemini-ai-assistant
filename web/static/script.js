
const chatForm = document.getElementById("chat-form");
const promptInput = document.getElementById("prompt");
const messagesContainer = document.getElementById("messages");
const sendButton = document.getElementById("send-button");
const newChatButton = document.getElementById("new-chat-button");

// Conversation ID
let conversationId = null;


// =============================================
// 1. Configure Markdown
// =============================================

if (typeof marked !== "undefined") {
    marked.setOptions({
        breaks: true,
        gfm: true
    });
}


// =============================================
// 2. Render Assistant Message
// =============================================

function renderAssistantMessage(element, text) {

    if (
        typeof marked !== "undefined" &&
        typeof DOMPurify !== "undefined"
    ) {
        const html = marked.parse(text);
        element.innerHTML = DOMPurify.sanitize(html);
    } else {
        element.textContent = text;
    }
}


// =============================================
// 3. Add Message to Chat
// =============================================

function addMessage(text, sender) {

    const messageElement = document.createElement("div");

    messageElement.classList.add("message", sender);

    if (sender === "assistant") {
        renderAssistantMessage(messageElement, text);
    } else {
        messageElement.textContent = text;
    }

    messagesContainer.appendChild(messageElement);

    messagesContainer.scrollTop =
        messagesContainer.scrollHeight;

    return messageElement;
}


// =============================================
// 4. Adjust Textarea Height
// =============================================

function adjustTextareaHeight() {

    promptInput.style.height = "auto";

    const maxHeight = 180;

    promptInput.style.height =
        Math.min(promptInput.scrollHeight, maxHeight) + "px";
}


// =============================================
// 5. Start New Chat
// =============================================

function startNewChat() {

    conversationId = null;

    messagesContainer.innerHTML = "";

    addMessage(
        "Hello! I'm your AI assistant. How can I help you today?",
        "assistant"
    );

    promptInput.value = "";

    adjustTextareaHeight();

    promptInput.focus();
}


// =============================================
// 6. Send Message to Gemini
// =============================================

async function sendMessage(prompt) {

    addMessage(prompt, "user");

    const loadingMessage = addMessage(
        "Thinking...",
        "assistant"
    );

    sendButton.disabled = true;
    newChatButton.disabled = true;
    promptInput.disabled = true;

    try {

        const response = await fetch("/chat", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                prompt: prompt,
                conversation_id: conversationId
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Something went wrong."
            );
        }

        // Save the conversation ID returned by the server.
        conversationId = data.conversation_id;

        const responseText =
            data.response || "No response received.";

        renderAssistantMessage(
            loadingMessage,
            responseText
        );

    } catch (error) {

        loadingMessage.textContent =
            "Error: " + error.message;

        loadingMessage.classList.add("error");

    } finally {

        sendButton.disabled = false;
        newChatButton.disabled = false;
        promptInput.disabled = false;

        promptInput.focus();

        messagesContainer.scrollTop =
            messagesContainer.scrollHeight;
    }
}


// =============================================
// 7. Handle Form Submission
// =============================================

chatForm.addEventListener("submit", async function(event) {

    event.preventDefault();

    const prompt = promptInput.value.trim();

    if (!prompt || sendButton.disabled) {
        return;
    }

    promptInput.value = "";

    adjustTextareaHeight();

    await sendMessage(prompt);
});


// =============================================
// 8. Enter to Send, Shift + Enter for New Line
// =============================================

promptInput.addEventListener("keydown", function(event) {

    if (
        event.key === "Enter" &&
        !event.shiftKey &&
        !event.isComposing
    ) {
        event.preventDefault();

        chatForm.requestSubmit();
    }
});


// =============================================
// 9. Auto Resize Textarea
// =============================================

promptInput.addEventListener(
    "input",
    adjustTextareaHeight
);


// =============================================
// 10. New Chat Button
// =============================================

newChatButton.addEventListener(
    "click",
    startNewChat
);
