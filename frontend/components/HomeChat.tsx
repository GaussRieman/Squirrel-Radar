"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import type { AgentInterpretation } from "@/lib/api";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type HomeChatProps = {
  month: string;
};

type SelectedContext = Record<string, unknown> & {
  type?: string;
  name?: string;
  matched?: boolean;
};

function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
}

export function HomeChat({ month }: HomeChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedContext, setSelectedContext] = useState<SelectedContext | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    function handleContext(event: Event) {
      const detail = (event as CustomEvent<SelectedContext>).detail;
      setSelectedContext(detail);
      if (detail.type === "indicator") {
        setInput(`解释一下 ${detail.name} 对本月周期判断的影响`);
      } else if (detail.type === "rule") {
        setInput(`解释规则"${detail.name}"为什么${detail.matched ? "命中" : "未命中"}`);
      }
    }
    window.addEventListener("agent-context-selected", handleContext);
    return () => window.removeEventListener("agent-context-selected", handleContext);
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await submitQuestion(input);
  }

  async function submitQuestion(rawQuestion: string) {
    const question = rawQuestion.trim();
    if (!question || loading) return;

    setInput("");
    setLoading(true);
    const nextMessages: ChatMessage[] = [...messages, { role: "user", content: question }];
    setMessages(nextMessages);

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/agent/interpretation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          month,
          question,
          use_model: true,
          conversation_id: `macro-cycle-radar:${month}`,
          selected_context: selectedContext,
        }),
      });
      if (!response.ok) throw new Error("Agent request failed");
      const data = (await response.json()) as AgentInterpretation;
      setMessages((items) => [...items, { role: "assistant", content: data.content }]);
      if (data.navigate_month) {
        window.dispatchEvent(
          new CustomEvent("agent-navigate-month", { detail: { month: data.navigate_month } })
        );
      }
    } catch {
      setMessages((items) => [
        ...items,
        { role: "assistant", content: "请求失败，请重试。" },
      ]);
    } finally {
      setLoading(false);
      setSelectedContext(null);
    }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submitQuestion(input);
    }
  }

  return (
    <aside className="chat-pane">
      <header className="chat-header">
        <span className="chat-header-title">宏观周期 Agent</span>
      </header>

      <div className="chat-messages">
        {messages.length === 0 && !loading ? (
          <div className="chat-empty">
            <p>你好，我是宏观周期 Agent。</p>
            <p>可以问我本月的经济状态、规则命中原因、风险点或对家庭企业的含义。</p>
          </div>
        ) : null}

        {messages.map((message, index) => (
          <article className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
            <div className="chat-role-label">
              {message.role === "user" ? "我" : "Agent"}
            </div>
            <div className="chat-content">
              {message.role === "assistant" ? (
                <ReactMarkdown>{message.content}</ReactMarkdown>
              ) : (
                message.content
              )}
            </div>
          </article>
        ))}

        {loading ? (
          <article className="chat-message assistant">
            <div className="chat-role-label">Agent</div>
            <div className="chat-content chat-thinking">
              <span />
              <span />
              <span />
            </div>
          </article>
        ) : null}
        <div ref={bottomRef} />
      </div>

      <form className="chat-input" onSubmit={handleSubmit}>
        {selectedContext ? (
          <div className="selected-context">
            <span>上下文：{selectedContext.name || selectedContext.type}</span>
            <button type="button" onClick={() => setSelectedContext(null)}>×</button>
          </div>
        ) : null}
        <div className="chat-input-row">
          <textarea
            aria-label="向 Agent 提问"
            placeholder={`问问 ${month} 的宏观状态…`}
            rows={1}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button type="submit" disabled={loading || !input.trim()} aria-label="发送">
            ↑
          </button>
        </div>
      </form>
    </aside>
  );
}
