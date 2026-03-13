import './App.css';
import { useState } from "react";

const API = "http://localhost:8000";

function App() {
  const [token, setToken] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [file, setFile] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [history, setHistory] = useState([]);

  // NEW STATES
  const [uploading, setUploading] = useState(false);
  const [thinking, setThinking] = useState(false);

  const signup = async () => {
    const fd = new FormData();
    fd.append("email", email);
    fd.append("password", password);
    await fetch(`${API}/signup`, { method: "POST", body: fd });
    alert("Signup successful! Now login.");
  };

  const login = async () => {
    const fd = new FormData();
    fd.append("email", email);
    fd.append("password", password);
    const res = await fetch(`${API}/login`, { method: "POST", body: fd });
    const data = await res.json();
    setToken(data.token);
  };

  const upload = async () => {
    if (!file) return alert("Choose a file first!");
    setUploading(true);

    const fd = new FormData();
    fd.append("file", file);

    await fetch(`${API}/upload`, {
      method: "POST",
      body: fd,
      headers: { token }
    });

    setUploading(false);
    alert("File uploaded & indexed!");
  };


  return (
    <div style={{ padding: 20, fontFamily: "Arial", maxWidth: 600, margin: "auto" }}>
      <h2>AI Research Assistant</h2>

      {!token && (
        <>
          <h3>Signup</h3>
          <input placeholder="Email" onChange={e => setEmail(e.target.value)} />
          <input type="password" placeholder="Password" onChange={e => setPassword(e.target.value)} />
          <button onClick={signup}>Signup</button>

          <h3>Login</h3>
          <button onClick={login}>Login</button>
        </>
      )}

      {token && (
        <>
          <h3>Upload Document</h3>
          <input type="file" onChange={e => setFile(e.target.files[0])} />
          <button onClick={upload} disabled={uploading}>
            {uploading ? "Uploading..." : "Upload"}
          </button>

          {uploading && <div className="loader"></div>}

          <h3>Ask Question</h3>
          <input
            value={question}
            onChange={e => setQuestion(e.target.value)}
            placeholder="Ask..."
          />
          <button onClick={""} disabled={thinking}>
            {thinking ? "Thinking..." : "Ask"}
          </button>

          {thinking && <div className="loader"></div>}

          <p><b>Answer:</b> {thinking ? "Generating answer..." : answer}</p>

          <h3>Chat History</h3>
          {history.map(h => (
            <div key={h.id} style={{ borderBottom: "1px solid #ccc", marginBottom: 10 }}>
              <b>Q:</b> {h.question}<br />
              <b>A:</b> {h.answer}<br />
              <small>{new Date(h.time).toLocaleString()}</small>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

export default App;
