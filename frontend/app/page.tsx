import { AgentContextButton } from "@/components/AgentContextButton";
import { HomeChat } from "@/components/HomeChat";
import { MonthSelector } from "@/components/MonthSelector";
import { TrendChart } from "@/components/TrendChart";
import { getAgentInterpretation, getDashboard } from "@/lib/api";

const statusText: Record<string, string> = {
  strong: "偏强",
  neutral: "中性",
  weak: "偏弱",
};

type HomeProps = {
  searchParams?: Promise<{ month?: string }>;
};

export default async function Home({ searchParams }: HomeProps) {
  const params = await searchParams;
  const selectedMonth = params?.month;
  const dashboard = await getDashboard(selectedMonth);
  const agent = await getAgentInterpretation(dashboard.month);
  const matchedRules = dashboard.rule_results.filter((rule) => rule.matched);
  const sortedRules = [...dashboard.rule_results].sort((a, b) => Number(b.matched) - Number(a.matched));

  return (
    <main className="radar-workspace">
      <HomeChat month={dashboard.month} initialAgent={agent} />

      <section className="display-pane">
        <section className="panel display-table">
          <div className="panel-title-row">
            <div className="table-title">
              <h2>核心指标表</h2>
              <MonthSelector months={dashboard.months} currentMonth={dashboard.month} />
            </div>
            <span>{dashboard.indicators.length} 项指标</span>
          </div>
          {dashboard.indicators.length ? (
            <div className="table-scroll">
              <table className="compact-table">
                <thead>
                  <tr>
                    <th>指标</th>
                    <th>模块</th>
                    <th>当前值</th>
                    <th>同比</th>
                    <th>环比</th>
                    <th>3个月趋势</th>
                    <th>24月分位</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.indicators.map((row) => (
                    <tr key={row.id}>
                      <td>
                        <AgentContextButton
                          context={{
                            type: "indicator",
                            name: row.indicator.name,
                            code: row.indicator.code,
                            month: dashboard.month,
                            value: row.value,
                            unit: row.indicator.unit,
                            yoy: row.yoy,
                            mom: row.mom,
                            trend_3m: row.trend_3m,
                            percentile_24m: row.percentile_24m,
                            status: row.status,
                          }}
                        >
                          <strong>{row.indicator.name}</strong>
                        </AgentContextButton>
                        <span className="small">{row.indicator.source}</span>
                      </td>
                      <td>{row.indicator.category}</td>
                      <td>
                        {row.value}
                        {row.indicator.unit}
                      </td>
                      <td>{formatNumber(row.yoy)}</td>
                      <td>{formatNumber(row.mom)}</td>
                      <td>{formatNumber(row.trend_3m)}</td>
                      <td>{formatNumber(row.percentile_24m)}%</td>
                      <td>
                        <span className={`status ${row.status}`}>{statusText[row.status] || row.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="empty-state">当前月份没有指标数据。</p>
          )}
        </section>

        <section className="display-bottom">
          <div className="panel visual-panel">
            <div className="panel-title-row">
              <h2>关键趋势图</h2>
              <span>截至 {dashboard.month}</span>
            </div>
            <TrendChart history={dashboard.history} currentMonth={dashboard.month} />
          </div>

          <div className="panel rules-panel">
            <div className="panel-title-row">
              <h2>规则雷达</h2>
              <span>{matchedRules.length} 条命中</span>
            </div>
            <div className="rules rules-scroll">
              {dashboard.rule_results.length ? (
                sortedRules.map((rule) => (
                  <article className={`rule ${rule.matched ? "matched" : ""}`} key={rule.rule_id}>
                    <div className="rule-title">
                      <AgentContextButton
                        context={{
                          type: "rule",
                          name: rule.name,
                          rule_id: rule.rule_id,
                          month: dashboard.month,
                          matched: rule.matched,
                          evidence: rule.evidence.evidence_text || rule.explanation,
                          risk: rule.evidence.risk,
                        }}
                      >
                        <span>{rule.name}</span>
                      </AgentContextButton>
                      <span className="tag">{rule.matched ? "已命中" : "未命中"}</span>
                    </div>
                    <p className="module-desc">{rule.evidence.evidence_text || rule.explanation}</p>
                    {rule.matched && rule.evidence.risk ? (
                      <p className="rule-risk">{rule.evidence.risk}</p>
                    ) : null}
                  </article>
                ))
              ) : (
                <p className="empty-state">当前月份没有规则评估结果。</p>
              )}
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}

function formatNumber(value: number | null) {
  if (value === null || value === undefined) return "-";
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}
