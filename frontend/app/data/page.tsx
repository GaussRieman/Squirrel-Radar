import { CsvImportForm } from "@/components/CsvImportForm";
import { DataEntryForm } from "@/components/DataEntryForm";
import { getIndicators } from "@/lib/api";

export default async function DataPage() {
  const indicators = await getIndicators();

  return (
    <main>
      <header className="topbar">
        <div>
          <h1>指标数据维护</h1>
          <p className="subtitle">手动录入或 CSV 导入月度指标数据，保存后后端会重新计算对应月份的规则和快照。</p>
        </div>
        <a className="nav-link" href="/">
          返回首页
        </a>
      </header>

      <section className="grid two-col" style={{ marginTop: 20 }}>
        <div className="panel">
          <h2>手动录入</h2>
          <DataEntryForm indicators={indicators} />
        </div>
        <div className="panel">
          <h2>CSV 导入</h2>
          <CsvImportForm />
          <p className="module-desc" style={{ marginTop: 12 }}>
            CSV 字段：indicator_code, month, value, yoy, mom, trend_3m, percentile_24m, status。
          </p>
        </div>
      </section>
    </main>
  );
}
