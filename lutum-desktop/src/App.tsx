/**
 * Lutum Veritas Desktop App
 * ==========================
 * Haupteinstiegspunkt der React-Anwendung.
 */

import { useEffect } from "react";
import { Chat } from "./components/Chat";
import "./App.css";

function App() {
  // Heartbeat: ping backend every 30s to keep idle timeout alive
  useEffect(() => {
    const interval = setInterval(() => {
      fetch("http://127.0.0.1:8420/health", { method: "GET" }).catch(() => {});
    }, 30_000);
    return () => clearInterval(interval);
  }, []);

  return <Chat />;
}

export default App;
