"use client";

import { FormEvent, useEffect, useState } from "react";
import type { AgentInterpretation } from "@/lib/api";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  sections?: Array<{ title: string; body: string }>;
};

type HomeChatProps = {
  month: string;
  initialAgent: AgentInterpretation;
};

type SelectedContext = Record<string, unknown> & {
  type?: string;
  name?: string;
  matched?: boolean;
};

function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
}

const QUICK_PROMPTS = [
  "本月处在什么宏观状态？",
  "为什么有规则命中？",
  "下个月重点观察什么？",
  "对家庭和企业有什么含义？",
];

export function HomeChat({ month, initialAgent }: HomeChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: `已加载 ${month} 的指标、规则和周期快照。\n你可以继续追问，例如”为什么说信用偏弱？”或”下个月重点看什么？”。`,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedContext, setSelectedContext] = useState<SelectedContext | null>(null);

  useEffect(() => {
    function handleContext(event: Event) {
      const detail = (event as CustomEvent<SelectedContext>).detail;
      setSelectedContext(detail);
      if (detail.type === "indicator") {
        setInput(`解释一下 ${detail.name} 对本月周期判断的影响`);
      } else if (detail.type === "rule") {
        setInput(`解释规则“${detail.name}”为什么${detail.matched ? "命中" : "未命中"}`);
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
      setMessages((items) => [
        ...items,
        {
          role: "assistant",
          content: data.content,
          sections: data.sections,
        },
      ]);
    } catch (error) {
      setMessages((items) => [
        ...items,
        {
          role: "assistant",
          content: "Agent 调用失败。请确认后端服务和模型配置可用后重试。",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <aside className="chat-pane">
      <div className="chat-head">
        <div>
          <span className="eyebrow">DeepAgent</span>
          <h2>宏观周期对话</h2>
        </div>
        <span className="chat-month">{month}</span>
      </div>

      <div className="agent-capabilities">
        <span>意图判断</span>
        <span>技能路由</span>
        <span>工具取数</span>
        <span>会话记忆</span>
      </div>

      <div className="chat-messages">
        {messages.map((message, index) => (
          <article className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
            <div className="chat-role">{message.role === "user" ? "你" : "Agent"}</div>
            {!message.sections?.length ? <div className="chat-content">{message.content}</div> : null}
            {message.role === "assistant" && message.sections?.length ? (
              <div className="agent-sections">
                {message.sections.map((section) => (
                  <details key={section.title} open={message.sections?.length === 1}>
                    <summary>{section.title}</summary>
                    <p>{section.body}</p>
                  </details>
                ))}
              </div>
            ) : null}
          </article>
        ))}
        {loading ? (
          <article className="chat-message assistant">
            <div className="chat-role">Agent</div>
            <div className="chat-content">正在读取指标、规则和快照...</div>
          </article>
        ) : null}
      </div>

      <div className="quick-prompts">
        {QUICK_PROMPTS.map((prompt) => (
          <button type="button" key={prompt} onClick={() => submitQuestion(prompt)} disabled={loading}>
            {prompt}
          </button>
        ))}
      </div>

      <form className="chat-input" onSubmit={handleSubmit}>
        {selectedContext ? (
          <div className="selected-context">
            <span>上下文：{selectedContext.name || selectedContext.type}</span>
            <button type="button" onClick={() => setSelectedContext(null)}>
              清除
            </button>
          </div>
        ) : null}
        <textarea
          aria-label="向 Agent 提问"
          placeholder="例如：本月为什么判断信用偏弱？"
          rows={3}
          value={input}
          onChange={(event) => setInput(event.target.value)}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          发送
        </button>
      </form>
    </aside>
  );
}
