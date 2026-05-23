// Widget → FastAPI api client.
// API_BASE is injected at build time from the iframe's URL origin.

const API_BASE = window.location.origin.replace(":8080", ":8000");

export interface WidgetConfig {
  widget_id: string;
  theme: Record<string, string>;
  greeting: string;
  enabled_tools: string[];
}

// Fetch the public configuration for a widget by its ID.
export async function fetchConfig(widgetId: string): Promise<WidgetConfig> {
  const resp = await fetch(`${API_BASE}/embed/config/${widgetId}`);
  if (!resp.ok) throw new Error(`Config fetch failed: ${resp.status}`);
  return resp.json();
}

export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

// Load past messages for a conversation from the embed history endpoint.
export async function fetchHistory(
  widgetId: string,
  conversationId: string,
): Promise<HistoryMessage[]> {
  const resp = await fetch(
    `${API_BASE}/embed/history/${widgetId}/${conversationId}`,
  );
  if (!resp.ok) return [];
  const data = await resp.json();
  return data.messages || [];
}

// Stream SSE chunks from the embed chat endpoint, yielding each data line.
export async function* streamChat(
  widgetId: string,
  text: string,
  conversationId: string | null,
): AsyncGenerator<string> {
  const body: Record<string, unknown> = { text, widget_id: widgetId };
  if (conversationId) body.conversation_id = conversationId;

  const resp = await fetch(`${API_BASE}/embed/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
  });

  if (!resp.ok || !resp.body) throw new Error(`Chat request failed: ${resp.status}`);

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        yield line.slice(6);
      }
    }
  }
}
