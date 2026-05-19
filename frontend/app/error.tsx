"use client";

export default function ErrorPage({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <main>
      <section className="panel" style={{ marginTop: 24 }}>
        <h1>数据暂时不可用</h1>
        <p className="subtitle">{error.message || "当前页面缺少必要数据，请稍后重试。"}</p>
        <button className="primary-action" type="button" onClick={() => reset()}>
          重新加载
        </button>
      </section>
    </main>
  );
}
