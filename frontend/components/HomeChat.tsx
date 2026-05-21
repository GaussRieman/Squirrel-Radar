"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { ArrowUp, Mic, Paperclip, Plus } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  status?: string;
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
  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
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
      } else if (detail.type === "module") {
        setInput(`解释一下${detail.name}模块为什么是"${detail.state}"`);
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
    const nextMessages: ChatMessage[] = [
      ...messages,
      { role: "user", content: question },
      { role: "assistant", content: "", status: "理解请求" },
    ];
    setMessages(nextMessages);

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/agent/stream`, {
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
      if (!response.body) throw new Error("Agent stream unavailable");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      function appendAssistant(text: string) {
        setMessages((items) =>
          items.map((item, index) =>
            index === items.length - 1 && item.role === "assistant"
              ? { ...item, content: item.content + text, status: undefined }
              : item,
          ),
        );
      }

      function updateAssistantStatus(status: string) {
        setMessages((items) =>
          items.map((item, index) =>
            index === items.length - 1 && item.role === "assistant" && !item.content
              ? { ...item, status }
              : item,
          ),
        );
      }

      function handleBlock(block: string) {
        const lines = block.split("\n");
        const eventLine = lines.find((line) => line.startsWith("event:"));
        const dataLine = lines.find((line) => line.startsWith("data:"));
        if (!eventLine || !dataLine) return;
        const event = eventLine.slice("event:".length).trim();
        const data = JSON.parse(dataLine.slice("data:".length).trim()) as Record<string, unknown>;
        if (event === "delta" && typeof data.text === "string") {
          appendAssistant(data.text);
        }
        if (event === "status" && typeof data.label === "string") {
          updateAssistantStatus(data.label);
        }
        if (event === "action" && data.type === "navigate_month" && typeof data.month === "string") {
          window.dispatchEvent(
            new CustomEvent("agent-navigate-month", { detail: { month: data.month } })
          );
        }
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";
        for (const block of blocks) handleBlock(block);
      }
      buffer += decoder.decode();
      if (buffer.trim()) handleBlock(buffer);
    } catch {
      setMessages((items) =>
        items.map((item, index) =>
          index === items.length - 1 && item.role === "assistant"
            ? { ...item, content: item.content || "请求失败，请重试。", status: undefined }
            : item,
        ),
      );
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

  const lastMessage = messages[messages.length - 1];
  const showThinking = loading && lastMessage?.role === "assistant" && !lastMessage.content;
  const quickPrompts = [
    "解释本月为什么是信用偏弱",
    "生成一份月度宏观总结",
    "这对家庭部门意味着什么",
    "列出下月需要跟踪的证据",
  ];

  return (
    <section className="chat-pane">
      <header className="chat-header">
        <div>
          <span className="chat-header-eyebrow">当前主题</span>
          <h1 className="chat-header-title">{month} 宏观分析</h1>
        </div>
        <span className="chat-header-month">真实快照</span>
      </header>

      <div className="chat-messages">
        {messages.length === 0 && !loading ? (
          <div className="chat-empty">
            <h2>从一个问题开始。</h2>
            <p>我会结合右侧证据链解释周期判断、规则命中原因，以及它对家庭和企业的含义。</p>
          </div>
        ) : null}

        {messages.map((message, index) =>
          message.role === "assistant" && !message.content ? null : (
            <article className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
              <div className="chat-role-label">
                {message.role === "user" ? "我" : "Agent"}
              </div>
              <div className="chat-content">
                {message.role === "assistant" ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                ) : (
                  message.content
                )}
              </div>
            </article>
          ),
        )}

        {showThinking ? (
          <article className="chat-message assistant">
            <div className="chat-role-label">Agent</div>
            <div className="chat-content">
              <span className="stream-status">{lastMessage.status || "处理中"}</span>
            </div>
          </article>
        ) : null}
        <div ref={bottomRef} />
      </div>

      <form className="chat-input" onSubmit={handleSubmit}>
        <div className="quick-prompts" aria-label="快捷问题">
          {quickPrompts.map((prompt) => (
            <button
              type="button"
              key={prompt}
              onClick={() => submitQuestion(prompt)}
              disabled={loading}
            >
              {prompt}
            </button>
          ))}
        </div>
        {selectedContext ? (
          <div className="selected-context">
            <span>上下文：{selectedContext.name || selectedContext.type}</span>
            <button type="button" onClick={() => setSelectedContext(null)}>×</button>
          </div>
        ) : null}
        <div className="chat-input-row">
          <button type="button" className="input-icon-button" aria-label="新建分析">
            <Plus size={18} />
          </button>
          <button type="button" className="input-icon-button" aria-label="上传材料">
            <Paperclip size={18} />
          </button>
          <textarea
            aria-label="向 Agent 提问"
            placeholder={`问问 ${month} 的宏观状态…`}
            rows={1}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button type="button" className="input-icon-button" aria-label="语音输入">
            <Mic size={18} />
          </button>
          <button className="send-button" type="submit" disabled={loading || !input.trim()} aria-label="发送">
            <ArrowUp size={18} />
          </button>
        </div>
      </form>
    </section>
  );
}
