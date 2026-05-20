export type IndicatorDefinition = {
  id: number;
  code: string;
  name: string;
  category: string;
  frequency: string;
  source: string;
  unit: string;
  importance: number;
  confidence: number;
  definition: string;
  interpretation: string;
  risk_note: string;
};

export type IndicatorData = {
  id: number;
  indicator_id: number;
  month: string;
  value: number;
  yoy: number | null;
  mom: number | null;
  trend_3m: number | null;
  percentile_24m: number | null;
  status: string;
  indicator: IndicatorDefinition;
};

export type RuleResult = {
  id: number;
  rule_id: string;
  month: string;
  name: string;
  module: string;
  severity: string;
  matched: boolean;
  explanation: string;
  evidence: {
    conditions?: Record<string, unknown>;
    risk?: string;
    observed_indicators?: string[];
    triggered_status?: { module: string; status: string; severity: string };
    evidence_template?: string;
    evidence_text?: string;
  };
};

export type CycleSnapshot = {
  id: number;
  month: string;
  headline: string;
  summary: string;
  modules: Record<
    string,
    {
      module: string;
      state: string;
      description: string;
      signals?: Array<{
        rule_id: string;
        name: string;
        category: string;
        severity: string;
        risk?: string;
        evidence_text?: string;
      }>;
    }
  >;
  risks: string[];
  watch_tasks: string[];
  agent_brief: string;
};

export type Dashboard = {
  month: string;
  months: string[];
  snapshot: CycleSnapshot;
  indicators: IndicatorData[];
  rule_results: RuleResult[];
  history: Array<{
    month: string;
    code: string;
    name: string;
    value: number;
    yoy: number | null;
    mom: number | null;
  }>;
};

export type AgentInterpretation = {
  month: string;
  mode: string;
  model?: string | null;
  tools?: string[];
  sections: Array<{ title: string; body: string }>;
  content: string;
  navigate_month?: string | null;
};

export type AgentStatus = {
  runtime: string;
  model: string;
  model_calls_enabled: boolean;
  api_key_configured: boolean;
  base_url_configured: boolean;
  tools: string[];
  skills: string[];
  fallback: string;
};

export type TestScenario = {
  scenario_id: string;
  name: string;
  month: string;
  description: string;
  data: Record<string, unknown>;
};

export type RuleCatalog = {
  version: number;
  updated_at: string;
  rules: Array<{
    rule_id: string;
    name: string;
    category: string;
    description: string;
    observed_indicators: string[];
    logic: "all" | "any";
    conditions: Array<{
      indicator: string;
      field: string;
      operator: string;
      value: number;
    }>;
    triggered_status: { module: string; status: string; severity: string };
    risk: string;
    evidence_template: string;
  }>;
};

function getBaseUrl() {
  return process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
}

export async function getDashboard(month?: string): Promise<Dashboard> {
  const baseUrl = getBaseUrl();
  const query = month ? `?month=${encodeURIComponent(month)}` : "";
  const response = await fetch(`${baseUrl}/api/dashboard${query}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Failed to load dashboard");
  }
  return response.json();
}

export async function getIndicators(): Promise<IndicatorDefinition[]> {
  const baseUrl = getBaseUrl();
  const response = await fetch(`${baseUrl}/api/indicators`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Failed to load indicators");
  }
  return response.json();
}

export async function getAgentInterpretation(month?: string): Promise<AgentInterpretation> {
  const baseUrl = getBaseUrl();
  const query = month ? `?month=${encodeURIComponent(month)}` : "";
  const response = await fetch(`${baseUrl}/api/agent/interpretation${query}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Failed to load agent interpretation");
  }
  return response.json();
}

export async function getTestScenarios(): Promise<TestScenario[]> {
  const baseUrl = getBaseUrl();
  const response = await fetch(`${baseUrl}/api/test-data/scenarios`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Failed to load test scenarios");
  }
  return response.json();
}

export async function getAgentStatus(): Promise<AgentStatus> {
  const baseUrl = getBaseUrl();
  const response = await fetch(`${baseUrl}/api/agent/status`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Failed to load agent status");
  }
  return response.json();
}

export async function getRuleCatalog(): Promise<RuleCatalog> {
  const baseUrl = getBaseUrl();
  const response = await fetch(`${baseUrl}/api/rules`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Failed to load rules");
  }
  return response.json();
}
