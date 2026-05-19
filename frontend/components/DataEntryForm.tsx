"use client";

import { FormEvent, useState } from "react";

import type { IndicatorDefinition } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function DataEntryForm({ indicators }: { indicators: IndicatorDefinition[] }) {
  const [message, setMessage] = useState("");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("正在保存...");
    const form = new FormData(event.currentTarget);
    const payload = {
      indicator_id: Number(form.get("indicator_id")),
      month: String(form.get("month")),
      value: Number(form.get("value")),
      yoy: toNumberOrNull(form.get("yoy")),
      mom: toNumberOrNull(form.get("mom")),
      trend_3m: toNumberOrNull(form.get("trend_3m")),
      percentile_24m: toNumberOrNull(form.get("percentile_24m")),
      status: String(form.get("status") || "neutral"),
    };
    const response = await fetch(`${API_BASE}/api/indicator-data`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setMessage(response.ok ? "已保存，并重新计算该月规则和快照。" : `保存失败：${await response.text()}`);
  }

  return (
    <form className="form-grid" onSubmit={onSubmit}>
      <label>
        指标
        <select name="indicator_id" required>
          {indicators.map((indicator) => (
            <option value={indicator.id} key={indicator.id}>
              {indicator.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        月份
        <input name="month" type="month" required />
      </label>
      <label>
        当前值
        <input name="value" type="number" step="0.01" required />
      </label>
      <label>
        同比
        <input name="yoy" type="number" step="0.01" />
      </label>
      <label>
        环比
        <input name="mom" type="number" step="0.01" />
      </label>
      <label>
        3个月趋势
        <input name="trend_3m" type="number" step="0.01" />
      </label>
      <label>
        24月分位
        <input name="percentile_24m" type="number" step="0.1" min="0" max="100" />
      </label>
      <label>
        状态
        <select name="status" defaultValue="neutral">
          <option value="strong">偏强</option>
          <option value="neutral">中性</option>
          <option value="weak">偏弱</option>
        </select>
      </label>
      <button type="submit">保存指标数据</button>
      {message ? <p className="form-message">{message}</p> : null}
    </form>
  );
}

function toNumberOrNull(value: FormDataEntryValue | null) {
  if (value === null || value === "") return null;
  return Number(value);
}
