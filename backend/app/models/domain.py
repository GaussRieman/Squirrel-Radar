from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


INDICATOR_SOURCE_URLS = {
    "m2_yoy": "https://www.cnfin.com/yw-lb/detail/20260514/4412666_1.html",
    "tsf_stock_yoy": "https://www.cnfin.com/yw-lb/detail/20260514/4412666_1.html",
    "new_rmb_loan": "https://www.nbd.com.cn/articles/2026-05-14/4392761.html",
    "household_mid_long_loan": "https://www.nbd.com.cn/articles/2026-05-14/4392761.html",
    "enterprise_mid_long_loan": "https://www.nbd.com.cn/articles/2026-05-14/4392761.html",
    "core_cpi": "https://www.stats.gov.cn/sj/zxfb/202605/t20260511_1963659.html",
    "ppi": "https://www.stats.gov.cn/sj/zxfbhjd/202605/t20260511_1963658.html",
    "secondhand_home_price_mom_70c": "https://www.stats.gov.cn/sj/zxfb/202605/t20260518_1963715.html",
    "commodity_house_sales_area": "https://www.stats.gov.cn/sj/zxfb/202605/t20260518_1963729.html",
    "wage_income": "https://www.stats.gov.cn/sj/zxfb/202604/t20260416_1963323.html",
    "private_investment": "https://www.stats.gov.cn/sj/zxfb/202605/t20260518_1963730.html",
    "industrial_profit": "https://www.stats.gov.cn/sj/zxfb/202604/t20260427_1963403.html",
}


class IndicatorDefinition(Base):
    __tablename__ = "indicator_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64), index=True)
    frequency: Mapped[str] = mapped_column(String(32), default="monthly")
    source: Mapped[str] = mapped_column(String(128))
    unit: Mapped[str] = mapped_column(String(32))
    importance: Mapped[int] = mapped_column(Integer, default=3)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    definition: Mapped[str] = mapped_column(Text)
    interpretation: Mapped[str] = mapped_column(Text)
    risk_note: Mapped[str] = mapped_column(Text)

    data_points: Mapped[list["IndicatorData"]] = relationship(
        back_populates="indicator", cascade="all, delete-orphan"
    )

    @property
    def source_url(self) -> str | None:
        return INDICATOR_SOURCE_URLS.get(self.code)


class IndicatorData(Base):
    __tablename__ = "indicator_data"
    __table_args__ = (UniqueConstraint("indicator_id", "month", name="uq_indicator_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicator_definitions.id"))
    month: Mapped[str] = mapped_column(String(7), index=True)
    value: Mapped[float] = mapped_column(Float)
    yoy: Mapped[float | None] = mapped_column(Float)
    mom: Mapped[float | None] = mapped_column(Float)
    trend_3m: Mapped[float | None] = mapped_column(Float)
    percentile_24m: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="neutral")

    indicator: Mapped[IndicatorDefinition] = relationship(back_populates="data_points")


class RuleResult(Base):
    __tablename__ = "rule_results"
    __table_args__ = (UniqueConstraint("rule_id", "month", name="uq_rule_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(64), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    name: Mapped[str] = mapped_column(String(128))
    module: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(32))
    matched: Mapped[bool] = mapped_column(default=False)
    explanation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)


class CycleSnapshot(Base):
    __tablename__ = "cycle_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[str] = mapped_column(String(7), unique=True, index=True)
    headline: Mapped[str] = mapped_column(String(256))
    summary: Mapped[str] = mapped_column(Text)
    modules: Mapped[dict] = mapped_column(JSON, default=dict)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    watch_tasks: Mapped[list] = mapped_column(JSON, default=list)
    agent_brief: Mapped[str] = mapped_column(Text)
