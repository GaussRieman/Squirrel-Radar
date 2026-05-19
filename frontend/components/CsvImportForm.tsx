"use client";

import { FormEvent, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function CsvImportForm() {
  const [message, setMessage] = useState("");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("正在导入...");
    const form = new FormData(event.currentTarget);
    const response = await fetch(`${API_BASE}/api/indicator-data/import-csv`, {
      method: "POST",
      body: form,
    });
    setMessage(response.ok ? `导入完成：${await response.text()}` : `导入失败：${await response.text()}`);
  }

  return (
    <form className="form-grid" onSubmit={onSubmit}>
      <label>
        CSV 文件
        <input name="file" type="file" accept=".csv,text/csv" required />
      </label>
      <div className="form-actions">
        <button type="submit">上传并导入</button>
        <a href={`${API_BASE}/api/indicator-data/template.csv`}>下载 CSV 模板</a>
      </div>
      {message ? <p className="form-message">{message}</p> : null}
    </form>
  );
}
