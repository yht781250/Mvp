"""
规则建议引擎

基于规则的风险预警和投资建议生成。
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session

from app.data.models import Fund, Holding, Signal, SignalLevel
from app.services import fund_service, holding_service, nav_service, metrics_service


class RuleType(str, Enum):
    """规则类型"""
    CONCENTRATION = "concentration"  # 集中度
    REBALANCE = "rebalance"  # 再平衡
    DRAWDOWN = "drawdown"  # 回撤
    VOLATILITY = "volatility"  # 波动率
    SHARPE = "sharpe"  # 夏普比率


@dataclass
class RuleResult:
    """规则检查结果"""
    rule_name: str
    rule_type: RuleType
    level: SignalLevel
    triggered: bool
    title: str
    diagnosis: str  # 诊断结论
    trigger_basis: str  # 触发依据
    suggestion: str  # 建议动作
    risk_warning: str  # 风险提示
    fund_code: Optional[str] = None
    fund_name: Optional[str] = None
    trigger_value: Optional[str] = None
    threshold_value: Optional[str] = None


# ============ 规则定义 ============

def check_single_fund_concentration(
    db: Session,
    holdings: list[Holding],
    threshold: float = 25.0,
) -> list[RuleResult]:
    """
    规则1：单基金占比超过阈值

    当单只基金占总成本的比例超过25%时，提示集中度风险。
    """
    results = []
    total_cost = sum(h.total_cost for h in holdings)

    if total_cost == 0:
        return results

    # 按基金汇总
    fund_costs: dict[int, Decimal] = {}
    fund_info: dict[int, tuple[str, str]] = {}

    for h in holdings:
        fund_costs[h.fund_id] = fund_costs.get(h.fund_id, Decimal("0")) + h.total_cost
        fund_info[h.fund_id] = (h.fund.code, h.fund.name)

    for fund_id, cost in fund_costs.items():
        pct = float(cost / total_cost * 100)
        code, name = fund_info[fund_id]

        if pct > threshold:
            level = SignalLevel.WARNING if pct > 40 else SignalLevel.ATTENTION
            results.append(RuleResult(
                rule_name="单基金集中度",
                rule_type=RuleType.CONCENTRATION,
                level=level,
                triggered=True,
                title=f"{name} 占比过高",
                diagnosis=f"该基金占组合总成本的 {pct:.1f}%，超过 {threshold}% 的警戒线。",
                trigger_basis=f"单基金成本 ¥{cost:,.2f}，占比 {pct:.1f}%",
                suggestion="建议分散投资，降低单只基金的仓位比例，避免过度依赖单一基金的表现。",
                risk_warning="集中持仓可能放大单只基金的波动对组合的影响，增加非系统性风险。",
                fund_code=code,
                fund_name=name,
                trigger_value=f"{pct:.1f}%",
                threshold_value=f"{threshold}%",
            ))

    return results


def check_asset_allocation(
    db: Session,
    holdings: list[Holding],
    target_equity: float = 60.0,
    tolerance: float = 10.0,
) -> list[RuleResult]:
    """
    规则2：权益仓位超过目标配置

    当股票型+指数型基金占比超过目标配置一定比例时，提示再平衡。
    """
    results = []
    allocation = metrics_service.get_asset_allocation(holdings)

    if not allocation:
        return results

    # 计算权益类占比（股票型 + 指数型）
    equity_pct = allocation.get("stock", 0) + allocation.get("index", 0)
    deviation = equity_pct - target_equity

    if deviation > tolerance:
        results.append(RuleResult(
            rule_name="资产配置偏离",
            rule_type=RuleType.REBALANCE,
            level=SignalLevel.ATTENTION,
            triggered=True,
            title="权益仓位超配",
            diagnosis=f"当前权益类资产占比 {equity_pct:.1f}%，超过目标配置 {target_equity}% 约 {deviation:.1f} 个百分点。",
            trigger_basis=f"股票型 {allocation.get('stock', 0):.1f}% + 指数型 {allocation.get('index', 0):.1f}% = {equity_pct:.1f}%",
            suggestion="建议适度调整，减持部分权益类基金或增加债券类基金，使资产配置回归目标比例。",
            risk_warning="权益仓位过高会增加组合波动，在市场下跌时可能承受较大损失。",
            trigger_value=f"{equity_pct:.1f}%",
            threshold_value=f"{target_equity + tolerance}%",
        ))
    elif deviation < -tolerance:
        results.append(RuleResult(
            rule_name="资产配置偏离",
            rule_type=RuleType.REBALANCE,
            level=SignalLevel.INFO,
            triggered=True,
            title="权益仓位低配",
            diagnosis=f"当前权益类资产占比 {equity_pct:.1f}%，低于目标配置 {target_equity}% 约 {-deviation:.1f} 个百分点。",
            trigger_basis=f"股票型 {allocation.get('stock', 0):.1f}% + 指数型 {allocation.get('index', 0):.1f}% = {equity_pct:.1f}%",
            suggestion="如果风险承受能力允许，可考虑适度增加权益类基金配置，提高组合的收益潜力。",
            risk_warning="权益仓位过低可能导致长期收益不及预期，需根据自身风险偏好决定。",
            trigger_value=f"{equity_pct:.1f}%",
            threshold_value=f"{target_equity - tolerance}%",
        ))

    return results


def check_max_drawdown(
    db: Session,
    holdings: list[Holding],
    threshold: float = -15.0,
) -> list[RuleResult]:
    """
    规则3：回撤超过阈值

    当基金近期最大回撤超过阈值时，提示检查基金质量。
    """
    results = []
    fund_ids = set(h.fund_id for h in holdings)

    for fund_id in fund_ids:
        fund = fund_service.get_fund_by_id(db, fund_id)
        if not fund:
            continue

        metrics = metrics_service.calculate_fund_metrics(db, fund, days=30)
        if metrics.max_drawdown is None:
            continue

        if metrics.max_drawdown < threshold:
            level = SignalLevel.WARNING if metrics.max_drawdown < -25 else SignalLevel.ATTENTION
            results.append(RuleResult(
                rule_name="回撤预警",
                rule_type=RuleType.DRAWDOWN,
                level=level,
                triggered=True,
                title=f"{fund.name} 回撤较大",
                diagnosis=f"该基金近30日最大回撤达 {metrics.max_drawdown:.2f}%，超过 {threshold}% 的警戒线。",
                trigger_basis=f"最大回撤 {metrics.max_drawdown:.2f}%",
                suggestion="建议检查基金近期表现和持仓变化，评估是否为短期波动或基金质量问题。如确认基金质量下滑，可考虑减仓或换基。",
                risk_warning="大幅回撤可能需要较长时间恢复，需关注基金经理操作和市场环境变化。",
                fund_code=fund.code,
                fund_name=fund.name,
                trigger_value=f"{metrics.max_drawdown:.2f}%",
                threshold_value=f"{threshold}%",
            ))

    return results


def check_high_volatility(
    db: Session,
    holdings: list[Holding],
    threshold: float = 35.0,
) -> list[RuleResult]:
    """
    规则4：波动率异常升高

    当基金年化波动率超过阈值时，提示分批操作。
    """
    results = []
    fund_ids = set(h.fund_id for h in holdings)

    for fund_id in fund_ids:
        fund = fund_service.get_fund_by_id(db, fund_id)
        if not fund:
            continue

        metrics = metrics_service.calculate_fund_metrics(db, fund, days=30)
        if metrics.annualized_volatility is None:
            continue

        if metrics.annualized_volatility > threshold:
            level = SignalLevel.ATTENTION
            results.append(RuleResult(
                rule_name="波动率预警",
                rule_type=RuleType.VOLATILITY,
                level=level,
                triggered=True,
                title=f"{fund.name} 波动较大",
                diagnosis=f"该基金年化波动率达 {metrics.annualized_volatility:.2f}%，超过 {threshold}% 的警戒线。",
                trigger_basis=f"年化波动率 {metrics.annualized_volatility:.2f}%",
                suggestion="建议采用分批买入/卖出策略，避免一次性操作遭遇不利时点。同时关注市场环境和基金策略是否发生变化。",
                risk_warning="高波动意味着净值波动剧烈，短期内可能出现较大涨跌，需做好心理准备。",
                fund_code=fund.code,
                fund_name=fund.name,
                trigger_value=f"{metrics.annualized_volatility:.2f}%",
                threshold_value=f"{threshold}%",
            ))

    return results


def check_negative_sharpe(
    db: Session,
    holdings: list[Holding],
) -> list[RuleResult]:
    """
    规则5：夏普比率为负

    当基金夏普比率为负时，表示收益不及无风险利率，需要关注。
    """
    results = []
    fund_ids = set(h.fund_id for h in holdings)

    for fund_id in fund_ids:
        fund = fund_service.get_fund_by_id(db, fund_id)
        if not fund:
            continue

        metrics = metrics_service.calculate_fund_metrics(db, fund, days=30)
        if metrics.sharpe_ratio is None:
            continue

        if metrics.sharpe_ratio < 0:
            level = SignalLevel.ATTENTION
            results.append(RuleResult(
                rule_name="风险收益比预警",
                rule_type=RuleType.SHARPE,
                level=level,
                triggered=True,
                title=f"{fund.name} 风险收益比不佳",
                diagnosis=f"该基金夏普比率为 {metrics.sharpe_ratio:.2f}，低于0表示承担风险后的收益不及无风险利率。",
                trigger_basis=f"夏普比率 {metrics.sharpe_ratio:.2f}",
                suggestion="建议评估该基金是否值得继续持有，可对比同类基金表现，考虑是否换成风险收益比更优的产品。",
                risk_warning="夏普比率为负说明当前阶段基金表现不佳，但也可能是短期市场因素，需结合更长周期判断。",
                fund_code=fund.code,
                fund_name=fund.name,
                trigger_value=f"{metrics.sharpe_ratio:.2f}",
                threshold_value="0",
            ))

    return results


# ============ 规则引擎主函数 ============

def run_all_rules(db: Session) -> list[RuleResult]:
    """
    运行所有规则检查

    返回所有触发的规则结果列表
    """
    holdings = holding_service.get_all_holdings(db)
    if not holdings:
        return []

    all_results = []

    # 规则1：单基金集中度
    all_results.extend(check_single_fund_concentration(db, holdings))

    # 规则2：资产配置偏离
    all_results.extend(check_asset_allocation(db, holdings))

    # 规则3：回撤预警
    all_results.extend(check_max_drawdown(db, holdings))

    # 规则4：波动率预警
    all_results.extend(check_high_volatility(db, holdings))

    # 规则5：夏普比率预警
    all_results.extend(check_negative_sharpe(db, holdings))

    # 按严重程度排序
    level_order = {
        SignalLevel.CRITICAL: 0,
        SignalLevel.WARNING: 1,
        SignalLevel.ATTENTION: 2,
        SignalLevel.INFO: 3,
    }
    all_results.sort(key=lambda x: level_order.get(x.level, 99))

    return all_results


def save_signals(db: Session, results: list[RuleResult]) -> int:
    """
    将规则检查结果保存为信号记录

    返回保存的记录数
    """
    count = 0
    for r in results:
        if not r.triggered:
            continue

        fund_id = None
        if r.fund_code:
            fund = fund_service.get_fund_by_code(db, r.fund_code)
            if fund:
                fund_id = fund.id

        signal = Signal(
            fund_id=fund_id,
            rule_name=r.rule_name,
            level=r.level,
            title=r.title,
            description=f"{r.diagnosis}\n\n触发依据：{r.trigger_basis}",
            trigger_value=r.trigger_value,
            threshold_value=r.threshold_value,
            suggestion=f"{r.suggestion}\n\n⚠️ {r.risk_warning}",
        )
        db.add(signal)
        count += 1

    db.flush()
    return count
