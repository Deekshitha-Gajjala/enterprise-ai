import { useEffect, useRef, useState } from "react";
import Login from "./Login";
import "./App.css";

const API = "/api";

function App() {
  const [user, setUser] = useState(() => {
  const savedUser =
    localStorage.getItem("enterprise_ai_user");

  return savedUser
    ? JSON.parse(savedUser)
    : null;
});

const [isAuthenticated, setIsAuthenticated] =
  useState(() => {
    return Boolean(
      localStorage.getItem(
        "enterprise_ai_token"
      )
    );
  });
  

const [documents, setDocuments] = useState([]);
const [selectedDocument, setSelectedDocument] = useState(null);
const [chats, setChats] = useState([]);
const [activeChat, setActiveChat] = useState(null);

  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [error, setError] = useState("");
  const [backendOnline, setBackendOnline] = useState(false);

  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // ============================================================
  // API REQUEST HELPER
  // ============================================================

  async function request(path, options = {}) {
    try {
      const response = await fetch(`${API}${path}`, options);

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.detail ||
            data.message ||
            `Request failed with status ${response.status}`
        );
      }

      return data;
    } catch (error) {
      if (error.name === "TypeError") {
        throw new Error(
          "Cannot connect to backend. Make sure FastAPI is running on port 8000."
        );
      }

      throw error;
    }
  }

  // ============================================================
  // AUTHENTICATION
  // ============================================================

  function handleLogin(loggedInUser) {
    setUser(loggedInUser);
    setIsAuthenticated(true);
  }

  function handleLogout() {
    localStorage.removeItem("enterprise_ai_token");
    localStorage.removeItem("enterprise_ai_user");
    setUser(null);
    setIsAuthenticated(false);
    setDocuments([]);
    setChats([]);
    setActiveChat(null);
    setSelectedDocument(null);
  }

  // ============================================================
  // GET DOCUMENT ID
  // ============================================================

  function getDocumentId(document) {
    if (!document) {
      return null;
    }

    /*
      First try the normal ID fields.
    */

    const directId =
      document.id ??
      document.document_id ??
      document._id ??
      document.uuid;

    if (
      directId !== undefined &&
      directId !== null &&
      String(directId).trim() !== ""
    ) {
      return String(directId);
    }

    /*
      Some older versions of the backend do not return `id`
      from GET /documents.

      In that case, the stored filename may look like:

      UUID_original_filename.pdf

      Example:

      8d722d1d-01b8-4b8a-9caa-cfdc1ed8a62b_module 1 notes.pdf

      Recover the UUID from that filename.
    */

    const filename = document.filename;

    if (filename) {
      const match = String(filename).match(
        /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/i
      );

      if (match) {
        return match[0];
      }
    }

    /*
      Last fallback.

      This is useful only if the backend DELETE endpoint
      accepts filename-based deletion.
    */

    if (filename) {
      return String(filename);
    }

    if (document.original_name) {
      return String(document.original_name);
    }

    return null;
  }

  // ============================================================
  // LOAD DOCUMENTS
  // ============================================================

  async function loadDocuments() {
    const data = await request("/documents");

    if (!Array.isArray(data)) {
      setDocuments([]);
      return;
    }

    const normalizedDocuments = data.map((document) => ({
      ...document,

      _deleteId: getDocumentId(document),
    }));

    console.log(
      "[DOCUMENTS] Loaded documents:",
      normalizedDocuments
    );

    setDocuments(normalizedDocuments);
  }

  // ============================================================
  // LOAD CHATS
  // ============================================================

  async function loadChats() {
    const data = await request("/chats");

    setChats(Array.isArray(data) ? data : []);

    if (!activeChat && data.length > 0) {
      const firstChat = await request(
        `/chats/${data[0].id}`
      );

      setActiveChat(firstChat);
    }
  }

  // ============================================================
  // CHECK BACKEND
  // ============================================================

  async function checkBackend() {
    try {
      await request("/health");

      setBackendOnline(true);

      return true;
    } catch {
      setBackendOnline(false);

      return false;
    }
  }

  // ============================================================
  // INITIAL LOAD
  // ============================================================

  useEffect(() => {
    async function initialize() {
      try {
        const online = await checkBackend();

        if (!online) {
          setError(
            "Backend is offline. Start FastAPI with: uvicorn backend.app.main:app --reload"
          );

          return;
        }

        await loadDocuments();

        await loadChats();
      } catch (error) {
        setError(error.message);
      }
    }

    initialize();
  }, []);

  // ============================================================
  // AUTO SCROLL
  // ============================================================

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [activeChat?.messages, loading]);

  // ============================================================
  // CREATE NEW CHAT
  // ============================================================

  async function createNewChat() {
    try {
      setError("");

      const chat = await request("/chats", {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          title: "New chat",
        }),
      });

      setChats((previous) => [
        chat,
        ...previous,
      ]);

      setActiveChat(chat);

      setQuestion("");
    } catch (error) {
      setError(error.message);
    }
  }

  // ============================================================
  // OPEN CHAT
  // ============================================================

  async function openChat(chatId) {
    try {
      setError("");

      const chat = await request(
        `/chats/${chatId}`
      );

      setActiveChat(chat);
    } catch (error) {
      setError(error.message);
    }
  }

  // ============================================================
  // DELETE CHAT
  // ============================================================

  async function deleteChat(chatId, event) {
    event?.stopPropagation();

    const confirmed = window.confirm(
      "Are you sure you want to delete this conversation?"
    );

    if (!confirmed) {
      return;
    }

    try {
      setError("");

      await request(
        `/chats/${chatId}`,
        {
          method: "DELETE",
        }
      );

      const remainingChats = chats.filter(
        (chat) => chat.id !== chatId
      );

      setChats(remainingChats);

      if (activeChat?.id === chatId) {
        if (remainingChats.length > 0) {
          const nextChat = await request(
            `/chats/${remainingChats[0].id}`
          );

          setActiveChat(nextChat);
        } else {
          setActiveChat(null);
        }
      }
    } catch (error) {
      setError(error.message);
    }
  }

  // ============================================================
  // UPLOAD PDF
  // ============================================================

  async function uploadPDF(event) {
    const file = event.target.files?.[0];

    event.target.value = "";

    if (!file) {
      return;
    }

    if (
      !file.name
        .toLowerCase()
        .endsWith(".pdf")
    ) {
      setError("Please select a PDF file.");

      return;
    }

    try {
      setUploading(true);

      setError("");

      const formData = new FormData();

      formData.append("file", file);

      const result = await request(
        "/documents/upload",
        {
          method: "POST",
          body: formData,
        }
      );

      console.log(
        "[UPLOAD] Result:",
        result
      );

      await loadDocuments();
    } catch (error) {
      console.error(
        "[UPLOAD] Error:",
        error
      );

      setError(error.message);
    } finally {
      setUploading(false);
    }
  }

  // ============================================================
  // DELETE PDF
  // ============================================================

  async function deleteDocument(document) {
    if (!document) {
      setError(
        "Unable to delete PDF: document information is missing."
      );

      return;
    }

    /*
      Use the normalized ID first.
    */

    const documentId =
      document._deleteId ??
      getDocumentId(document);

    console.log(
      "[DELETE PDF] Document object:",
      document
    );

    console.log(
      "[DELETE PDF] Delete ID:",
      documentId
    );

    /*
      Never send /undefined.
    */

    if (
      documentId === undefined ||
      documentId === null ||
      String(documentId).trim() === ""
    ) {
      setError(
        "Unable to delete PDF because its ID could not be found."
      );

      return;
    }

    const filename =
      document.original_name ||
      document.filename ||
      "this PDF";

    const confirmed = window.confirm(
      `Delete "${filename}" and remove it from document search?`
    );

    if (!confirmed) {
      return;
    }

    try {
      setError("");

      const encodedId = encodeURIComponent(
        String(documentId)
      );

      console.log(
        "[DELETE PDF] Sending request:",
        `/documents/${encodedId}`
      );

      /*
        IMPORTANT:
        Send the actual document identifier.
      */

      await request(
        `/documents/${encodedId}`,
        {
          method: "DELETE",
        }
      );

      /*
        Remove immediately from frontend.
      */

      setDocuments((previous) =>
        previous.filter((item) => {
          const itemId =
            item._deleteId ??
            getDocumentId(item);

          return (
            String(itemId) !==
            String(documentId)
          );
        })
      );

      /*
        Reload from backend so frontend and backend
        remain synchronized.
      */

      await loadDocuments();

      console.log(
        "[DELETE PDF] Successfully deleted:",
        documentId
      );
    } catch (error) {
      console.error(
        "[DELETE PDF] Delete failed:",
        error
      );

      setError(
        error.message ||
          "Failed to delete the PDF."
      );
    }
  }

  // ============================================================
  // SEND MESSAGE
  // ============================================================

  async function sendMessage(event) {
    event?.preventDefault();

    const text = question.trim();

    if (!text || loading) {
      return;
    }

    try {
      setLoading(true);

      setError("");

      let chat = activeChat;

      // --------------------------------------------------------
      // CREATE CHAT IF NONE EXISTS
      // --------------------------------------------------------

      if (!chat) {
        chat = await request(
          "/chats",
          {
            method: "POST",

            headers: {
              "Content-Type": "application/json",
            },

            body: JSON.stringify({
              title: text.slice(0, 45),
            }),
          }
        );

        setChats((previous) => [
          chat,
          ...previous,
        ]);

        setActiveChat(chat);
      }

      // --------------------------------------------------------
      // SHOW USER MESSAGE IMMEDIATELY
      // --------------------------------------------------------

      const optimisticChat = {
        ...chat,

        messages: [
          ...(chat.messages || []),

          {
            role: "user",
            content: text,
            timestamp:
              new Date().toISOString(),
          },
        ],
      };

      setActiveChat(optimisticChat);

      setQuestion("");

      // --------------------------------------------------------
      // SEND TO BACKEND
      // --------------------------------------------------------

      const result = await request(
        "/ask",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
  question: text,
  chat_id: chat.id,
  mode: selectedDocument ? "document" : undefined,
  route: selectedDocument ? "document" : undefined,
  filename: selectedDocument || undefined,
}),
        }
      );

      // --------------------------------------------------------
      // LOAD UPDATED CHAT
      // --------------------------------------------------------

      const updatedChat =
        await request(
          `/chats/${result.chat_id}`
        );

      setActiveChat(updatedChat);

      // --------------------------------------------------------
      // UPDATE CHAT LIST
      // --------------------------------------------------------

      setChats((previous) =>
        previous.map((item) =>
          item.id === updatedChat.id
            ? {
                ...item,

                title:
                  updatedChat.title,

                updated_at:
                  updatedChat.updated_at,
              }
            : item
        )
      );
    } catch (error) {
      console.error(
        "[CHAT] Error:",
        error
      );

      setError(error.message);
    } finally {
      setLoading(false);
    }
  }

  // ============================================================
  // HANDLE ENTER
  // ============================================================

  function handleKeyDown(event) {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();

      sendMessage(event);
    }
  }

  const messages =
    activeChat?.messages || [];

  // ============================================================
  // LOGIN GATE
  // ============================================================

  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />;
  }

  // ============================================================
  // UI
  // ============================================================

  return (
    <div className="app-shell">

      {/* ======================================================
          SIDEBAR
      ====================================================== */}

      <aside className="sidebar">

        {/* BRAND */}

        <div className="brand">

          <div className="brand-icon">
            AI
          </div>

          <div>
            <strong>
              Enterprise AI
            </strong>

            <span>
              Document Assistant
            </span>
          </div>

        </div>

        {/* NEW CHAT */}

        <button
          className="new-chat"
          onClick={createNewChat}
        >
          + New chat
        </button>

        {/* ====================================================
            RECENT CHATS
        ==================================================== */}

        <section className="side-section">

          <div className="section-title">
            RECENT CHATS
          </div>

          <div className="chat-list">

            {chats.length === 0 && (
              <div className="empty-side">
                No recent chats
              </div>
            )}

            {chats.map((chat) => (

              <div
                key={chat.id}
                className={`chat-row ${
                  activeChat?.id ===
                  chat.id
                    ? "active"
                    : ""
                }`}
                onClick={() =>
                  openChat(chat.id)
                }
              >

                <span className="chat-symbol">
                  ◌
                </span>

                <span className="chat-title">
                  {chat.title ||
                    "New chat"}
                </span>

                <button
                  className="delete-small"
                  title="Delete conversation"
                  onClick={(event) =>
                    deleteChat(
                      chat.id,
                      event
                    )
                  }
                >
                  ×
                </button>

              </div>

            ))}

          </div>

        </section>

        {/* ====================================================
            DOCUMENTS
        ==================================================== */}

        <section className="side-section documents-section">

  <div className="section-title">
    DOCUMENTS
  </div>

  {selectedDocument && (
    <div className="selected-document">
      📄 Using: <strong>{selectedDocument}</strong>

      <button
        type="button"
        onClick={() => setSelectedDocument(null)}
      >
        ×
      </button>
    </div>
  )}

  {documents.map(
    (document) => {

              const documentId =
                document._deleteId ??
                getDocumentId(document);

              return (
                <div
  className={`document-card ${
    selectedDocument ===
    (document.filename || document.original_name)
      ? "selected"
      : ""
  }`}
  key={
    documentId ||
    document.filename ||
    document.original_name
  }
  onClick={() =>
    setSelectedDocument(
      selectedDocument ===
        (document.filename || document.original_name)
        ? null
        : document.filename || document.original_name
    )
  }
>

                  <div className="pdf-icon">
                    PDF
                  </div>

                  <div className="document-info">

                    <strong
                      title={
                        document.original_name ||
                        document.filename ||
                        "PDF"
                      }
                    >
                      {document.original_name ||
                        document.filename ||
                        "PDF"}
                    </strong>

                    <span>
                      {document.indexed
                        ? "Document indexed"
                        : "Not indexed"}
                    </span>

                  </div>

                  <button
                    className="document-delete"
                    title="Delete PDF"
                    onClick={() =>
                      deleteDocument(
                        document
                      )
                    }
                  >
                    ×
                  </button>

                </div>
              );
            }
          )}

          {/* UPLOAD BUTTON */}

          <button
            className="upload-button"
            onClick={() =>
              fileInputRef.current?.click()
            }
            disabled={uploading}
          >
            {uploading
              ? "Indexing PDF..."
              : "+ Upload PDF"}
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            hidden
            onChange={uploadPDF}
          />

        </section>

        {/* FOOTER */}

        <div className="sidebar-footer">

          <span>
            Enterprise RAG
          </span>

          <span>
            v4.0
          </span>

        </div>

      </aside>

      {/* ======================================================
          MAIN
      ====================================================== */}

      <main className="main">

        {/* HEADER */}

        <header className="topbar">

          <button
            className="menu-button"
            aria-label="Menu"
          >
            ☰
          </button>

          <div>

            <h1>
              Document Assistant
            </h1>

            <p>
              Ask questions and have a
              conversation with your AI
              assistant.
            </p>

          </div>

          <div className="topbar-actions">

            <div
              className={`status ${
                backendOnline
                  ? "online"
                  : "offline"
              }`}
            >

              <span />

              {backendOnline
                ? "System Online"
                : "Backend Offline"}

            </div>

            {user && (
              <button
                type="button"
                className="logout-button"
                onClick={handleLogout}
                title={`Logged in as ${user.email || "user"}`}
              >
                Logout
              </button>
            )}

          </div>

        </header>

        {/* ERROR */}

        {error && (

          <div className="error-banner">

            <span>
              {error}
            </span>

            <button
              onClick={() =>
                setError("")
              }
            >
              ×
            </button>

          </div>

        )}

        {/* ====================================================
            CONVERSATION
        ==================================================== */}

        <div className="conversation">

          {messages.length === 0 ? (

            <div className="welcome">

              <div className="welcome-icon">
                AI
              </div>

              <h2>
                How can I help you?
              </h2>

              <p>
                Talk to me normally, or ask
                questions about your uploaded
                PDFs.
              </p>

              <div className="welcome-pills">

                <span>
                  💬 Normal conversation
                </span>

                <span>
                  📄 PDF questions
                </span>

                <span>
                  🔎 Document search
                </span>

              </div>

              <div className="document-count">

                {documents.length}{" "}

                {documents.length === 1
                  ? "document"
                  : "documents"}{" "}

                available

              </div>

            </div>

          ) : (

            <div className="message-list">

              {messages.map(
                (message, index) => (

                  <div
                    key={`${
                      message.timestamp ||
                      "message"
                    }-${index}`}
                    className={`message-row ${
                      message.role
                    }`}
                  >

                    {/* AI AVATAR */}

                    {message.role ===
                      "assistant" && (

                      <div className="avatar">
                        AI
                      </div>

                    )}

                    <div className="message-content">

                      <div className="message-label">

                        {message.role ===
                        "user"
                          ? "You"
                          : "Enterprise AI"}

                      </div>

                      <div className="message-bubble">

                        {message.content}

                      </div>

                      {/* SOURCES */}

                      {message.role ===
                        "assistant" &&
                        message.sources?.length >
                          0 && (

                        <div className="sources">

                          <div className="sources-title">
                            📚 Sources
                          </div>

                          {message.sources.map(
                            (
                              source,
                              sourceIndex
                            ) => (

                              <div
                                className="source"
                                key={`${
                                  source.filename
                                }-${
                                  source.page
                                }-${
                                  sourceIndex
                                }`}
                              >

                                <strong>

                                  {source.filename}

                                  {source.page
                                    ? ` — page ${source.page}`
                                    : ""}

                                </strong>

                                <p>
                                  {source.text}
                                </p>

                              </div>

                            )
                          )}

                        </div>

                      )}

                    </div>

                  </div>

                )
              )}

              {/* TYPING */}

              {loading && (

                <div className="message-row assistant">

                  <div className="avatar">
                    AI
                  </div>

                  <div className="message-content">

                    <div className="message-label">
                      Enterprise AI
                    </div>

                    <div className="message-bubble typing">

                      <span />
                      <span />
                      <span />

                    </div>

                  </div>

                </div>

              )}

              <div
                ref={messagesEndRef}
              />

            </div>

          )}

        </div>

        {/* ====================================================
            COMPOSER
        ==================================================== */}

        <form
          className="composer"
          onSubmit={sendMessage}
        >

          <textarea
            value={question}
            onChange={(event) =>
              setQuestion(
                event.target.value
              )
            }
            onKeyDown={handleKeyDown}
            placeholder="Message Enterprise AI..."
            rows={1}
            disabled={loading}
          />

          <button
            type="submit"
            className="send-button"
            disabled={
              !question.trim() ||
              loading
            }
          >
            ↑
          </button>

          <div className="composer-help">
            Enter to send · Shift + Enter
            for a new line
          </div>

        </form>

      </main>

    </div>
  );
}

export default App;