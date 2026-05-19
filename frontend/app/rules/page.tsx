import { getRuleCatalog } from "@/lib/api";

export default async function RulesPage() {
  const catalog = await getRuleCatalog();

  return (
    <main>
      <header className="topbar">
        <div>
          <h1>规则系统</h1>
          <p className="subtitle">
            当前规则版本 {catalog.version}，更新时间 {catalog.updated_at}。规则使用透明阈值条件和 all/any 逻辑。
          </p>
        </div>
        <a className="nav-link" href="/">
          返回首页
        </a>
      </header>

      <section className="rule-catalog">
        {catalog.rules.map((rule) => (
          <article className="panel" key={rule.rule_id}>
            <div className="indicator-card-head">
              <div>
                <h2>{rule.name}</h2>
                <p className="small">
                  {rule.category} · {rule.logic === "all" ? "全部条件满足" : "任一条件满足"}
                </p>
              </div>
              <span className="status neutral">{rule.triggered_status.severity}</span>
            </div>
            <p className="module-desc">{rule.description}</p>
            <div className="condition-list">
              {rule.conditions.map((condition) => (
                <code key={`${rule.rule_id}-${condition.indicator}-${condition.field}`}>
                  {condition.indicator}.{condition.field} {condition.operator} {condition.value}
                </code>
              ))}
            </div>
            <p className="module-desc">
              <strong>观察指标：</strong>
              {rule.observed_indicators.join("、")}
            </p>
            <p className="module-desc">
              <strong>触发状态：</strong>
              {rule.triggered_status.module} / {rule.triggered_status.status}
            </p>
            <p className="module-desc">
              <strong>风险：</strong>
              {rule.risk}
            </p>
          </article>
        ))}
      </section>
    </main>
  );
}
