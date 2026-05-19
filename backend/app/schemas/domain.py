from pydantic import BaseModel, ConfigDict


class IndicatorDefinitionBase(BaseModel):
    code: str
    name: str
    category: str
    frequency: str = "monthly"
    source: str
    unit: str
    importance: int = 3
    confidence: float = 0.8
    definition: str
    interpretation: str
    risk_note: str


class IndicatorDefinitionCreate(IndicatorDefinitionBase):
    pass


class IndicatorDefinitionRead(IndicatorDefinitionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class IndicatorDataBase(BaseModel):
    indicator_id: int
    month: str
    value: float
    yoy: float | None = None
    mom: float | None = None
    trend_3m: float | None = None
    percentile_24m: float | None = None
    status: str = "neutral"


class IndicatorDataCreate(IndicatorDataBase):
    pass


class IndicatorDataRead(IndicatorDataBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    indicator: IndicatorDefinitionRead | None = None


class RuleResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_id: str
    month: str
    name: str
    module: str
    severity: str
    matched: bool
    explanation: str
    evidence: dict


class CycleSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    month: str
    headline: str
    summary: str
    modules: dict
    risks: list
    watch_tasks: list
    agent_brief: str


class DashboardRead(BaseModel):
    month: str
    months: list[str]
    snapshot: CycleSnapshotRead
    indicators: list[IndicatorDataRead]
    rule_results: list[RuleResultRead]
    history: list[dict]


class AgentInterpretationRead(BaseModel):
    month: str
    prompt_version: str
    prompt_excerpt: str | None = None
    mode: str = "mock"
    model: str | None = None
    tools: list[str] = []
    intent: str | None = None
    skill: str | None = None
    context_summary: str | None = None
    steps: list[str] = []
    sections: list[dict] = []
    content: str


class AgentInterpretationRequest(BaseModel):
    month: str | None = None
    use_model: bool = False
    question: str | None = None
    conversation_id: str = "default"
    history: list[dict] = []
    selected_context: dict | None = None
