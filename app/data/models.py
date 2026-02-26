"""
数据库模型定义

核心表：
- Fund: 基金基础信息
- Holding: 用户持仓信息
- NavHistory: 净值历史数据
- Signal: 规则触发记录
- Report: AI建议报告
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.database import Base


class FundType(str, Enum):
    """基金类型枚举"""

    STOCK = "stock"  # 股票型
    BOND = "bond"  # 债券型
    HYBRID = "hybrid"  # 混合型
    MONEY = "money"  # 货币型
    INDEX = "index"  # 指数型
    QDII = "qdii"  # QDII
    OTHER = "other"  # 其他


class SignalLevel(str, Enum):
    """信号级别枚举"""

    INFO = "info"  # 信息提示
    ATTENTION = "attention"  # 关注
    WARNING = "warning"  # 预警
    CRITICAL = "critical"  # 重要预警


class Fund(Base):
    """
    基金基础信息表

    存储基金的静态信息，如代码、名称、类型等。
    """

    __tablename__ = "funds"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, comment="基金代码")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="基金名称")
    fund_type: Mapped[FundType] = mapped_column(
        SQLEnum(FundType), default=FundType.OTHER, comment="基金类型"
    )
    manager: Mapped[Optional[str]] = mapped_column(String(50), comment="基金经理")
    company: Mapped[Optional[str]] = mapped_column(String(100), comment="基金公司")
    establish_date: Mapped[Optional[date]] = mapped_column(Date, comment="成立日期")
    scale: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(16, 2), comment="最新规模(亿元)"
    )
    fee_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 4), comment="管理费率"
    )
    is_favorite: Mapped[bool] = mapped_column(default=False, comment="是否自选")
    group_name: Mapped[Optional[str]] = mapped_column(String(50), comment="分组名称")
    notes: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    # 关联关系
    holdings: Mapped[list["Holding"]] = relationship(back_populates="fund")
    nav_history: Mapped[list["NavHistory"]] = relationship(back_populates="fund")
    signals: Mapped[list["Signal"]] = relationship(back_populates="fund")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="fund")

    __table_args__ = (Index("idx_fund_code", "code"),)

    def __repr__(self) -> str:
        return f"<Fund(code={self.code}, name={self.name})>"


class Holding(Base):
    """
    用户持仓信息表

    记录用户持有的基金份额、成本等信息。
    """

    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id"), nullable=False)
    shares: Mapped[Decimal] = mapped_column(
        Numeric(16, 4), nullable=False, comment="持有份额"
    )
    cost_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, comment="成本单价"
    )
    buy_date: Mapped[date] = mapped_column(Date, nullable=False, comment="买入日期")
    is_auto_invest: Mapped[bool] = mapped_column(default=False, comment="是否定投")
    notes: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    # 关联关系
    fund: Mapped["Fund"] = relationship(back_populates="holdings")

    __table_args__ = (Index("idx_holding_fund", "fund_id"),)

    @property
    def total_cost(self) -> Decimal:
        """总成本 = 份额 * 成本单价"""
        return self.shares * self.cost_price

    def __repr__(self) -> str:
        return f"<Holding(fund_id={self.fund_id}, shares={self.shares})>"


class NavHistory(Base):
    """
    净值历史数据表

    存储基金的每日净值数据。
    """

    __tablename__ = "nav_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id"), nullable=False)
    nav_date: Mapped[date] = mapped_column(Date, nullable=False, comment="净值日期")
    nav: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, comment="单位净值"
    )
    acc_nav: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 4), comment="累计净值"
    )
    daily_return: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 4), comment="日涨跌幅(%)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="创建时间"
    )

    # 关联关系
    fund: Mapped["Fund"] = relationship(back_populates="nav_history")

    __table_args__ = (
        Index("idx_nav_fund_date", "fund_id", "nav_date", unique=True),
        Index("idx_nav_date", "nav_date"),
    )

    def __repr__(self) -> str:
        return f"<NavHistory(fund_id={self.fund_id}, date={self.nav_date}, nav={self.nav})>"


class Signal(Base):
    """
    规则触发记录表

    记录规则引擎产生的预警信号。
    """

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fund_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("funds.id"), comment="关联基金(可为空表示组合级别)"
    )
    rule_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="规则名称")
    level: Mapped[SignalLevel] = mapped_column(
        SQLEnum(SignalLevel), default=SignalLevel.INFO, comment="信号级别"
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="信号标题")
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="详细描述")
    trigger_value: Mapped[Optional[str]] = mapped_column(String(100), comment="触发值")
    threshold_value: Mapped[Optional[str]] = mapped_column(String(100), comment="阈值")
    suggestion: Mapped[Optional[str]] = mapped_column(Text, comment="建议动作")
    is_read: Mapped[bool] = mapped_column(default=False, comment="是否已读")
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="触发时间"
    )

    # 关联关系
    fund: Mapped[Optional["Fund"]] = relationship(back_populates="signals")

    __table_args__ = (
        Index("idx_signal_fund", "fund_id"),
        Index("idx_signal_level", "level"),
        Index("idx_signal_time", "triggered_at"),
    )

    def __repr__(self) -> str:
        return f"<Signal(rule={self.rule_name}, level={self.level})>"


class Report(Base):
    """
    AI建议报告表

    存储系统生成的分析报告。
    """

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="报告类型(daily/weekly/analysis)"
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False, comment="报告日期")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="报告标题")
    summary: Mapped[str] = mapped_column(Text, nullable=False, comment="摘要结论")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="报告正文")
    data_snapshot: Mapped[Optional[str]] = mapped_column(Text, comment="数据快照(JSON)")
    risk_warning: Mapped[str] = mapped_column(
        Text,
        default="历史业绩不代表未来表现，基金投资有风险，入市需谨慎。",
        comment="风险提示",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="创建时间"
    )

    __table_args__ = (
        Index("idx_report_type_date", "report_type", "report_date"),
        Index("idx_report_date", "report_date"),
    )

    def __repr__(self) -> str:
        return f"<Report(type={self.report_type}, date={self.report_date})>"


class ChatRole(Base):
    """
    AI对话角色配置表

    存储自定义的AI对话角色，包括系统提示词、温度参数等。
    支持内置角色和用户自定义角色。
    """

    __tablename__ = "chat_roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="角色名称")
    description: Mapped[str] = mapped_column(String(200), nullable=False, comment="角色简介")
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, comment="系统提示词")
    is_default: Mapped[bool] = mapped_column(default=False, comment="是否默认角色")
    is_builtin: Mapped[bool] = mapped_column(default=False, comment="是否内置角色（不可删除）")
    temperature: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("0.70"), comment="生成温度(0-1)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    def __repr__(self) -> str:
        return f"<ChatRole(name={self.name}, is_default={self.is_default})>"


class ChatSession(Base):
    """
    AI对话会话表

    每次与一只基金的对话为一个会话，包含基金信息和角色配置。
    """

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False, comment="会话标题")
    fund_code: Mapped[Optional[str]] = mapped_column(String(10), comment="关联基金代码")
    fund_name: Mapped[Optional[str]] = mapped_column(String(100), comment="关联基金名称")
    role_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="使用的角色名称")
    message_count: Mapped[int] = mapped_column(default=0, comment="消息数量")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="最后活跃时间"
    )

    # 关联关系
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

    __table_args__ = (
        Index("idx_session_fund", "fund_code"),
        Index("idx_session_updated", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, title={self.title})>"


class ChatMessage(Base):
    """
    AI对话消息表

    存储每轮对话的用户消息和AI回复。
    """

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id"), nullable=False, comment="所属会话ID"
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="消息角色(user/assistant)"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="创建时间"
    )

    # 关联关系
    session: Mapped["ChatSession"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("idx_message_session", "session_id"),
    )

    def __repr__(self) -> str:
        return f"<ChatMessage(session_id={self.session_id}, role={self.role})>"


class TransactionType(str, Enum):
    """交易类型枚举"""

    BUY = "buy"  # 买入/加仓
    SELL = "sell"  # 卖出/减仓
    DIVIDEND = "dividend"  # 分红
    SPLIT = "split"  # 拆分


class Transaction(Base):
    """
    交易记录表

    记录每次买入、卖出、分红等操作，用于计算持仓成本和收益。
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id"), nullable=False)
    trans_type: Mapped[TransactionType] = mapped_column(
        SQLEnum(TransactionType), nullable=False, comment="交易类型"
    )
    shares: Mapped[Decimal] = mapped_column(
        Numeric(16, 4), nullable=False, comment="交易份额"
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, comment="交易单价"
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(16, 2), nullable=False, comment="交易金额"
    )
    fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0"), comment="手续费"
    )
    trans_date: Mapped[date] = mapped_column(Date, nullable=False, comment="交易日期")
    # 交易后的持仓快照
    shares_after: Mapped[Decimal] = mapped_column(
        Numeric(16, 4), nullable=False, comment="交易后总份额"
    )
    cost_after: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, comment="交易后成本单价"
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="创建时间"
    )

    # 关联关系
    fund: Mapped["Fund"] = relationship(back_populates="transactions")

    __table_args__ = (
        Index("idx_trans_fund", "fund_id"),
        Index("idx_trans_date", "trans_date"),
        Index("idx_trans_fund_date", "fund_id", "trans_date"),
    )

    def __repr__(self) -> str:
        return f"<Transaction(fund_id={self.fund_id}, type={self.trans_type}, shares={self.shares})>"
