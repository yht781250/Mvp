"""
指标计算服务

提供基金和组合的核心风险收益指标计算。
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
import math

from sqlalchemy.orm import Session

from app.data.models import Fund, NavHistory, Holding
from app.services.nav_service import get_nav_history


@dataclass
class FundMetrics:
    """单只基金指标"""
    fund_code: str
    fund_name: str
    period_return: Optional[float] = None  # 区间收益率 %
    annualized_volatility: Optional[float] = None  # 年化波动率 %
    max_drawdown: Optional[float] = None  # 最大回撤 %
    sharpe_ratio: Optional[float] = None  # 夏普比率
    latest_nav: Optional[float] = None  # 最新净值
    nav_date: Optional[date] = None  # 净值日期


@dataclass
class PortfolioMetrics:
    """组合整体指标"""
    total_cost: Decimal  # 总成本
    total_value: Optional[Decimal] = None  # 总市值（如有最新净值）
    total_return: Optional[float] = None  # 总收益率 %
    fund_count: int = 0  # 基金只数
    holding_count: int = 0  # 持仓笔数
    top3_concentration: Optional[float] = None  # 前3大持仓集中度 %


# 无风险利率（年化），用于计算夏普比率
RISK_FREE_RATE = 0.02  # 2%


def calculate_period_return(nav_list: list[NavHistory]) -> Optional[float]:
    """
    计算区间收益率

    参数:
        nav_list: 净值列表（按日期降序）

    返回:
        收益率百分比，如 10.5 表示 10.5%
    """
    if len(nav_list) < 2:
        return None

    # nav_list 按日期降序，第一个是最新，最后一个是最早
    latest_nav = float(nav_list[0].nav)
    earliest_nav = float(nav_list[-1].nav)

    if earliest_nav == 0:
        return None

    return_pct = (latest_nav - earliest_nav) / earliest_nav * 100
    return round(return_pct, 2)


def calculate_annualized_volatility(nav_list: list[NavHistory]) -> Optional[float]:
    """
    计算年化波动率

    使用日收益率的标准差，年化因子为 sqrt(252)

    参数:
        nav_list: 净值列表（按日期降序）

    返回:
        年化波动率百分比
    """
    if len(nav_list) < 3:
        return None

    # 按日期正序排列，计算日收益率
    sorted_nav = sorted(nav_list, key=lambda x: x.nav_date)
    daily_returns = []

    for i in range(1, len(sorted_nav)):
        prev_nav = float(sorted_nav[i - 1].nav)
        curr_nav = float(sorted_nav[i].nav)
        if prev_nav > 0:
            daily_return = (curr_nav - prev_nav) / prev_nav
            daily_returns.append(daily_return)

    if len(daily_returns) < 2:
        return None

    # 计算标准差
    mean = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
    std_dev = math.sqrt(variance)

    # 年化（假设一年252个交易日）
    annualized_vol = std_dev * math.sqrt(252) * 100
    return round(annualized_vol, 2)


def calculate_max_drawdown(nav_list: list[NavHistory]) -> Optional[float]:
    """
    计算最大回撤

    最大回撤 = (历史最高点 - 最低点) / 历史最高点

    参数:
        nav_list: 净值列表（按日期降序）

    返回:
        最大回撤百分比（负数），如 -15.5 表示回撤 15.5%
    """
    if len(nav_list) < 2:
        return None

    # 按日期正序排列
    sorted_nav = sorted(nav_list, key=lambda x: x.nav_date)
    navs = [float(n.nav) for n in sorted_nav]

    max_drawdown = 0
    peak = navs[0]

    for nav in navs:
        if nav > peak:
            peak = nav
        drawdown = (nav - peak) / peak
        if drawdown < max_drawdown:
            max_drawdown = drawdown

    return round(max_drawdown * 100, 2)


def calculate_sharpe_ratio(
    nav_list: list[NavHistory],
    risk_free_rate: float = RISK_FREE_RATE,
) -> Optional[float]:
    """
    计算夏普比率

    夏普比率 = (年化收益率 - 无风险利率) / 年化波动率

    参数:
        nav_list: 净值列表（按日期降序）
        risk_free_rate: 无风险利率（年化）

    返回:
        夏普比率
    """
    if len(nav_list) < 3:
        return None

    # 计算年化收益率
    period_return = calculate_period_return(nav_list)
    if period_return is None:
        return None

    # 估算年化收益率（假设持有期为 nav_list 的天数）
    sorted_nav = sorted(nav_list, key=lambda x: x.nav_date)
    days = (sorted_nav[-1].nav_date - sorted_nav[0].nav_date).days
    if days <= 0:
        return None

    annualized_return = (period_return / 100) * (365 / days)

    # 计算年化波动率
    volatility = calculate_annualized_volatility(nav_list)
    if volatility is None or volatility == 0:
        return None

    # 夏普比率
    sharpe = (annualized_return - risk_free_rate) / (volatility / 100)
    return round(sharpe, 2)


def calculate_fund_metrics(db: Session, fund: Fund, days: int = 30) -> FundMetrics:
    """
    计算单只基金的所有指标

    参数:
        db: 数据库会话
        fund: 基金对象
        days: 计算区间天数

    返回:
        FundMetrics 对象
    """
    nav_list = get_nav_history(db, fund.id, limit=days)

    metrics = FundMetrics(
        fund_code=fund.code,
        fund_name=fund.name,
    )

    if nav_list:
        metrics.latest_nav = float(nav_list[0].nav)
        metrics.nav_date = nav_list[0].nav_date
        metrics.period_return = calculate_period_return(nav_list)
        metrics.annualized_volatility = calculate_annualized_volatility(nav_list)
        metrics.max_drawdown = calculate_max_drawdown(nav_list)
        metrics.sharpe_ratio = calculate_sharpe_ratio(nav_list)

    return metrics


def calculate_portfolio_metrics(
    db: Session,
    holdings: list[Holding],
) -> PortfolioMetrics:
    """
    计算组合整体指标

    参数:
        db: 数据库会话
        holdings: 持仓列表

    返回:
        PortfolioMetrics 对象
    """
    total_cost = Decimal("0")
    total_value = Decimal("0")
    fund_codes = set()
    holding_values = []  # (代码, 市值)

    for h in holdings:
        total_cost += h.total_cost
        fund_codes.add(h.fund.code)

        # 获取最新净值计算市值
        nav_list = get_nav_history(db, h.fund_id, limit=1)
        if nav_list:
            current_value = h.shares * Decimal(str(nav_list[0].nav))
            total_value += current_value
            holding_values.append((h.fund.code, current_value))

    metrics = PortfolioMetrics(
        total_cost=total_cost,
        fund_count=len(fund_codes),
        holding_count=len(holdings),
    )

    # 计算总收益率
    if total_cost > 0 and total_value > 0:
        metrics.total_value = total_value
        return_pct = float((total_value - total_cost) / total_cost * 100)
        metrics.total_return = round(return_pct, 2)

    # 计算前3大持仓集中度
    if holding_values and total_value > 0:
        # 按市值降序排序
        holding_values.sort(key=lambda x: x[1], reverse=True)
        top3_value = sum(v for _, v in holding_values[:3])
        concentration = float(top3_value / total_value * 100)
        metrics.top3_concentration = round(concentration, 2)

    return metrics


def get_asset_allocation(holdings: list[Holding]) -> dict[str, float]:
    """
    计算资产类型占比

    参数:
        holdings: 持仓列表

    返回:
        {资产类型: 占比百分比}
    """
    type_totals: dict[str, Decimal] = {}
    total = Decimal("0")

    for h in holdings:
        fund_type = h.fund.fund_type.value
        type_totals[fund_type] = type_totals.get(fund_type, Decimal("0")) + h.total_cost
        total += h.total_cost

    if total == 0:
        return {}

    allocation = {}
    for fund_type, value in type_totals.items():
        allocation[fund_type] = round(float(value / total * 100), 2)

    return allocation
