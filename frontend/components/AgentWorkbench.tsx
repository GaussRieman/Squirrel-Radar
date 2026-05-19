"use client";

import { useState } from "react";

import type { AgentInterpretation, AgentStatus, TestScenario } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function AgentWorkbench({
  scenarios,
  initialMonth,
  status,
}: {
  scenarios: TestScenario[];
  initialMonth: string;
  status: AgentStatus;
}) {
  const [scenarioId, setScenarioId] = useState(scenarios[0]?.scenario_id || "");
  const [month, setMonth] = useState(initialMonth || scenarios[0]?.month || "");
  const [useModel, setUseModel] = useState(false);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<AgentInterpretation | null>(null);

  async function applyScenario() {
    if (!scenarioId) return;
    setMessage("正在应用测试数据...");
    const response = await fetch(`${API_BASE}/api/test-data/scenarios/${scenarioId}/apply`, {
      method: "POST",
    });
    if (!response.ok) {
      setMessage(`应用失败：${await response.text()}`);
      return;
    }
    const payload = await response.json();
    setMonth(payload.month);
    setMessage(`已应用测试场景：${payload.name}，月份 ${payload.month}。`);
  }

  async function runAgent() {
    setMessage(useModel ? "正在调用 DeepAgent..." : "正在生成 mock 解读...");
    const response = await fetch(`${API_BASE}/api/agent/interpretation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ month, use_model: useModel }),
    });
    if (!response.ok) {
      setMessage(`生成失败：${await response.text()}`);
      return;
    }
    const payload = (await response.json()) as AgentInterpretation;
    setResult(payload);
    setMessage(payload.mode === "deepagent" ? `已由 DeepAgent 生成：${payload.model}` : "已生成 mock 解读。若要真实调用模型，请配置 OPENAI_API_KEY。");
  }

  const activeScenario = scenarios.find((scenario) => scenario.scenario_id === scenarioId);

  return (
    <section className="grid two-col" style={{ marginTop: 20 }}>
      <div className="panel">
        <h2>Macro Cycle Agent</h2>
        <div className="agent-status">
          <span>Runtime：{status.runtime}</span>
          <span>Model：{status.model}</span>
          <span>{status.api_key_configured ? "密钥已配置" : "未配置密钥，使用 mock fallback"}</span>
          <span>{status.base_url_configured ? "兼容模型 Base URL 已配置" : "未配置 OPENAI_BASE_URL"}</span>
        </div>
        <div className="tool-list">
          {status.tools.map((tool) => (
            <code key={tool}>{tool}</code>
          ))}
        </div>
        <div className="form-grid">
          <label>
            测试场景
            <select value={scenarioId} onChange={(event) => setScenarioId(event.target.value)}>
              {scenarios.map((scenario) => (
                <option value={scenario.scenario_id} key={scenario.scenario_id}>
                  {scenario.name}
                </option>
              ))}
            </select>
          </label>
          {activeScenario ? <p className="module-desc">{activeScenario.description}</p> : null}
          <label>
            解读月份
            <input value={month} onChange={(event) => setMonth(event.target.value)} placeholder="YYYY-MM" />
          </label>
          <label className="checkbox-line">
            <input type="checkbox" checked={useModel} onChange={(event) => setUseModel(event.target.checked)} />
            使用 DeepAgent 调用真实模型，并让 Agent 通过工具读取指标、规则和快照
          </label>
          <div className="form-actions">
            <button type="button" onClick={applyScenario}>
              应用测试数据
            </button>
            <button type="button" onClick={runAgent}>
              生成解读
            </button>
          </div>
          {message ? <p className="form-message">{message}</p> : null}
        </div>
      </div>

      <div className="panel">
        <h2>生成结果</h2>
        {result ? (
          <>
            <p className="small">
              模式：{result.mode} {result.model ? `· 模型：${result.model}` : ""}
            </p>
            {result.tools?.length ? (
              <p className="small">可用工具：{result.tools.join("、")}</p>
            ) : null}
            <div className="agent-markdown">{result.content}</div>
          </>
        ) : (
          <p className="empty-state">先应用一个测试场景，然后点击“生成解读”。</p>
        )}
      </div>
    </section>
  );
}
