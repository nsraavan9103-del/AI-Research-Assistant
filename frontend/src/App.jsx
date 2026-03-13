// ============================================================
// AI Research Assistant — frontend/src/App.js
// Fixed: API URL from env, proper error handling, streaming support
// Compatible: Windows 10, React 18, Node 18 LTS
// ============================================================

import React, { useState, useRef, useEffect } from "react";
import "./App.css";

// FIX: Use environment variable — create frontend/.env with:
// REACT_APP_API_URL=http://localhost:8000
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ── API Helper ────────────────────────────────────────────────
async function apiCall(endpoint, options = {}, token = null) {
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${endpoint}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Auth Context ──────────────────────────────────────────────
function useAuth() {
  const [token, setToken] = useState(() => localStorage.getItem("auth_token"));
  const [user, setUser] = useState(null);

  useEffect(() => {
    if (token) {
      apiCall("/users/me", {}, token)
        .then(setUser)
        .catch(() => { setToken(null); localStorage.removeItem("auth_token"); });
    }
  }, [token]);

  const login = async (username, password) => {
    const body = new URLSearchParams({ username, password });
    const res = await fetch(`${API_URL}/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString()
    });
    if (!res.ok) throw new Error("Invalid credentials");
    const data = await res.json();
    localStorage.setItem("auth_token", data.access_token);
    setToken(data.access_token);
  };

  const register = async (username, email, password) => {
    await apiCall("/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password })
    });
    await login(username, password);
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    setToken(null);
    setUser(null);
  };

  return { token, user, login, register, logout };
}

// ── Auth Screen ───────────────────────────────────────────────
function AuthScreen({ onLogin, onRegister }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") await onLogin(username, password);
      else await onRegister(username, email, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1 className="app-title">🔬 AI Research Assistant</h1>
        <p className="app-subtitle">Powered by Ollama + phi3 — runs fully locally</p>

        <div className="tab-row">
          <button className={`tab ${mode === "login" ? "active" : ""}`} onClick={() => setMode("login")}>Login</button>
          <button className={`tab ${mode === "register" ? "active" : ""}`} onClick={() => setMode("register")}>Register</button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <input className="input" placeholder="Username" value={username}
            onChange={e => setUsername(e.target.value)} required />
          {mode === "register" && (
            <input className="input" type="email" placeholder="Email" value={email}
              onChange={e => setEmail(e.target.value)} required />
          )}
          <input className="input" type="password" placeholder="Password" value={password}
            onChange={e => setPassword(e.target.value)} required />
          {error && <p className="error-msg">{error}</p>}
          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? "Please wait…" : mode === "login" ? "Login" : "Create Account"}
          </button>
        </form>
      </div>
    </div>
  );
}

// ── Upload Panel ──────────────────────────────────────────────
function UploadPanel({ token, onSessionCreated }) {
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const fileRef = useRef(null);

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const ALLOWED = [".pdf", ".docx", ".xlsx", ".xls", ".txt"];
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
    if (!ALLOWED.includes(ext)) {
      setError(`Unsupported file type. Allowed: PDF, DOCX, XLSX, TXT`);
      return;
    }

    setError("");
    setStatus("Uploading and indexing…");
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_URL}/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }

      const data = await res.json();
      setStatus(`✅ Indexed ${data.chunks_indexed} chunks from "${data.filename}"`);
      onSessionCreated(data.session_id, data.filename);
    } catch (err) {
      setError(err.message);
      setStatus("");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div className="upload-panel">
      <h3>📄 Upload Research Document</h3>
      <label className={`upload-btn ${uploading ? "disabled" : ""}`}>
        {uploading ? "Processing…" : "Choose File"}
        <input ref={fileRef} type="file" accept=".pdf,.docx,.xlsx,.xls,.txt" onChange={handleUpload}
          disabled={uploading} style={{ display: "none" }} />
      </label>
      {status && <p className="status-msg">{status}</p>}
      {error && <p className="error-msg">{error}</p>}
    </div>
  );
}

// ── Chat Panel ────────────────────────────────────────────────
function ChatPanel({ token, sessionId, docName, model }) {
  const [messages, setMessages] = useState([
    { role: "assistant", text: `Document "${docName}" loaded. Ask me anything about it!` }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", text: question }]);
    setLoading(true);

    // Streaming: show tokens as they arrive
    const assistantMsgId = Date.now();
    setMessages(prev => [...prev, { id: assistantMsgId, role: "assistant", text: "" }]);

    try {
      const res = await fetch(`${API_URL}/ask/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ question, session_id: sessionId, model })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Request failed");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let fullText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        fullText += decoder.decode(value, { stream: true });
        setMessages(prev => prev.map(m =>
          m.id === assistantMsgId ? { ...m, text: fullText } : m
        ));
      }
    } catch (err) {
      setMessages(prev => prev.map(m =>
        m.id === assistantMsgId
          ? { ...m, text: `❌ Error: ${err.message}` }
          : m
      ));
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span>💬 Chat with: <strong>{docName}</strong></span>
      </div>
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={msg.id || i} className={`message ${msg.role}`}>
            <span className="role-label">{msg.role === "user" ? "You" : "AI"}</span>
            <p>{msg.text || <span className="typing">▋</span>}</p>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="chat-input-row">
        <textarea
          className="chat-input"
          rows={2}
          placeholder="Ask a question about the paper… (Enter to send)"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button className="btn-send" onClick={sendMessage} disabled={loading || !input.trim()}>
          {loading ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────
export default function App() {
  const { token, user, login, register, logout } = useAuth();
  const [session, setSession] = useState(null); // { id, name }
  const [ollamaOk, setOllamaOk] = useState(null);
  const [models, setModels] = useState(["qwen2.5:3b", "phi3:mini"]);
  const [selectedModel, setSelectedModel] = useState("qwen2.5:3b");

  // Check Ollama health and fetch available models on mount
  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then(r => r.json())
      .then(d => setOllamaOk(d.ollama))
      .catch(() => setOllamaOk(false));

    // Fetch available models from Ollama directly
    fetch("http://localhost:11434/api/tags")
      .then(r => r.json())
      .then(data => {
        const names = (data.models || []).map(m => m.name);
        if (names.length > 0) {
          setModels(names);
          // Default to qwen2.5:3b if available, otherwise first model
          const preferred = names.find(n => n.startsWith("qwen2.5:3b")) ||
                            names.find(n => n.startsWith("qwen2.5")) ||
                            names[0];
          setSelectedModel(preferred);
        }
      })
      .catch(() => {}); // silently keep defaults if Ollama not reachable
  }, []);

  if (!token) {
    return <AuthScreen onLogin={login} onRegister={register} />;
  }

  return (
    <div className="app-layout">
      <header className="app-header">
        <span className="header-title">🔬 AI Research Assistant</span>
        <div className="header-right">
          {ollamaOk === false && (
            <span className="ollama-warning">⚠️ Ollama offline — run: ollama serve</span>
          )}
          {ollamaOk === true && <span className="ollama-ok">● Ollama online</span>}

          {/* ── Model Switcher ── */}
          <div className="model-switcher">
            <label htmlFor="model-select" className="model-label">🤖 Model:</label>
            <select
              id="model-select"
              className="model-select"
              value={selectedModel}
              onChange={e => setSelectedModel(e.target.value)}
            >
              {models.map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>

          <span className="user-name">👤 {user?.username}</span>
          <button className="btn-logout" onClick={logout}>Logout</button>
        </div>
      </header>

      <main className="app-main">
        <div className="left-panel">
          <UploadPanel
            token={token}
            onSessionCreated={(id, name) => setSession({ id, name })}
          />
        </div>
        <div className="right-panel">
          {session ? (
            <ChatPanel token={token} sessionId={session.id} docName={session.name} model={selectedModel} />
          ) : (
            <div className="empty-state">
              <p>⬅️ Upload a document to get started</p>
              <small>Active model: {selectedModel}</small>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
