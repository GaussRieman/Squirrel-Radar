from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


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
