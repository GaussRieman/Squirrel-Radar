import { getIndicators } from "@/lib/api";

export default async function IndicatorsPage() {
  const indicators = await getIndicators();

  return (
    <main>
      <header className="topbar">
        <div>
          <h1>指标定义</h1>
          <p className="subtitle">查看 12 个核心宏观指标的定义、解释、风险提示和关联指标。</p>
        </div>
        <a className="nav-link" href="/">
          返回首页
        </a>
      </header>

      <section className="indicator-list">
        {indicators.map((indicator) => (
          <article className="panel" key={indicator.id}>
            <div className="indicator-card-head">
              <div>
                <h2>{indicator.name}</h2>
                <p className="small">
                  {indicator.category} · {indicator.frequency} ·{" "}
                  {indicator.source_url ? (
                    <a className="source-link" href={indicator.source_url} target="_blank" rel="noreferrer">
                      {indicator.source}
                    </a>
                  ) : (
                    indicator.source
                  )}
                </p>
              </div>
              <span className="status neutral">重要性 {indicator.importance}</span>
            </div>
            <p className="module-desc">{indicator.definition}</p>
            <p className="module-desc">
              <strong>解释：</strong>
              {indicator.interpretation}
            </p>
            <p className="module-desc">
              <strong>风险：</strong>
              {indicator.risk_note}
            </p>
          </article>
        ))}
      </section>
    </main>
  );
}
