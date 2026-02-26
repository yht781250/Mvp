"""
数据库初始化脚本

功能：
1. 创建所有数据库表
2. 可选：插入测试数据进行验证
"""

import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.data import (
    ChatRole,
    Fund,
    FundType,
    Holding,
    NavHistory,
    Report,
    Signal,
    SignalLevel,
    get_db_context,
    init_db,
)


def create_tables() -> None:
    """创建所有数据库表"""
    print("正在创建数据库表...")
    init_db()
    print("数据库表创建完成！")


def init_default_roles() -> None:
    """初始化默认AI对话角色"""
    print("\n正在检查AI对话角色...")
    with get_db_context() as db:
        from app.services import chat_service
        chat_service.init_default_roles(db)
        role_count = db.query(ChatRole).count()
        print(f"  AI对话角色：{role_count} 个")


def insert_test_data() -> None:
    """插入测试数据"""
    print("\n正在插入测试数据...")

    with get_db_context() as db:
        # 检查是否已有数据
        existing = db.query(Fund).first()
        if existing:
            print("数据库已有数据，跳过测试数据插入")
            return

        # 1. 插入测试基金
        test_funds = [
            Fund(
                code="000001",
                name="华夏成长混合",
                fund_type=FundType.HYBRID,
                manager="张三",
                company="华夏基金",
                establish_date=date(2015, 1, 1),
                scale=Decimal("120.50"),
                fee_rate=Decimal("0.0150"),
                is_favorite=True,
                group_name="核心持仓",
                notes="长期持有的混合基金",
            ),
            Fund(
                code="110011",
                name="易方达沪深300ETF联接",
                fund_type=FundType.INDEX,
                manager="李四",
                company="易方达",
                establish_date=date(2018, 6, 1),
                scale=Decimal("85.30"),
                fee_rate=Decimal("0.0050"),
                is_favorite=True,
                group_name="指数配置",
                notes="宽基指数定投",
            ),
            Fund(
                code="003003",
                name="招商中证白酒指数",
                fund_type=FundType.INDEX,
                manager="王五",
                company="招商基金",
                establish_date=date(2019, 3, 15),
                scale=Decimal("320.00"),
                fee_rate=Decimal("0.0100"),
                is_favorite=False,
                group_name="行业配置",
            ),
        ]

        for fund in test_funds:
            db.add(fund)
        db.flush()  # 获取自动生成的 ID

        print(f"  插入 {len(test_funds)} 只测试基金")

        # 2. 插入持仓数据
        holdings = [
            Holding(
                fund_id=test_funds[0].id,
                shares=Decimal("5000.00"),
                cost_price=Decimal("1.2500"),
                buy_date=date(2023, 1, 15),
                is_auto_invest=False,
                notes="一次性买入",
            ),
            Holding(
                fund_id=test_funds[1].id,
                shares=Decimal("3000.00"),
                cost_price=Decimal("1.5200"),
                buy_date=date(2023, 6, 1),
                is_auto_invest=True,
                notes="每月定投500",
            ),
            Holding(
                fund_id=test_funds[2].id,
                shares=Decimal("1000.00"),
                cost_price=Decimal("2.1000"),
                buy_date=date(2024, 1, 10),
                is_auto_invest=False,
            ),
        ]

        for h in holdings:
            db.add(h)
        print(f"  插入 {len(holdings)} 条持仓记录")

        # 3. 插入净值历史
        nav_records = [
            NavHistory(
                fund_id=test_funds[0].id,
                nav_date=date(2025, 2, 7),
                nav=Decimal("1.3200"),
                acc_nav=Decimal("3.5600"),
                daily_return=Decimal("0.76"),
            ),
            NavHistory(
                fund_id=test_funds[0].id,
                nav_date=date(2025, 2, 10),
                nav=Decimal("1.3350"),
                acc_nav=Decimal("3.5750"),
                daily_return=Decimal("1.14"),
            ),
            NavHistory(
                fund_id=test_funds[1].id,
                nav_date=date(2025, 2, 10),
                nav=Decimal("1.6100"),
                acc_nav=Decimal("1.6100"),
                daily_return=Decimal("0.56"),
            ),
        ]

        for nav in nav_records:
            db.add(nav)
        print(f"  插入 {len(nav_records)} 条净值记录")

        # 4. 插入预警信号
        signals = [
            Signal(
                fund_id=test_funds[2].id,
                rule_name="concentration_risk",
                level=SignalLevel.ATTENTION,
                title="行业集中度提醒",
                description="白酒指数基金属于单一行业暴露，需关注行业周期风险",
                trigger_value="行业占比100%",
                threshold_value="单行业>30%",
                suggestion="建议控制单一行业基金占比不超过总仓位的20%",
            ),
        ]

        for sig in signals:
            db.add(sig)
        print(f"  插入 {len(signals)} 条预警信号")

        # 5. 插入示例报告
        report = Report(
            report_type="daily",
            report_date=date(2025, 2, 10),
            title="2025年2月10日持仓日报",
            summary="今日组合整体上涨0.82%，跑赢沪深300指数0.25个百分点。",
            content="""
## 今日概览
- 组合总收益：+0.82%
- 基准对比：+0.25%（vs 沪深300）
- 最大贡献：华夏成长混合 +1.14%
- 最大拖累：无

## 持仓变化
各基金净值正常更新，无异常波动。

## 风险提示
白酒指数基金行业集中度较高，建议关注。
            """.strip(),
            risk_warning="以上分析仅供研究参考，不构成投资建议。基金投资有风险，入市需谨慎。",
        )
        db.add(report)
        print("  插入 1 份示例报告")

    print("测试数据插入完成！")


def verify_data() -> None:
    """验证数据库数据"""
    print("\n正在验证数据...")

    with get_db_context() as db:
        # 统计各表数据
        fund_count = db.query(Fund).count()
        holding_count = db.query(Holding).count()
        nav_count = db.query(NavHistory).count()
        signal_count = db.query(Signal).count()
        report_count = db.query(Report).count()
        role_count = db.query(ChatRole).count()

        print(f"  funds 表：{fund_count} 条")
        print(f"  holdings 表：{holding_count} 条")
        print(f"  nav_history 表：{nav_count} 条")
        print(f"  signals 表：{signal_count} 条")
        print(f"  reports 表：{report_count} 条")
        print(f"  chat_roles 表：{role_count} 条")

        # 查询示例
        if fund_count > 0:
            fund = db.query(Fund).first()
            print(f"\n  示例查询 - 第一只基金：{fund.code} {fund.name}")

            # 关联查询
            if fund.holdings:
                h = fund.holdings[0]
                print(f"  关联持仓：{h.shares} 份，成本 {h.cost_price}")

    print("\n验证完成！数据库工作正常。")


def main() -> None:
    """主函数"""
    print("=" * 50)
    print("AI基金分析助手 - 数据库初始化")
    print("=" * 50)

    # 1. 创建表
    create_tables()

    # 1.5 初始化默认角色
    init_default_roles()

    # 2. 询问是否插入测试数据
    if len(sys.argv) > 1 and sys.argv[1] == "--with-test-data":
        insert_test_data()
    else:
        print("\n提示：使用 --with-test-data 参数可插入测试数据")

    # 3. 验证
    verify_data()

    print("\n" + "=" * 50)
    print("初始化完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
