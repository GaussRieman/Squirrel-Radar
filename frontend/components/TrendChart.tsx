"use client";

import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Dashboard } from "@/lib/api";

const COLORS = ["#2563eb", "#178c5f", "#c2410c", "#7c3aed"];
const DEFAULT_CODES = ["m2_yoy", "tsf_stock_yoy", "ppi", "commodity_house_sales_area"];

export function TrendChart({ history, currentMonth }: { history: Dashboard["history"]; currentMonth: string }) {
  const visibleHistory = useMemo(
    () => history.filter((row) => row.month <= currentMonth),
    [history, currentMonth],
  );
  const options = useMemo(() => {
    const names = new Map<string, string>();
    for (const row of visibleHistory) names.set(row.code, row.name);
    return Array.from(names.entries()).map(([code, name]) => ({ code, name }));
  }, [visibleHistory]);
  const [selected, setSelected] = useState(
    DEFAULT_CODES.filter((code) => options.some((option) => option.code === code)),
  );
  const activeCodes = selected.length ? selected : options.slice(0, 4).map((option) => option.code);
  const data = useMemo(() => {
    const byMonth = new Map<string, Record<string, number | string | null>>();
    for (const row of visibleHistory) {
      if (!activeCodes.includes(row.code)) continue;
      const item = byMonth.get(row.month) || { month: row.month };
      item[row.code] = row.yoy;
      byMonth.set(row.month, item);
    }
    return Array.from(byMonth.values());
  }, [visibleHistory, activeCodes]);

  function toggle(code: string) {
    setSelected((current) => {
      if (current.includes(code)) {
        return current.filter((item) => item !== code);
      }
      return [...current, code].slice(-4);
    });
  }

  return (
    <div>
      <div className="chart-controls">
        {options.map((option) => (
          <button
            className={activeCodes.includes(option.code) ? "active" : ""}
            type="button"
            key={option.code}
            onClick={() => toggle(option.code)}
          >
            {option.name}
          </button>
        ))}
      </div>
      {data.length ? (
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={data} margin={{ top: 8, right: 24, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e5e7eb" vertical={false} />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <ReferenceLine
              x={currentMonth}
              stroke="#111827"
              strokeDasharray="4 4"
              label={{ value: currentMonth, position: "insideTopRight", fontSize: 12 }}
            />
            {activeCodes.map((code, index) => {
              const option = options.find((item) => item.code === code);
              return (
                <Line
                  type="monotone"
                  dataKey={code}
                  name={option?.name || code}
                  stroke={COLORS[index % COLORS.length]}
                  dot={false}
                  strokeWidth={2}
                  key={code}
                />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <p className="empty-state">当前没有可展示的趋势数据。</p>
      )}
    </div>
  );
}
