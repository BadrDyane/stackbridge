import { useState, useEffect } from "react";
import "./App.css";

function App() {
  const [status, setStatus] = useState("Checking...");

  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "ok" && data.db === "ok") {
          setStatus("StackBridge API: OK");
        } else {
          setStatus(`API issue: ${JSON.stringify(data)}`);
        }
      })
      .catch(() => setStatus("StackBridge API: unreachable"));
  }, []);

  return (
    <div style={{ fontFamily: "monospace", padding: "2rem" }}>
      <h1>StackBridge</h1>
      <p>{status}</p>
    </div>
  );
}

export default App;