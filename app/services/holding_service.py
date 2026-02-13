"""
持仓服务层

提供持仓的增删改查、加减仓操作及CSV导入功能。
支持按基金汇总持仓、计算平均成本、记录交易流水。
"""

import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from app.data.models import Fund, FundType, Holding, Transaction, TransactionType
from app.services.fund_service import get_or_create_fund


@dataclass
class ImportResult:
    """导入结果"""
    success_count: int = 0
    fail_count: int = 0
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class PositionSummary:
    """持仓汇总（按基金）"""
    fund_id: int
    fund_code: str
    fund_name: str
    fund_type: str
    total_shares: Decimal  # 总份额
    avg_cost: Decimal  # 平均成本
    total_cost: Decimal  # 总成本
    first_buy_date: date  # 首次买入日期
    holding_ids: list[int]  # 关联的持仓记录ID


@dataclass
class TransactionResult:
    """交易结果"""
    success: bool
    message: str
    transaction_id: Optional[int] = None
    realized_profit: Optional[Decimal] = None  # 卖出时的实现盈亏


def get_all_holdings(db: Session) -> list[Holding]:
    """获取所有持仓（含基金信息）"""
    stmt = (
        select(Holding)
        .options(joinedload(Holding.fund))
        .order_by(Holding.buy_date.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_holding_by_id(db: Session, holding_id: int) -> Optional[Holding]:
    """根据ID获取持仓"""
    stmt = select(Holding).options(joinedload(Holding.fund)).where(Holding.id == holding_id)
    return db.execute(stmt).scalar_one_or_none()


def get_holdings_by_fund(db: Session, fund_id: int) -> list[Holding]:
    """获取某只基金的所有持仓"""
    stmt = (
        select(Holding)
        .options(joinedload(Holding.fund))
        .where(Holding.fund_id == fund_id)
        .order_by(Holding.buy_date.asc())
    )
    return list(db.execute(stmt).scalars().all())


def get_position_summary(db: Session, fund_id: int) -> Optional[PositionSummary]:
    """获取某只基金的持仓汇总"""
    holdings = get_holdings_by_fund(db, fund_id)
    if not holdings:
        return None

    fund = holdings[0].fund
    total_shares = sum(h.shares for h in holdings)
    total_cost = sum(h.total_cost for h in holdings)
    avg_cost = total_cost / total_shares if total_shares > 0 else Decimal("0")
    first_buy_date = min(h.buy_date for h in holdings)

    return PositionSummary(
        fund_id=fund.id,
        fund_code=fund.code,
        fund_name=fund.name,
        fund_type=fund.fund_type.value,
        total_shares=total_shares,
        avg_cost=avg_cost.quantize(Decimal("0.0001")),
        total_cost=total_cost,
        first_buy_date=first_buy_date,
        holding_ids=[h.id for h in holdings],
    )


def get_all_position_summaries(db: Session) -> list[PositionSummary]:
    """获取所有基金的持仓汇总"""
    # 获取所有持有基金的ID
    stmt = select(Holding.fund_id).distinct()
    fund_ids = [row[0] for row in db.execute(stmt).all()]

    summaries = []
    for fund_id in fund_ids:
        summary = get_position_summary(db, fund_id)
        if summary and summary.total_shares > 0:
            summaries.append(summary)

    return summaries


def create_holding(
    db: Session,
    fund_id: int,
    shares: Decimal,
    cost_price: Decimal,
    buy_date: date,
    is_auto_invest: bool = False,
    notes: str = None,
) -> Holding:
    """创建持仓记录"""
    holding = Holding(
        fund_id=fund_id,
        shares=shares,
        cost_price=cost_price,
        buy_date=buy_date,
        is_auto_invest=is_auto_invest,
        notes=notes,
    )
    db.add(holding)
    db.flush()
    return holding


def add_position(
    db: Session,
    fund_id: int,
    shares: Decimal,
    price: Decimal,
    trans_date: date,
    fee: Decimal = Decimal("0"),
    notes: str = None,
) -> TransactionResult:
    """
    加仓操作

    新增份额，重新计算平均成本。

    参数:
        fund_id: 基金ID
        shares: 买入份额
        price: 买入单价
        trans_date: 交易日期
        fee: 手续费
        notes: 备注

    返回:
        TransactionResult
    """
    if shares <= 0:
        return TransactionResult(success=False, message="买入份额必须大于0")
    if price <= 0:
        return TransactionResult(success=False, message="买入单价必须大于0")

    # 计算交易金额
    amount = shares * price + fee

    # 获取当前持仓
    current_summary = get_position_summary(db, fund_id)

    if current_summary:
        # 已有持仓，计算新的平均成本
        old_total_shares = current_summary.total_shares
        old_total_cost = current_summary.total_cost
        new_total_shares = old_total_shares + shares
        new_total_cost = old_total_cost + amount
        new_avg_cost = new_total_cost / new_total_shares
    else:
        # 新建仓
        new_total_shares = shares
        new_total_cost = amount
        new_avg_cost = price + (fee / shares if shares > 0 else Decimal("0"))

    # 创建新的持仓记录
    holding = create_holding(
        db,
        fund_id=fund_id,
        shares=shares,
        cost_price=price,
        buy_date=trans_date,
        is_auto_invest=False,
        notes=notes,
    )

    # 记录交易流水
    transaction = Transaction(
        fund_id=fund_id,
        trans_type=TransactionType.BUY,
        shares=shares,
        price=price,
        amount=amount,
        fee=fee,
        trans_date=trans_date,
        shares_after=new_total_shares,
        cost_after=new_avg_cost.quantize(Decimal("0.0001")),
        notes=notes,
    )
    db.add(transaction)
    db.flush()

    return TransactionResult(
        success=True,
        message=f"加仓成功：买入 {shares} 份，成本 {price}，当前持有 {new_total_shares} 份",
        transaction_id=transaction.id,
    )


def reduce_position(
    db: Session,
    fund_id: int,
    shares: Decimal,
    price: Decimal,
    trans_date: date,
    fee: Decimal = Decimal("0"),
    notes: str = None,
) -> TransactionResult:
    """
    减仓操作

    卖出份额，计算实现盈亏。采用先进先出法（FIFO）扣减持仓。

    参数:
        fund_id: 基金ID
        shares: 卖出份额
        price: 卖出单价
        trans_date: 交易日期
        fee: 手续费
        notes: 备注

    返回:
        TransactionResult（含实现盈亏）
    """
    if shares <= 0:
        return TransactionResult(success=False, message="卖出份额必须大于0")
    if price <= 0:
        return TransactionResult(success=False, message="卖出单价必须大于0")

    # 获取当前持仓
    current_summary = get_position_summary(db, fund_id)
    if not current_summary:
        return TransactionResult(success=False, message="该基金无持仓")

    if shares > current_summary.total_shares:
        return TransactionResult(
            success=False,
            message=f"卖出份额 {shares} 超过持有份额 {current_summary.total_shares}"
        )

    # 计算卖出金额和实现盈亏
    amount = shares * price - fee
    cost_basis = shares * current_summary.avg_cost
    realized_profit = amount - cost_basis

    # 采用FIFO扣减持仓
    holdings = get_holdings_by_fund(db, fund_id)
    remaining_to_sell = shares

    for holding in holdings:
        if remaining_to_sell <= 0:
            break

        if holding.shares <= remaining_to_sell:
            # 全部卖出这笔持仓
            remaining_to_sell -= holding.shares
            db.delete(holding)
        else:
            # 部分卖出
            holding.shares -= remaining_to_sell
            remaining_to_sell = Decimal("0")

    db.flush()

    # 计算卖出后的持仓情况
    new_summary = get_position_summary(db, fund_id)
    new_total_shares = new_summary.total_shares if new_summary else Decimal("0")
    new_avg_cost = new_summary.avg_cost if new_summary else Decimal("0")

    # 记录交易流水
    transaction = Transaction(
        fund_id=fund_id,
        trans_type=TransactionType.SELL,
        shares=shares,
        price=price,
        amount=amount,
        fee=fee,
        trans_date=trans_date,
        shares_after=new_total_shares,
        cost_after=new_avg_cost,
        notes=notes,
    )
    db.add(transaction)
    db.flush()

    profit_str = f"+{realized_profit:.2f}" if realized_profit >= 0 else f"{realized_profit:.2f}"

    return TransactionResult(
        success=True,
        message=f"减仓成功：卖出 {shares} 份，单价 {price}，实现盈亏 {profit_str}",
        transaction_id=transaction.id,
        realized_profit=realized_profit,
    )


def clear_position(db: Session, fund_id: int, price: Decimal, trans_date: date, fee: Decimal = Decimal("0"), notes: str = None) -> TransactionResult:
    """
    清仓操作

    卖出全部份额。
    """
    current_summary = get_position_summary(db, fund_id)
    if not current_summary:
        return TransactionResult(success=False, message="该基金无持仓")

    return reduce_position(
        db,
        fund_id=fund_id,
        shares=current_summary.total_shares,
        price=price,
        trans_date=trans_date,
        fee=fee,
        notes=notes or "清仓",
    )


def get_transactions(db: Session, fund_id: Optional[int] = None, limit: int = 50) -> list[Transaction]:
    """获取交易记录"""
    stmt = (
        select(Transaction)
        .options(joinedload(Transaction.fund))
        .order_by(Transaction.trans_date.desc(), Transaction.id.desc())
        .limit(limit)
    )
    if fund_id:
        stmt = stmt.where(Transaction.fund_id == fund_id)
    return list(db.execute(stmt).scalars().all())


def delete_holding(db: Session, holding_id: int) -> bool:
    """删除单笔持仓记录"""
    holding = db.get(Holding, holding_id)
    if holding:
        db.delete(holding)
        return True
    return False


def import_holdings_from_csv(db: Session, csv_content: str) -> ImportResult:
    """
    从CSV导入持仓数据

    CSV格式要求：
    - 必须包含表头
    - 必填字段：fund_code, fund_name, shares, cost_price, buy_date
    - 可选字段：is_auto_invest, notes

    日期格式：YYYY-MM-DD
    """
    result = ImportResult()

    try:
        reader = csv.DictReader(io.StringIO(csv_content))
    except Exception as e:
        result.errors.append(f"CSV解析失败: {str(e)}")
        return result

    # 检查必填字段
    required_fields = {"fund_code", "fund_name", "shares", "cost_price", "buy_date"}
    if reader.fieldnames is None:
        result.errors.append("CSV文件为空或格式错误")
        return result

    missing_fields = required_fields - set(reader.fieldnames)
    if missing_fields:
        result.errors.append(f"缺少必填字段: {', '.join(missing_fields)}")
        return result

    for row_num, row in enumerate(reader, start=2):
        try:
            # 解析数据
            fund_code = row["fund_code"].strip()
            fund_name = row["fund_name"].strip()

            if not fund_code or not fund_name:
                result.errors.append(f"第{row_num}行: 基金代码或名称为空")
                result.fail_count += 1
                continue

            # 解析份额
            try:
                shares = Decimal(row["shares"].strip())
                if shares <= 0:
                    result.errors.append(f"第{row_num}行: 份额必须大于0")
                    result.fail_count += 1
                    continue
            except InvalidOperation:
                result.errors.append(f"第{row_num}行: 份额格式错误")
                result.fail_count += 1
                continue

            # 解析成本价
            try:
                cost_price = Decimal(row["cost_price"].strip())
                if cost_price <= 0:
                    result.errors.append(f"第{row_num}行: 成本价必须大于0")
                    result.fail_count += 1
                    continue
            except InvalidOperation:
                result.errors.append(f"第{row_num}行: 成本价格式错误")
                result.fail_count += 1
                continue

            # 解析日期
            try:
                buy_date_str = row["buy_date"].strip()
                buy_date_val = date.fromisoformat(buy_date_str)
            except ValueError:
                result.errors.append(f"第{row_num}行: 日期格式错误，应为YYYY-MM-DD")
                result.fail_count += 1
                continue

            # 解析可选字段
            is_auto_invest = row.get("is_auto_invest", "").strip().lower() in ("true", "1", "是", "yes")
            notes = row.get("notes", "").strip() or None

            # 获取或创建基金
            fund, _ = get_or_create_fund(db, fund_code, fund_name, FundType.OTHER)

            # 创建持仓（使用加仓逻辑记录交易）
            add_position(
                db,
                fund_id=fund.id,
                shares=shares,
                price=cost_price,
                trans_date=buy_date_val,
                notes=notes,
            )
            result.success_count += 1

        except Exception as e:
            result.errors.append(f"第{row_num}行: {str(e)}")
            result.fail_count += 1

    return result


def get_csv_template() -> str:
    """返回CSV导入模板"""
    return """fund_code,fund_name,shares,cost_price,buy_date,is_auto_invest,notes
000001,华夏成长混合,1000.00,1.2500,2024-01-15,false,示例数据
110011,易方达中小盘混合,500.00,2.3400,2024-02-20,true,定投"""
