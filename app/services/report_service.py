"""
日报生成服务

生成每日投资观察报告，包含专业投资建议，输出为 Markdown 文件。
"""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.settings import settings
from app.data.models import Fund
from app.services import fund_service, holding_service, nav_service, metrics_service, rules_engine, llm_service, risk_analysis_service


def generate_daily_report(db: Session, use_llm: bool = True) -> tuple[str, str]:
    """
    生成每日投资报告（含专业投资建议）

    参数:
        db: 数据库会话
        use_llm: 是否使用 LLM 生成分析内容

    返回:
        (报告内容, 文件路径)
    """
    today = date.today()
    report_date = today.strftime("%Y-%m-%d")

    # 获取持仓数据
    holdings = holding_service.get_all_holdings(db)

    if not holdings:
        return "暂无持仓数据", ""

    # 计算组合指标
    portfolio_metrics = metrics_service.calculate_portfolio_metrics(db, holdings)
    allocation = metrics_service.get_asset_allocation(holdings)

    # 运行规则检查
    rule_results = rules_engine.run_all_rules(db)

    # 获取各基金指标
    fund_metrics_list = []
    fund_ids = set(h.fund_id for h in holdings)
    for fund_id in fund_ids:
        fund = fund_service.get_fund_by_id(db, fund_id)
        if fund:
            metrics = metrics_service.calculate_fund_metrics(db, fund, days=30)
            fund_metrics_list.append(metrics)

    # 获取投资建议
    investment_advice = risk_analysis_service.generate_portfolio_investment_advice(db)

    # 构建报告内容
    report_lines = []

    # 标题
    report_lines.append(f"# 📊 每日投资观察报告")
    report_lines.append(f"")
    report_lines.append(f"**日期**：{report_date}")
    report_lines.append(f"**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"")

    # ========== 投资建议摘要（最重要，放在最前面）==========
    report_lines.append(f"## 💡 今日投资建议")
    report_lines.append(f"")

    if investment_advice:
        # 整体情绪和观点
        sentiment_icons = {
            "乐观": "🟢",
            "偏乐观": "🟢",
            "中性": "🟡",
            "偏谨慎": "🟠",
            "谨慎": "🔴",
        }
        sentiment_icon = sentiment_icons.get(investment_advice.overall_sentiment, "⚪")

        report_lines.append(f"### 📈 整体观点：{sentiment_icon} {investment_advice.overall_sentiment}")
        report_lines.append(f"")
        report_lines.append(f"> {investment_advice.market_view}")
        report_lines.append(f"")

        # 核心要点
        report_lines.append(f"### 🎯 核心要点")
        report_lines.append(f"")
        for point in investment_advice.key_points:
            report_lines.append(f"- {point}")
        report_lines.append(f"")

        # 组合操作建议
        report_lines.append(f"### 📋 组合操作建议")
        report_lines.append(f"")
        report_lines.append(f"**{investment_advice.portfolio_action}**")
        report_lines.append(f"")

        # 各基金具体建议
        report_lines.append(f"### 📊 各基金操作建议")
        report_lines.append(f"")
        report_lines.append(f"| 基金 | 操作建议 | 理由 | 建议仓位 | 风险等级 |")
        report_lines.append(f"|------|----------|------|----------|----------|")

        for advice in investment_advice.fund_advices:
            action_text = f"{advice.action_icon} {advice.action.value}"
            report_lines.append(f"| {advice.fund_name[:8]} | {action_text} | {advice.action_reason} | {advice.suggested_ratio} | {advice.risk_level.value} |")
        report_lines.append(f"")

        # 加仓推荐详情
        if investment_advice.buy_recommendations:
            report_lines.append(f"### 🟢 加仓推荐")
            report_lines.append(f"")
            for advice in investment_advice.buy_recommendations:
                report_lines.append(f"#### {advice.fund_name}（{advice.fund_code}）")
                report_lines.append(f"")
                report_lines.append(f"**最新净值**：¥{advice.current_nav:.4f}（{advice.nav_date}）")
                report_lines.append(f"")
                report_lines.append(f"**技术分析**：{advice.trend_analysis}")
                report_lines.append(f"")
                report_lines.append(f"**技术信号**：{' | '.join(advice.technical_signals)}")
                report_lines.append(f"")
                report_lines.append(f"**操作理由**：")
                for detail in advice.action_details:
                    report_lines.append(f"- {detail}")
                report_lines.append(f"")
                report_lines.append(f"**操作参考**：{advice.suggested_ratio}，{advice.time_horizon}")
                report_lines.append(f"")
                report_lines.append(f"**价格参考**：{advice.price_reference}")
                report_lines.append(f"")

        # 减仓提醒详情
        if investment_advice.sell_recommendations:
            report_lines.append(f"### 🔴 减仓提醒")
            report_lines.append(f"")
            for advice in investment_advice.sell_recommendations:
                report_lines.append(f"#### {advice.fund_name}（{advice.fund_code}）")
                report_lines.append(f"")
                report_lines.append(f"**最新净值**：¥{advice.current_nav:.4f}（{advice.nav_date}）")
                report_lines.append(f"")
                report_lines.append(f"**技术分析**：{advice.trend_analysis}")
                report_lines.append(f"")
                report_lines.append(f"**风险信号**：")
                for warning in advice.risk_warnings[:3]:
                    report_lines.append(f"- ⚠️ {warning}")
                report_lines.append(f"")
                report_lines.append(f"**操作参考**：{advice.suggested_ratio}，{advice.time_horizon}")
                report_lines.append(f"")

        # 持有观察
        if investment_advice.hold_recommendations:
            report_lines.append(f"### 🟡 建议持有观察")
            report_lines.append(f"")
            for advice in investment_advice.hold_recommendations:
                report_lines.append(f"- **{advice.fund_name}**：{advice.action_reason}。{advice.action_details[0] if advice.action_details else ''}")
            report_lines.append(f"")

    else:
        report_lines.append(f"⚠️ 净值数据不足，无法生成投资建议。请先更新基金净值数据。")
        report_lines.append(f"")

    # ========== 组合概况 ==========
    report_lines.append(f"---")
    report_lines.append(f"")
    report_lines.append(f"## 💼 组合概况")
    report_lines.append(f"")
    report_lines.append(f"| 指标 | 数值 |")
    report_lines.append(f"|------|------|")
    report_lines.append(f"| 持仓基金 | {portfolio_metrics.fund_count} 只 |")
    report_lines.append(f"| 持仓笔数 | {portfolio_metrics.holding_count} 笔 |")
    report_lines.append(f"| 总成本 | ¥{portfolio_metrics.total_cost:,.2f} |")

    if portfolio_metrics.total_value:
        report_lines.append(f"| 总市值 | ¥{portfolio_metrics.total_value:,.2f} |")
        report_lines.append(f"| 累计收益 | ¥{portfolio_metrics.total_value - portfolio_metrics.total_cost:,.2f} ({portfolio_metrics.total_return:+.2f}%) |")

    if portfolio_metrics.top3_concentration:
        report_lines.append(f"| 前3大持仓占比 | {portfolio_metrics.top3_concentration:.1f}% |")

    report_lines.append(f"")

    # 资产配置
    if allocation:
        type_names = {
            "stock": "股票型",
            "bond": "债券型",
            "hybrid": "混合型",
            "money": "货币型",
            "index": "指数型",
            "qdii": "QDII",
            "other": "其他",
        }
        report_lines.append(f"## 🎯 资产配置")
        report_lines.append(f"")
        for fund_type, pct in sorted(allocation.items(), key=lambda x: -x[1]):
            type_name = type_names.get(fund_type, fund_type)
            report_lines.append(f"- {type_name}：{pct:.1f}%")
        report_lines.append(f"")

    # 基金指标
    if fund_metrics_list:
        report_lines.append(f"## 📉 风险指标")
        report_lines.append(f"")
        report_lines.append(f"| 基金 | 区间收益 | 波动率 | 最大回撤 | 夏普比率 |")
        report_lines.append(f"|------|----------|--------|----------|----------|")
        for m in fund_metrics_list:
            period_ret = f"{m.period_return:.2f}%" if m.period_return is not None else "-"
            vol = f"{m.annualized_volatility:.2f}%" if m.annualized_volatility is not None else "-"
            mdd = f"{m.max_drawdown:.2f}%" if m.max_drawdown is not None else "-"
            sharpe = f"{m.sharpe_ratio:.2f}" if m.sharpe_ratio is not None else "-"
            report_lines.append(f"| {m.fund_name[:10]} | {period_ret} | {vol} | {mdd} | {sharpe} |")
        report_lines.append(f"")

    # 风险预警
    report_lines.append(f"## 🚨 风险预警")
    report_lines.append(f"")
    if rule_results:
        for r in rule_results:
            level_icons = {
                "critical": "🔴",
                "warning": "🟠",
                "attention": "🟡",
                "info": "🔵",
            }
            icon = level_icons.get(r.level.value, "⚪")
            report_lines.append(f"### {icon} {r.title}")
            report_lines.append(f"")
            report_lines.append(f"**诊断**：{r.diagnosis}")
            report_lines.append(f"")
            report_lines.append(f"**建议**：{r.suggestion}")
            report_lines.append(f"")
    else:
        report_lines.append(f"✅ 当前组合未触发任何风险预警规则。")
        report_lines.append(f"")

    # AI 分析（可选）
    if use_llm and llm_service.is_llm_configured():
        report_lines.append(f"## 🤖 AI 深度分析")
        report_lines.append(f"")

        # 构建更丰富的 prompt 上下文
        advice_summary = ""
        if investment_advice:
            advice_summary = f"投资建议摘要：{investment_advice.overall_sentiment}，{investment_advice.portfolio_action}。"
            if investment_advice.buy_recommendations:
                buy_names = [a.fund_name for a in investment_advice.buy_recommendations]
                advice_summary += f"建议加仓：{', '.join(buy_names)}。"
            if investment_advice.sell_recommendations:
                sell_names = [a.fund_name for a in investment_advice.sell_recommendations]
                advice_summary += f"建议减仓：{', '.join(sell_names)}。"

        portfolio_summary = f"持仓 {portfolio_metrics.fund_count} 只基金，总成本 ¥{portfolio_metrics.total_cost:,.2f}。{advice_summary}"
        response = llm_service.generate_analysis_summary(portfolio_summary, rule_results)

        if response.success:
            report_lines.append(response.content)
        else:
            report_lines.append(f"*AI 分析生成失败：{response.error}*")
        report_lines.append(f"")

    # 风险提示
    report_lines.append(f"---")
    report_lines.append(f"")
    report_lines.append(f"## ⚠️ 风险提示")
    report_lines.append(f"")
    if investment_advice:
        for reminder in investment_advice.risk_reminders:
            report_lines.append(f"- {reminder}")
    else:
        report_lines.append(f"- 历史业绩不代表未来表现，基金投资有风险。")
        report_lines.append(f"- 本报告仅为研究辅助，不构成投资建议。")
        report_lines.append(f"- 具体操作需结合个人风险承受能力和资金安排。")
    report_lines.append(f"")
    report_lines.append(f"---")
    report_lines.append(f"*由 AI基金分析助手 自动生成*")

    # 组合报告内容
    report_content = "\n".join(report_lines)

    # 保存到文件
    reports_dir = Path(settings.sqlite_path).parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    report_path = reports_dir / f"{report_date}.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    return report_content, str(report_path)
