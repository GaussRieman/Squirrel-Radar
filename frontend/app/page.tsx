"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Clock, FileText, MessageSquarePlus, Radar } from "lucide-react";
import { Suspense, useCallback, useEffect, useState } from "react";
import { AgentCanvas } from "@/components/AgentCanvas";
import { HomeChat } from "@/components/HomeChat";
import { type Dashboard, getDashboard } from "@/lib/api";

function HomeInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const urlMonth = searchParams.get("month") ?? undefined;

  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);

  const loadDashboard = useCallback(async (month?: string) => {
    setLoading(true);
    try {
      const data = await getDashboard(month);
      setDashboard(data);
      // sync URL without full navigation
      const params = new URLSearchParams(window.location.search);
      params.set("month", data.month);
      router.replace(`/?${params.toString()}`, { scroll: false });
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    loadDashboard(urlMonth);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Agent triggers this to switch month
  useEffect(() => {
    function handleNavigate(event: Event) {
      const { month } = (event as CustomEvent<{ month: string }>).detail;
      loadDashboard(month);
    }
    window.addEventListener("agent-navigate-month", handleNavigate);
    return () => window.removeEventListener("agent-navigate-month", handleNavigate);
  }, [loadDashboard]);

  if (!dashboard) {
    return (
      <main className="radar-workspace">
        <div className="chat-pane" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ color: "#5a7099", fontSize: 13 }}>加载中…</span>
        </div>
        <div className="display-pane" />
      </main>
    );
  }

  const assetItems = [
    "2026年4月宏观状态总结",
    "信用收缩压力解释",
    "房地产未确认见底证据链",
    "企业利润修复但投资未跟上",
  ];
  const topicItems = ["月度宏观雷达", "地产链观察", "居民部门观察", "企业利润观察"];

  return (
    <main className="radar-workspace">
      <aside className="asset-sidebar" aria-label="资产列表">
        <div className="asset-brand">
          <Radar size={20} />
          <span>SquirrelRadar</span>
        </div>
        <button className="new-analysis-button" type="button">
          <MessageSquarePlus size={17} />
          新建分析
        </button>
        <section className="asset-section">
          <h2>最近生成</h2>
          {assetItems.map((item, index) => (
            <button className={`asset-item${index === 0 ? " active" : ""}`} type="button" key={item}>
              <Clock size={15} />
              <span>{item}</span>
            </button>
          ))}
        </section>
        <section className="asset-section">
          <h2>专题资产</h2>
          {topicItems.map((item) => (
            <button className="asset-item" type="button" key={item}>
              <FileText size={15} />
              <span>{item}</span>
            </button>
          ))}
        </section>
      </aside>

      <HomeChat month={dashboard.month} />

      <section className={`display-pane${loading ? " pane-loading" : ""}`}>
        <AgentCanvas dashboard={dashboard} />
      </section>
    </main>
  );
}

export default function Home() {
  return (
    <Suspense>
      <HomeInner />
    </Suspense>
  );
}
