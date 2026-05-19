import { AgentWorkbench } from "@/components/AgentWorkbench";
import { getAgentStatus, getDashboard, getTestScenarios } from "@/lib/api";

export default async function AgentPage() {
  const [dashboard, scenarios, status] = await Promise.all([
    getDashboard(),
    getTestScenarios(),
    getAgentStatus(),
  ]);

  return (
    <main>
      <header className="topbar">
        <div>
          <h1>Agent 解读工作台</h1>
          <p className="subtitle">
            应用测试数据，选择是否调用 DeepAgent 真实模型，然后生成宏观周期状态解读。
          </p>
        </div>
        <a className="nav-link" href="/">
          返回首页
        </a>
      </header>
      <AgentWorkbench scenarios={scenarios} initialMonth={dashboard.month} status={status} />
    </main>
  );
}
