"use client";

import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AgentContextButton } from "@/components/AgentContextButton";
import { MonthSelector } from "@/components/MonthSelector";
import type { Dashboard, IndicatorData } from "@/lib/api";

const COLORS = ["#111827", "#2563eb", "#10a37f", "#c2410c", "#7c3aed", "#b7791f"];

const statusText: Record<string, string> = {
  strong: "偏强",
  neutral: "中性",
  weak: "偏弱",
};

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function formatTooltipNumber(value: unknown) {
  if (typeof value !== "number" || !Number.isFinite(value)) return String(value ?? "-");
  return Number(value.toPrecision(5)).toString();
}

function formatValue(row: IndicatorData) {
  return `${formatNumber(row.value)}${row.indicator.unit}`;
}

function normalizeRows(rows: Array<{ month: string; value: number }>) {
  const values = rows.map((row) => row.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  return rows.map((row) => ({
    month: row.month,
    value: max === min ? 50 : ((row.value - min) / (max - min)) * 100,
    raw: row.value,
  }));
}

export function AgentCanvas({ dashboard }: { dashboard: Dashboard }) {
  const modules = Object.values(dashboard.snapshot.modules);
  const historyByCode = useMemo(() => {
    const map = new Map<string, Dashboard["history"]>();
    for (const row of dashboard.history) {
      if (row.month > dashboard.month) continue;
      const list = map.get(row.code) || [];
      list.push(row);
      map.set(row.code, list);
    }
    return map;
  }, [dashboard.history, dashboard.month]);

  const chartSeries = dashboard.indicators.map((row) => {
    const rows = (historyByCode.get(row.indicator.code) || [])
      .slice(-12)
      .map((item) => ({ month: item.month, value: item.value }));
    return {
      row,
      data: rows.length ? normalizeRows(rows) : [],
    };
  });
  const combinedChartData = useMemo(() => {
    const byMonth = new Map<string, Record<string, number | string | null>>();
    for (const series of chartSeries) {
      for (const point of series.data) {
        const item = byMonth.get(point.month) || { month: point.month };
        item[series.row.indicator.code] = point.value;
        byMonth.set(point.month, item);
      }
    }
    return Array.from(byMonth.values());
  }, [chartSeries]);

  return (
    <section className="cycle-dashboard" aria-label="当前周期数据看板">
      <header className="dashboard-header">
        <div>
          <span>当前周期数据看板</span>
          <h2>{dashboard.month} 宏观周期</h2>
        </div>
        <MonthSelector months={dashboard.months} currentMonth={dashboard.month} />
      </header>

      <section className="dashboard-section status-section" aria-label="当前周期状态">
        <div className="dashboard-section-title">
          <h3>周期状态</h3>
          <span>点击卡片询问 Agent</span>
        </div>
        <div className="status-card-grid">
          {modules.map((module) => (
            <AgentContextButton
              className="status-card"
              context={{
                type: "module",
                name: module.module,
                state: module.state,
                month: dashboard.month,
                description: module.description,
                signals: module.signals,
              }}
              key={module.module}
            >
              <span>{module.module}</span>
              <strong>{module.state}</strong>
            </AgentContextButton>
          ))}
        </div>
      </section>

      <section className="dashboard-section charts-section" aria-label="全部指标图">
        <div className="dashboard-section-title">
          <h3>全部指标趋势</h3>
          <span>近 12 期 · 0-100 归一化</span>
        </div>
        <div className="combined-chart-wrap">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={combinedChartData} margin={{ top: 8, right: 18, left: -16, bottom: 0 }}>
              <CartesianGrid stroke="#e5e7eb" vertical={false} />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} width={38} />
              <Tooltip formatter={(value, name) => [formatTooltipNumber(value), name]} />
              {chartSeries.map(({ row }, index) => (
                <Line
                  type="monotone"
                  dataKey={row.indicator.code}
                  name={row.indicator.name}
                  stroke={COLORS[index % COLORS.length]}
                  dot={false}
                  strokeWidth={1.8}
                  strokeOpacity={0.86}
                  isAnimationActive={false}
                  key={row.id}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
          <div className="combined-chart-legend">
            {chartSeries.map(({ row }, index) => (
              <span key={row.id}>
                <i style={{ background: COLORS[index % COLORS.length] }} />
                {row.indicator.name}
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="dashboard-section table-section" aria-label="指标历史对比表">
        <div className="dashboard-section-title">
          <h3>指标对比与来源</h3>
          <span>{dashboard.indicators.length} 项</span>
        </div>
        <div className="dashboard-table-scroll">
          <table className="dashboard-table">
            <thead>
              <tr>
                <th>指标</th>
                <th>当前值</th>
                <th>上期</th>
                <th>3期均值</th>
                <th>24期分位</th>
                <th>状态</th>
                <th>来源</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.indicators.map((row) => {
                const history = historyByCode.get(row.indicator.code) || [];
                const previous = [...history].reverse().find((item) => item.month < dashboard.month);
                return (
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
                    </td>
                    <td>{formatValue(row)}</td>
                    <td>{previous ? `${formatNumber(previous.value)}${row.indicator.unit}` : "-"}</td>
                    <td>{formatNumber(row.trend_3m)}{row.trend_3m === null ? "" : row.indicator.unit}</td>
                    <td>{formatNumber(row.percentile_24m)}%</td>
                    <td>
                      <span className={`status ${row.status}`}>{statusText[row.status] || row.status}</span>
                    </td>
                    <td>
                      {row.indicator.source_url ? (
                        <a className="source-link" href={row.indicator.source_url} target="_blank" rel="noreferrer">
                          {row.indicator.source}
                        </a>
                      ) : (
                        row.indicator.source
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
