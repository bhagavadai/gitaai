"use client";

import { useState, useRef, useEffect } from "react";

const PIPELINE_URL = process.env.NEXT_PUBLIC_PIPELINE_URL || "http://localhost:8000";

type Language = "en" | "hi" | "auto";

interface Verse {
  verse_id: string;
  chapter_number: number;
  verse_number: number;
  sanskrit: string;
  transliteration: string;
  translation: string;
  translator: string;
  translation_hindi?: string;
  translator_hindi?: string;
  chapter_name: string;
}

interface Concept {
  id: string;
  name: string;
  sanskrit_term: string;
  category: string;
  description: string;
  description_hindi?: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  verses?: Verse[];
  concepts?: Concept[];
  relatedConcepts?: Concept[];
  language?: string;
}

function VerseCard({ verse, language }: { verse: Verse; language: string }) {
  const [expanded, setExpanded] = useState(false);

  const showHindi = language === "hi" && verse.translation_hindi;
  const translation = showHindi ? verse.translation_hindi! : verse.translation;
  const translator = showHindi
    ? verse.translator_hindi || verse.translator
    : verse.translator;

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
          <p>{translation}</p>
          {showHindi && verse.translation && (
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              English: {verse.translation}
            </p>
          )}
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
            {language === "hi" ? "अनुवाद:" : "Translation by"} {translator}
          </p>
        </div>
      )}
    </button>
  );
}

function SourcesSection({
  verses,
  language,
}: {
  verses: Verse[];
  language: string;
}) {
  const [open, setOpen] = useState(false);

  if (!verses.length) return null;

  const label =
    language === "hi"
      ? `गीता से ${verses.length} श्लोक`
      : `${verses.length} verse${verses.length > 1 ? "s" : ""} from the Gita`;

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
        {label}
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {verses.map((verse) => (
            <VerseCard key={verse.verse_id} verse={verse} language={language} />
          ))}
        </div>
      )}
    </div>
  );
}

function ConceptsSection({
  concepts,
  relatedConcepts,
  language,
}: {
  concepts: Concept[];
  relatedConcepts: Concept[];
  language: string;
}) {
  const [open, setOpen] = useState(false);

  if (!concepts.length && !relatedConcepts.length) return null;

  const label =
    language === "hi"
      ? `${concepts.length} संबंधित अवधारणाएँ`
      : `${concepts.length} related concept${concepts.length !== 1 ? "s" : ""}`;

  return (
    <div className="mt-2">
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
        {label}
      </button>
      {open && (
        <div className="mt-2 flex flex-wrap gap-2">
          {concepts.map((c) => (
            <span
              key={c.id}
              className="inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium"
              style={{
                background: "var(--accent)",
                color: "#fff",
              }}
              title={language === "hi" && c.description_hindi ? c.description_hindi : c.description}
            >
              {c.name}
              <span className="opacity-75">{c.sanskrit_term}</span>
            </span>
          ))}
          {relatedConcepts.map((c) => (
            <span
              key={c.id}
              className="inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs"
              style={{
                background: "var(--accent-light)",
                color: "var(--foreground)",
                border: "1px solid var(--border)",
              }}
              title={language === "hi" && c.description_hindi ? c.description_hindi : c.description}
            >
              {c.name}
              <span style={{ color: "var(--muted)" }}>{c.sanskrit_term}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const language = message.language || "en";

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
        {message.concepts && message.concepts.length > 0 && (
          <ConceptsSection
            concepts={message.concepts}
            relatedConcepts={message.relatedConcepts || []}
            language={language}
          />
        )}
        {message.verses && (
          <SourcesSection verses={message.verses} language={language} />
        )}
      </div>
    </div>
  );
}

function LanguageToggle({
  language,
  onChange,
}: {
  language: Language;
  onChange: (lang: Language) => void;
}) {
  return (
    <div className="flex items-center gap-1 text-xs">
      {(["auto", "en", "hi"] as Language[]).map((lang) => (
        <button
          key={lang}
          onClick={() => onChange(lang)}
          className="px-2 py-1 rounded-md transition-colors"
          style={{
            background: language === lang ? "var(--accent)" : "transparent",
            color: language === lang ? "#fff" : "var(--muted)",
            border:
              language === lang ? "none" : "1px solid var(--border)",
          }}
        >
          {lang === "auto" ? "Auto" : lang === "en" ? "EN" : "हिंदी"}
        </button>
      ))}
    </div>
  );
}

const SUGGESTIONS_EN = [
  "What does Krishna say about the nature of the soul?",
  "How can I overcome fear and anxiety?",
  "What is Nishkama Karma?",
  "What is the path to inner peace?",
];

const SUGGESTIONS_HI = [
  "कृष्ण आत्मा के बारे में क्या कहते हैं?",
  "मैं अपने डर और चिंता को कैसे दूर करूं?",
  "निष्काम कर्म क्या है?",
  "मन की शांति का मार्ग क्या है?",
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState<Language>("auto");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const suggestions = language === "hi" ? SUGGESTIONS_HI : SUGGESTIONS_EN;

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
        body: JSON.stringify({ message, language }),
      });

      if (!response.ok) throw new Error("Failed to get response");

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let verses: Verse[] = [];
      let concepts: Concept[] = [];
      let relatedConcepts: Concept[] = [];
      let detectedLang = "en";
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
              concepts = parsed.concepts || [];
              relatedConcepts = parsed.related_concepts || [];
              detectedLang = parsed.language || "en";
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
            concepts,
            relatedConcepts,
            language: detectedLang,
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
            language === "hi"
              ? "क्षमा करें, एक त्रुटि हुई। कृपया सुनिश्चित करें कि बैकएंड चल रहा है और पुनः प्रयास करें।"
              : "I apologize, but I encountered an error. Please ensure the backend is running and try again.",
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
        className="flex items-center justify-between py-4 px-4"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <div />
        <div className="text-center">
          <h1 className="text-2xl font-bold" style={{ color: "var(--accent)" }}>
            GitaAI
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
            {language === "hi"
              ? "भगवद्गीता का ज्ञान, शास्त्र पर आधारित"
              : "Wisdom from the Bhagavad Gita, grounded in scripture"}
          </p>
        </div>
        <LanguageToggle language={language} onChange={setLanguage} />
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full space-y-6">
            <div className="text-center space-y-2">
              <p className="text-lg" style={{ color: "var(--foreground)" }}>
                {language === "hi"
                  ? "भगवद्गीता के बारे में कोई प्रश्न पूछें"
                  : "Ask a question about the Bhagavad Gita"}
              </p>
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                {language === "hi"
                  ? "हर उत्तर वास्तविक श्लोकों पर आधारित है"
                  : "Every answer is grounded in actual verses with citations"}
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
              {suggestions.map((s) => (
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
            placeholder={
              language === "hi"
                ? "गीता के बारे में पूछें..."
                : "Ask about the Gita..."
            }
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
            {language === "hi" ? "पूछें" : "Ask"}
          </button>
        </form>
        <p
          className="text-center text-xs mt-2"
          style={{ color: "var(--muted)" }}
        >
          {language === "hi"
            ? "उत्तर AI द्वारा उत्पन्न हैं। मूल ग्रंथों से सत्यापित करें।"
            : "Answers are AI-generated. Always verify with the original texts."}
        </p>
      </footer>
    </div>
  );
}
