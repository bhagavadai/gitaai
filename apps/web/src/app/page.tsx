"use client";

import { useState, useRef, useEffect } from "react";

const PIPELINE_URL = process.env.NEXT_PUBLIC_PIPELINE_URL || "http://localhost:8000";

interface Verse {
  verse_id: string;
  chapter_number: number;
  verse_number: number;
  sanskrit: string;
  transliteration: string;
  translation: string;
  translator: string;
  chapter_name: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  verses?: Verse[];
}

function VerseCard({ verse }: { verse: Verse }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <button
      onClick={() => setExpanded(!expanded)}
      className="text-left w-full rounded-lg p-3 text-sm transition-colors"
      style={{
        background: "var(--accent-light)",
        border: "1px solid var(--border)",
      }}
    >
      <div className="flex justify-between items-center">
        <span className="font-semibold" style={{ color: "var(--accent)" }}>
          BG {verse.chapter_number}.{verse.verse_number}
        </span>
        <div className="flex items-center gap-2">
          <span className="text-xs" style={{ color: "var(--muted)" }}>
            {verse.chapter_name}
          </span>
          <span
            className="text-xs transition-transform"
            style={{
              color: "var(--muted)",
              transform: expanded ? "rotate(180deg)" : "rotate(0deg)",
            }}
          >
            ▼
          </span>
        </div>
      </div>
      {expanded && (
        <div className="mt-2 space-y-2" style={{ color: "var(--foreground)" }}>
          <p>{verse.translation}</p>
          <p className="italic text-xs" style={{ color: "var(--muted)" }}>
            {verse.transliteration}
          </p>
          <p
            className="text-xs font-mono whitespace-pre-line"
            style={{ color: "var(--muted)" }}
          >
            {verse.sanskrit}
          </p>
          <p className="text-xs" style={{ color: "var(--muted)" }}>
            Translation by {verse.translator}
          </p>
        </div>
      )}
    </button>
  );
}

function SourcesSection({ verses }: { verses: Verse[] }) {
  const [open, setOpen] = useState(false);

  if (!verses.length) return null;

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs font-medium px-1 transition-colors hover:opacity-80"
        style={{ color: "var(--muted)" }}
      >
        <span
          className="transition-transform"
          style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
        >
          ▼
        </span>
        {verses.length} verse{verses.length > 1 ? "s" : ""} from the Gita
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {verses.map((verse) => (
            <VerseCard key={verse.verse_id} verse={verse} />
          ))}
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div className={`max-w-[80%] ${isUser ? "" : "w-full"}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser ? "rounded-br-md" : "rounded-bl-md"
          }`}
          style={{
            background: isUser ? "var(--accent)" : "var(--card)",
            color: isUser ? "#fff" : "var(--foreground)",
            border: isUser ? "none" : "1px solid var(--border)",
          }}
        >
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        </div>
        {message.verses && <SourcesSection verses={message.verses} />}
      </div>
    </div>
  );
}

const SUGGESTIONS = [
  "What does Krishna say about the nature of the soul?",
  "How can I overcome fear and anxiety?",
  "What is Nishkama Karma?",
  "What is the path to inner peace?",
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(text?: string) {
    const message = text || input.trim();
    if (!message || loading) return;

    setInput("");
    const userMessage: Message = { role: "user", content: message };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await fetch(`${PIPELINE_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) throw new Error("Failed to get response");

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let verses: Verse[] = [];
      let answerText = "";
      let firstLine = true;

      const assistantMessage: Message = { role: "assistant", content: "", verses: [] };
      setMessages((prev) => [...prev, assistantMessage]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });

        if (firstLine) {
          const newlineIndex = chunk.indexOf("\n");
          if (newlineIndex !== -1) {
            const jsonLine = chunk.slice(0, newlineIndex);
            try {
              const parsed = JSON.parse(jsonLine);
              verses = parsed.verses || [];
            } catch {
              answerText += chunk;
            }
            answerText += chunk.slice(newlineIndex + 1);
            firstLine = false;
          } else {
            answerText += chunk;
          }
        } else {
          answerText += chunk;
        }

        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: answerText,
            verses,
          };
          return updated;
        });
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "I apologize, but I encountered an error. Please ensure the backend is running (uvicorn services.pipeline.src.api.main:app --reload) and try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto">
      {/* Header */}
      <header
        className="text-center py-6 px-4"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <h1 className="text-2xl font-bold" style={{ color: "var(--accent)" }}>
          GitaAI
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
          Wisdom from the Bhagavad Gita, grounded in scripture
        </p>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full space-y-6">
            <div className="text-center space-y-2">
              <p className="text-lg" style={{ color: "var(--foreground)" }}>
                Ask a question about the Bhagavad Gita
              </p>
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                Every answer is grounded in actual verses with citations
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handleSubmit(s)}
                  className="text-left text-sm rounded-lg px-4 py-3 transition-colors hover:opacity-80"
                  style={{
                    background: "var(--card)",
                    border: "1px solid var(--border)",
                    color: "var(--foreground)",
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {loading && messages[messages.length - 1]?.role === "user" && (
          <div className="flex justify-start mb-4">
            <div
              className="rounded-2xl rounded-bl-md px-4 py-3"
              style={{
                background: "var(--card)",
                border: "1px solid var(--border)",
              }}
            >
              <div className="flex space-x-1">
                <div
                  className="w-2 h-2 rounded-full animate-bounce"
                  style={{ background: "var(--accent)", animationDelay: "0ms" }}
                />
                <div
                  className="w-2 h-2 rounded-full animate-bounce"
                  style={{ background: "var(--accent)", animationDelay: "150ms" }}
                />
                <div
                  className="w-2 h-2 rounded-full animate-bounce"
                  style={{ background: "var(--accent)", animationDelay: "300ms" }}
                />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Input */}
      <footer
        className="px-4 py-4"
        style={{ borderTop: "1px solid var(--border)" }}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about the Gita..."
            className="flex-1 rounded-xl px-4 py-3 outline-none transition-colors"
            style={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              color: "var(--foreground)",
            }}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-xl px-6 py-3 font-medium transition-opacity disabled:opacity-50"
            style={{ background: "var(--accent)", color: "#fff" }}
          >
            Ask
          </button>
        </form>
        <p
          className="text-center text-xs mt-2"
          style={{ color: "var(--muted)" }}
        >
          Answers are AI-generated. Always verify with the original texts.
        </p>
      </footer>
    </div>
  );
}
