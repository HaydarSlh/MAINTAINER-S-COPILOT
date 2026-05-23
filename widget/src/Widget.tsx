import { useEffect, useRef, useState } from "react";
import { streamChat, fetchHistory } from "./api";
import type { WidgetConfig } from "./api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Props {
  config: WidgetConfig;
  widgetId: string;
}

const STORAGE_KEY = (widgetId: string) => `copilot:conv:${widgetId}`;

// Embeddable chat widget rendered inside the host-page iframe.
export function Widget({ config, widgetId }: Props) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [convId, setConvId] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const primary = config.theme?.primary ?? "#6366f1";

  // Restore conversation_id from localStorage on mount + load past messages
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY(widgetId));
    if (saved) {
      setConvId(saved);
      fetchHistory(widgetId, saved)
        .then((history) => {
          if (history.length > 0) setMessages(history);
        })
        .catch(() => {});
    }
  }, [widgetId]);

  // Persist conversation_id whenever it changes
  useEffect(() => {
    if (convId) localStorage.setItem(STORAGE_KEY(widgetId), convId);
  }, [convId, widgetId]);

  useEffect(() => {
    // Tell the host page to resize the iframe whenever open state changes
    window.parent.postMessage({ type: "copilot:resize", open }, "*");
  }, [open]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  // Clear the stored conversation and show the greeting message.
  function startNewChat() {
    localStorage.removeItem(STORAGE_KEY(widgetId));
    setConvId(null);
    setMessages([{ role: "assistant", content: config.greeting }]);
  }

  // Send the current input to the chat API and stream the assistant reply into the message list.
  async function send() {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setStreaming(true);

    let reply = "";
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      for await (const chunk of streamChat(widgetId, text, convId)) {
        if (chunk === "[DONE]") break;
        if (chunk.startsWith("[conv:") && chunk.endsWith("]")) {
          setConvId(chunk.slice(6, -1));
          continue;
        }
        reply += chunk;
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { role: "assistant", content: reply };
          return next;
        });
      }
    } catch (err) {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          role: "assistant",
          content: `Error: ${err instanceof Error ? err.message : String(err)}`,
        };
        return next;
      });
    } finally {
      setStreaming(false);
    }
  }

  // Bubble (collapsed)
  if (!open) {
    return (
      <div ref={rootRef} style={{ position: "fixed", bottom: 24, right: 24 }}>
        <button
          onClick={() => {
            setOpen(true);
            if (messages.length === 0) {
              setMessages([{ role: "assistant", content: config.greeting }]);
            }
          }}
          style={{
            width: 56, height: 56, borderRadius: "50%", border: "none",
            background: primary, color: "#fff", fontSize: 24,
            cursor: "pointer", boxShadow: "0 4px 12px rgba(0,0,0,0.25)",
          }}
          aria-label="Open copilot"
        >
          💬
        </button>
      </div>
    );
  }

  // Expanded panel
  return (
    <div
      ref={rootRef}
      style={{
        display: "flex", flexDirection: "column",
        height: "100%", width: "100%",
        fontFamily: "system-ui, sans-serif",
        fontSize: 14, background: "#fff",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          background: primary, color: "#fff", padding: "12px 16px",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          flexShrink: 0,
        }}
      >
        <span style={{ fontWeight: 600 }}>Maintainer's Copilot</span>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            onClick={startNewChat}
            style={{
              background: "rgba(255,255,255,0.18)", border: "none", color: "#fff",
              cursor: "pointer", fontSize: 12, padding: "4px 8px", borderRadius: 6,
            }}
            aria-label="New chat"
            title="Start a new conversation"
          >
            New
          </button>
          <button
            onClick={() => setOpen(false)}
            style={{
              background: "none", border: "none", color: "#fff",
              cursor: "pointer", fontSize: 18, lineHeight: 1,
            }}
            aria-label="Close"
          >
            ×
          </button>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "12px 16px" }}>
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              marginBottom: 12,
              display: "flex",
              justifyContent: m.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            <div
              style={{
                maxWidth: "80%", padding: "8px 12px", borderRadius: 12,
                background: m.role === "user" ? primary : "#f3f4f6",
                color: m.role === "user" ? "#fff" : "#111",
                whiteSpace: "pre-wrap", wordBreak: "break-word",
              }}
            >
              {m.content || (streaming && i === messages.length - 1 ? "▌" : "")}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div
        style={{
          display: "flex", gap: 8, padding: "10px 16px",
          borderTop: "1px solid #e5e7eb", flexShrink: 0,
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="Ask a question…"
          disabled={streaming}
          style={{
            flex: 1, padding: "8px 12px", borderRadius: 8,
            border: "1px solid #d1d5db", outline: "none", fontSize: 14,
          }}
        />
        <button
          onClick={send}
          disabled={streaming || !input.trim()}
          style={{
            padding: "8px 16px", borderRadius: 8, border: "none",
            background: primary, color: "#fff", cursor: "pointer",
            opacity: streaming || !input.trim() ? 0.5 : 1,
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
