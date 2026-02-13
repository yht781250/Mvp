"""
Streamlit 主页面 - 养基宝风格 UI

包含：组合总览、持仓管理、风险分析、净值查询等
淡蓝白色金融主题设计
"""

import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.core.settings import settings
from app.data.database import get_db_context, init_db
from app.data.models import FundType
from app.services import (
    fund_service, holding_service, nav_service, metrics_service,
    rules_engine, llm_service, report_service, risk_analysis_service,
)
from app.services.fund_data_fetcher import fetch_fund_info, fetch_nav_history
from app.ui.styles import (
    apply_custom_theme, render_hero_card, render_fund_card,
    render_section_header, render_empty_state, render_holding_card,
    render_page_header, render_stat_card,
)


# ============================================================
# 数据获取函数
# ============================================================

def get_holdings_data():
    """获取持仓数据（在session内提取所有需要的字段）"""
    with get_db_context() as db:
        holdings = holding_service.get_all_holdings(db)
        data = []
        for h in holdings:
            data.append({
                "id": h.id,
                "fund_code": h.fund.code,
                "fund_name": h.fund.name,
                "fund_type": h.fund.fund_type.value,
                "shares": h.shares,
                "cost_price": h.cost_price,
                "total_cost": h.total_cost,
                "buy_date": h.buy_date,
                "is_auto_invest": h.is_auto_invest,
                "notes": h.notes,
            })
        return data


def get_position_summaries_data():
    """获取按基金汇总的持仓数据（同一基金合并显示）"""
    with get_db_context() as db:
        summaries = holding_service.get_all_position_summaries(db)
        data = []
        for s in summaries:
            data.append({
                "fund_id": s.fund_id,
                "fund_code": s.fund_code,
                "fund_name": s.fund_name,
                "fund_type": s.fund_type,
                "total_shares": s.total_shares,
                "avg_cost": s.avg_cost,
                "total_cost": s.total_cost,
                "first_buy_date": s.first_buy_date,
            })
        return data


# ============================================================
# 初始化
# ============================================================

init_db()

st.set_page_config(
    page_title="AI基金分析助手",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#x1F4C8;</text></svg>",
    layout="wide",
)

# 应用自定义主题
apply_custom_theme()

# 显示消息提示
if "message" in st.session_state:
    msg = st.session_state.pop("message")
    if msg["type"] == "success":
        st.success(msg["text"])
    elif msg["type"] == "error":
        st.error(msg["text"])
    elif msg["type"] == "warning":
        st.warning(msg["text"])

# ============================================================
# 侧边栏导航
# ============================================================

with st.sidebar:
    st.markdown(
        '<div style="padding:1rem 0.5rem 1.2rem 0.5rem; margin-bottom:0.5rem;">'
        '<div style="font-size:1.3rem; font-weight:700; color:#2C3E50;">AI基金助手</div>'
        '<div style="font-size:0.78rem; color:#A0AEC0; margin-top:4px;">个人基金研究与风控辅助</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    page = st.radio(
        "导航",
        ["组合总览", "智能分析", "持仓管理", "净值数据", "导入持仓", "系统设置"],
        label_visibility="collapsed",
    )

    st.markdown(
        '<div style="margin-top:1.5rem; padding:0.8rem; background:#FFF9E6; border-radius:10px; border:1px solid #F5E6B8; font-size:0.78rem; color:#92700E; line-height:1.5;">'
        '<div style="font-weight:600; margin-bottom:4px;">风险提示</div>'
        '历史业绩不代表未来表现，投资有风险，入市需谨慎。系统输出仅为研究辅助。'
        '</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# 组合总览页面
# ============================================================

if page == "组合总览":
    summaries_data = get_position_summaries_data()

    if not summaries_data:
        render_page_header("组合总览", "您的基金组合一目了然")
        render_empty_state("暂无持仓数据", "请先在「持仓管理」中添加您的基金持仓")
    else:
        # 获取数据库净值
        fund_nav_data = {}
        with get_db_context() as db:
            for s in summaries_data:
                code = s["fund_code"]
                fund = fund_service.get_fund_by_code(db, code)
                if fund:
                    nav_list = nav_service.get_nav_history(db, fund.id, limit=2)
                    if nav_list:
                        fund_nav_data[code] = {
                            "nav": float(nav_list[0].nav),
                            "nav_date": nav_list[0].nav_date,
                            "daily_return": float(nav_list[0].daily_return) if nav_list[0].daily_return else 0,
                            "prev_nav": float(nav_list[1].nav) if len(nav_list) > 1 else None,
                        }

        # 实时估值缓存
        if "realtime_cache" not in st.session_state:
            st.session_state["realtime_cache"] = {"data": {}, "update_time": None}

        cache = st.session_state["realtime_cache"]
        cache_valid = False
        if cache["update_time"]:
            cache_age = datetime.now() - cache["update_time"]
            if cache_age < timedelta(minutes=5) and cache["data"]:
                cache_valid = True

        # 获取实时估值
        realtime_data = {}
        col_r1, col_r2 = st.columns([1, 5])
        with col_r1:
            refresh_btn = st.button("刷新估值", use_container_width=True)
        with col_r2:
            if cache["update_time"]:
                t_str = cache["update_time"].strftime("%H:%M:%S")
                st.caption(f"上次更新：{t_str}" + ("（缓存有效）" if cache_valid else "（已过期）"))
            else:
                st.caption("点击按钮获取今日实时估值")

        if refresh_btn or (not cache_valid and not cache["data"]):
            if refresh_btn or not cache["data"]:
                with st.spinner("获取实时估值中..."):
                    for s in summaries_data:
                        code = s["fund_code"]
                        try:
                            fund_info = fetch_fund_info(code)
                            if fund_info and fund_info.day_growth is not None:
                                realtime_data[code] = {
                                    "day_growth": float(fund_info.day_growth),
                                    "est_nav": float(fund_info.nav) if fund_info.nav else None,
                                }
                        except Exception:
                            pass
                    st.session_state["realtime_cache"] = {
                        "data": realtime_data,
                        "update_time": datetime.now(),
                    }
        else:
            realtime_data = cache["data"]

        # 计算收益
        total_cost = Decimal("0")
        total_value = Decimal("0")
        total_yesterday_profit = Decimal("0")
        total_today_profit = Decimal("0")
        display_items = []

        for s in summaries_data:
            code = s["fund_code"]
            shares = s["total_shares"]
            cost = s["total_cost"]
            total_cost += cost

            nav_info = fund_nav_data.get(code)
            realtime_info = realtime_data.get(code)

            item = {
                "fund_code": code,
                "fund_name": s["fund_name"],
                "shares": shares,
                "avg_cost": s["avg_cost"],
                "total_cost": cost,
            }

            if nav_info:
                current_nav = Decimal(str(nav_info["nav"]))
                market_value = shares * current_nav
                total_value += market_value
                profit = market_value - cost
                profit_rate = float(profit / cost * 100) if cost > 0 else 0

                yesterday_return = nav_info["daily_return"]
                if nav_info.get("prev_nav"):
                    yesterday_profit = shares * Decimal(str(nav_info["prev_nav"])) * Decimal(str(yesterday_return / 100))
                else:
                    yesterday_profit = Decimal("0")
                total_yesterday_profit += yesterday_profit

                if realtime_info:
                    today_growth = realtime_info["day_growth"]
                    today_profit = shares * current_nav * Decimal(str(today_growth / 100))
                    total_today_profit += today_profit
                else:
                    today_growth = None
                    today_profit = None

                item.update({
                    "current_nav": float(current_nav),
                    "nav_date": nav_info["nav_date"],
                    "market_value": float(market_value),
                    "profit": float(profit),
                    "profit_rate": profit_rate,
                    "yesterday_return": yesterday_return,
                    "today_growth": today_growth,
                    "today_profit": float(today_profit) if today_profit is not None else None,
                })
            else:
                item.update({
                    "current_nav": None,
                    "nav_date": None,
                    "market_value": None,
                    "profit": None,
                    "profit_rate": None,
                    "yesterday_return": None,
                    "today_growth": None,
                    "today_profit": None,
                })

            display_items.append(item)

        # 计算组合指标
        total_profit = total_value - total_cost if total_value > 0 else Decimal("0")
        total_profit_rate = float(total_profit / total_cost * 100) if total_cost > 0 else 0
        yesterday_profit_rate = float(total_yesterday_profit / (total_value - total_yesterday_profit) * 100) if total_value > total_yesterday_profit else 0
        today_profit_rate = float(total_today_profit / total_value * 100) if total_value > 0 and total_today_profit != 0 else 0

        # Hero 资产总览卡片
        render_hero_card(
            total_value=float(total_value),
            total_cost=float(total_cost),
            total_profit=float(total_profit),
            total_profit_rate=total_profit_rate,
            yesterday_profit=float(total_yesterday_profit),
            yesterday_rate=yesterday_profit_rate,
            today_profit=float(total_today_profit),
            today_rate=today_profit_rate,
        )

        # 提示信息
        if not fund_nav_data:
            st.warning("暂无净值数据，请先到「净值数据」页面更新基金净值")
        elif len(fund_nav_data) < len(summaries_data):
            missing = [s["fund_code"] for s in summaries_data if s["fund_code"] not in fund_nav_data]
            st.caption(f"提示：{', '.join(missing)} 暂无净值数据")

        if realtime_data:
            st.caption("今日估值为实时数据，仅供参考，以收盘后净值为准")

        # 基金卡片列表
        render_section_header("我的持仓", f"共 {len(display_items)} 只基金")

        for item in display_items:
            render_fund_card(
                fund_name=item["fund_name"],
                fund_code=item["fund_code"],
                market_value=item["market_value"] if item["market_value"] else 0,
                total_cost=float(item["total_cost"]),
                profit=item["profit"] if item["profit"] is not None else 0,
                profit_rate=item["profit_rate"] if item["profit_rate"] is not None else 0,
                shares=item["shares"],
                avg_cost=item["avg_cost"],
                current_nav=item["current_nav"] if item["current_nav"] else "-",
                nav_date=item["nav_date"].strftime("%m-%d") if item["nav_date"] else "-",
                yesterday_return=item["yesterday_return"] if item["yesterday_return"] else 0,
                today_growth=item["today_growth"],
            )


# ============================================================
# 智能分析页面
# ============================================================

elif page == "智能分析":
    render_page_header("智能分析", "技术指标分析 / AI投资建议 / 日报生成")

    holdings_data = get_holdings_data()

    if not holdings_data:
        render_empty_state("暂无持仓数据", "请先在「持仓管理」中添加持仓")
    else:
        tab1, tab2, tab3 = st.tabs(["技术指标", "AI建议", "生成日报"])

        # ===== 技术指标分析 =====
        with tab1:
            render_section_header("技术指标趋势分析", "基于MA均线、RSI、动量等指标的量化分析")

            with get_db_context() as db:
                portfolio_forecast = risk_analysis_service.forecast_portfolio_risk(db)

            if not portfolio_forecast:
                st.warning("暂无足够的净值数据进行分析，请先到「净值数据」页面更新（建议至少30天数据）")
            else:
                risk_colors = {
                    risk_analysis_service.RiskLevel.LOW: "🟢",
                    risk_analysis_service.RiskLevel.MEDIUM_LOW: "🟡",
                    risk_analysis_service.RiskLevel.MEDIUM: "🟠",
                    risk_analysis_service.RiskLevel.MEDIUM_HIGH: "🔴",
                    risk_analysis_service.RiskLevel.HIGH: "🔴",
                }

                # 风险概览卡片
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    risk_icon = risk_colors.get(portfolio_forecast.overall_risk_level, "⚪")
                    st.metric("整体风险", f"{risk_icon} {portfolio_forecast.overall_risk_level.value}")
                with col2:
                    st.metric("风险评分", f"{portfolio_forecast.overall_risk_score}/100")
                with col3:
                    st.metric("看涨基金", portfolio_forecast.bullish_funds)
                with col4:
                    st.metric("看跌基金", portfolio_forecast.bearish_funds)

                st.info(portfolio_forecast.risk_description)
                st.divider()

                # 风险预警
                render_section_header("风险预警")
                for warning in portfolio_forecast.warnings:
                    if "✓" in warning:
                        st.success(warning)
                    else:
                        st.warning(warning)

                st.divider()

                # 各基金趋势预测
                render_section_header("各基金趋势预测")

                trend_colors = {
                    risk_analysis_service.TrendDirection.STRONG_UP: "🟢",
                    risk_analysis_service.TrendDirection.UP: "🟢",
                    risk_analysis_service.TrendDirection.SIDEWAYS: "🟡",
                    risk_analysis_service.TrendDirection.DOWN: "🔴",
                    risk_analysis_service.TrendDirection.STRONG_DOWN: "🔴",
                }

                for forecast in portfolio_forecast.fund_forecasts:
                    trend_icon = trend_colors.get(forecast.trend, "⚪")
                    risk_icon = risk_colors.get(forecast.risk_level, "⚪")

                    with st.expander(
                        f"{trend_icon} {forecast.fund_name}（{forecast.fund_code}）- {forecast.trend.value}",
                        expanded=(forecast.risk_level in [risk_analysis_service.RiskLevel.HIGH, risk_analysis_service.RiskLevel.MEDIUM_HIGH])
                    ):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.markdown("**基本信息**")
                            st.write(f"当前净值：{forecast.current_nav}")
                            st.write(f"净值日期：{forecast.nav_date}")
                            st.write(f"风险等级：{risk_icon} {forecast.risk_level.value}")
                            st.write(f"风险评分：{forecast.risk_score}/100")

                        with col2:
                            st.markdown("**趋势分析**")
                            st.write(f"趋势方向：{trend_icon} {forecast.trend.value}")
                            st.write(f"趋势强度：{forecast.trend_strength}/100")
                            st.write(f"波动趋势：{forecast.volatility_trend}")
                            if forecast.support_level:
                                st.write(f"支撑位：{forecast.support_level}")
                            if forecast.resistance_level:
                                st.write(f"阻力位：{forecast.resistance_level}")

                        with col3:
                            st.markdown("**预测与建议**")
                            st.write(f"预期走向：{forecast.forecast_direction}")
                            st.write(f"预测置信度：{forecast.confidence}%")

                        st.divider()
                        st.markdown("**趋势解读**")
                        st.info(forecast.trend_description)

                        st.markdown("**风险因素**")
                        for factor in forecast.risk_factors:
                            st.write(f"- {factor}")

                        st.markdown("**技术面建议**")
                        st.success(forecast.suggestion)

                # 指标说明
                with st.expander("技术指标说明"):
                    st.markdown("""
                    | 指标 | 说明 | 应用 |
                    |------|------|------|
                    | **MA** | 5日/10日/20日均线 | 判断趋势方向和支撑阻力 |
                    | **RSI** | 0-100，衡量超买超卖 | >70超买，<30超卖 |
                    | **动量** | 价格变化速度 | 判断趋势强度 |
                    | **波动率** | 近期vs历史波动 | 判断风险变化 |
                    """)

                st.caption("以上分析基于历史数据和技术指标，仅供参考，不构成投资建议。")

        # ===== AI投资建议 =====
        with tab2:
            render_section_header("AI独立投资建议", "将原始数据提供给AI独立分析（含今日实时估值）")

            if not llm_service.is_llm_configured():
                st.warning("AI功能未配置，请在「系统设置 → LLM配置」中设置")
            else:
                st.caption(f"当前模型：{settings.llm_model}")

                # 收集原始数据
                with get_db_context() as db:
                    summaries = holding_service.get_all_position_summaries(db)

                    raw_data_text = "## 当前持仓数据\n\n"
                    raw_data_text += "| 基金名称 | 基金代码 | 持有份额 | 平均成本 | 总成本 |\n"
                    raw_data_text += "|----------|----------|----------|----------|--------|\n"

                    fund_nav_details = []

                    for s in summaries:
                        raw_data_text += f"| {s.fund_name} | {s.fund_code} | {s.total_shares:.2f} | {s.avg_cost:.4f} | {s.total_cost:.2f} |\n"

                        fund = fund_service.get_fund_by_code(db, s.fund_code)
                        if fund:
                            nav_list = nav_service.get_nav_history(db, fund.id, limit=30)
                            if nav_list:
                                current_nav = float(nav_list[0].nav)
                                market_value = float(s.total_shares) * current_nav
                                profit = market_value - float(s.total_cost)
                                profit_rate = profit / float(s.total_cost) * 100 if s.total_cost > 0 else 0

                                nav_changes = []
                                for n in nav_list[:7]:
                                    if n.daily_return:
                                        nav_changes.append(f"{n.nav_date}: {float(n.daily_return):+.2f}%")

                                fund_nav_details.append({
                                    "name": s.fund_name,
                                    "code": s.fund_code,
                                    "shares": float(s.total_shares),
                                    "current_nav": current_nav,
                                    "nav_date": nav_list[0].nav_date,
                                    "market_value": market_value,
                                    "profit": profit,
                                    "profit_rate": profit_rate,
                                    "recent_changes": nav_changes,
                                })

                    raw_data_text += "\n## 最新净值与收益（昨日收盘数据）\n\n"
                    raw_data_text += "| 基金名称 | 最新净值 | 净值日期 | 当前市值 | 持仓收益 | 收益率 |\n"
                    raw_data_text += "|----------|----------|----------|----------|----------|--------|\n"

                    for d in fund_nav_details:
                        raw_data_text += f"| {d['name']} | {d['current_nav']:.4f} | {d['nav_date']} | {d['market_value']:.2f} | {d['profit']:+.2f} | {d['profit_rate']:+.2f}% |\n"

                # 获取实时估值
                rt_data = {}
                total_td_profit = 0
                with st.spinner("获取实时估值中..."):
                    for d in fund_nav_details:
                        code = d["code"]
                        try:
                            fund_info = fetch_fund_info(code)
                            if fund_info and fund_info.day_growth is not None:
                                today_growth = float(fund_info.day_growth)
                                today_profit = d["shares"] * d["current_nav"] * (today_growth / 100)
                                total_td_profit += today_profit
                                rt_data[code] = {
                                    "day_growth": today_growth,
                                    "est_nav": float(fund_info.nav) if fund_info.nav else None,
                                    "today_profit": today_profit,
                                }
                        except Exception:
                            pass

                if rt_data:
                    current_time = datetime.now().strftime("%H:%M")
                    raw_data_text += f"\n## 今日实时估值（更新时间：{current_time}）\n\n"
                    raw_data_text += "| 基金名称 | 今日估值涨跌% | 估算净值 | 今日预计收益 |\n"
                    raw_data_text += "|----------|---------------|----------|-------------|\n"

                    for d in fund_nav_details:
                        code = d["code"]
                        if code in rt_data:
                            r = rt_data[code]
                            est_nav_str = f"{r['est_nav']:.4f}" if r['est_nav'] else "-"
                            raw_data_text += f"| {d['name']} | {r['day_growth']:+.2f}% | {est_nav_str} | {r['today_profit']:+.2f} |\n"
                        else:
                            raw_data_text += f"| {d['name']} | - | - | - |\n"

                    raw_data_text += f"\n**今日组合预计总收益：{total_td_profit:+.2f} 元**\n"
                else:
                    raw_data_text += "\n## 今日实时估值\n\n暂无实时数据（可能是非交易时间）\n"

                raw_data_text += "\n## 近7日涨跌记录\n\n"
                for d in fund_nav_details:
                    raw_data_text += f"### {d['name']}（{d['code']}）\n"
                    if d['recent_changes']:
                        for change in d['recent_changes']:
                            raw_data_text += f"- {change}\n"
                    else:
                        raw_data_text += "- 暂无近期数据\n"
                    raw_data_text += "\n"

                with st.expander("查看将发送给AI的原始数据"):
                    st.markdown(raw_data_text)

                st.divider()

                if st.button("请AI分析并给出投资建议", use_container_width=True, type="primary"):
                    with st.spinner("AI正在独立分析中..."):
                        from openai import OpenAI

                        client = OpenAI(
                            base_url=settings.llm_base_url,
                            api_key=settings.llm_api_key,
                        )

                        prompt = f"""你是一位资深的基金投资顾问，请根据以下投资者的持仓数据，独立分析并给出专业的投资建议。

{raw_data_text}

请从以下几个角度进行**独立分析**（不要依赖任何预设结论）：

1. **持仓分析** - 资产配置是否合理？各基金盈亏情况？
2. **今日盘中分析** - 今日走势如何？是否有收盘前操作建议？
3. **市场判断** - 近7日趋势？异常波动？
4. **投资建议** - 加仓/减仓/持有的明确建议
5. **风险提示** - 主要风险点
6. **总结** - 一句话今日建议 + 一句话中期策略

请用专业但易懂的语言回答，给出具体、可操作的建议。"""

                        try:
                            response = client.chat.completions.create(
                                model=settings.llm_model,
                                messages=[
                                    {"role": "system", "content": "你是一位专业的基金投资顾问。请根据用户提供的原始持仓、历史净值和今日实时估值数据，进行独立分析，给出客观、专业、具体的投资建议。"},
                                    {"role": "user", "content": prompt}
                                ],
                                temperature=0.5,
                                max_tokens=2500,
                            )
                            ai_analysis = response.choices[0].message.content

                            st.divider()
                            render_section_header("AI投资建议")
                            st.markdown(ai_analysis)

                            st.divider()
                            st.caption(f"以上建议由 {settings.llm_model} 基于原始数据独立分析生成")
                            st.caption("AI建议仅供参考，不构成投资建议。投资有风险，入市需谨慎。")

                        except Exception as e:
                            st.error(f"AI分析失败：{str(e)}")

        # ===== 生成日报 =====
        with tab3:
            render_section_header("生成每日投资报告", "一键生成包含技术分析的完整日报")

            col1, col2 = st.columns(2)
            with col1:
                use_llm = st.checkbox(
                    "在日报中启用AI分析",
                    value=llm_service.is_llm_configured(),
                    disabled=not llm_service.is_llm_configured(),
                    help="在日报中加入AI分析内容"
                )
                if not llm_service.is_llm_configured():
                    st.caption("配置 LLM 后可启用")

            with col2:
                st.markdown("**日报将包含：**")
                st.caption("- 组合概况与市值")
                st.caption("- 技术指标分析")
                st.caption("- 风险预警信号")
                st.caption("- 操作建议参考")
                if use_llm:
                    st.caption("- AI综合分析")

            st.divider()

            if st.button("生成每日报告", use_container_width=True, type="primary"):
                with st.spinner("正在生成报告..."):
                    with get_db_context() as db:
                        report_content, report_path = report_service.generate_daily_report(db, use_llm=use_llm)

                if report_content and report_path:
                    st.success("报告生成成功！")
                    st.caption(f"已保存到：{report_path}")

                    st.divider()
                    render_section_header("报告预览")
                    st.markdown(report_content)

                    st.divider()
                    st.download_button(
                        label="下载 Markdown 文件",
                        data=report_content,
                        file_name=report_path.split("/")[-1] if "/" in report_path else report_path.split("\\")[-1],
                        mime="text/markdown",
                        use_container_width=True,
                    )
                elif report_content == "暂无持仓数据":
                    st.warning("暂无持仓数据，无法生成报告")
                else:
                    st.error("报告生成失败，请检查数据")

            st.divider()

            # 历史报告
            render_section_header("历史报告")

            from pathlib import Path
            reports_dir = Path(settings.sqlite_path).parent.parent / "reports"

            if reports_dir.exists():
                report_files = sorted(reports_dir.glob("*.md"), reverse=True)
                if report_files:
                    for f in report_files[:10]:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.write(f.stem)
                        with col2:
                            report_text = f.read_text(encoding="utf-8")
                            st.download_button(
                                label="下载",
                                data=report_text,
                                file_name=f.name,
                                mime="text/markdown",
                                key=f"dl_{f.stem}",
                            )
                else:
                    st.caption("暂无历史报告")
            else:
                st.caption("暂无历史报告")

            st.caption("报告内容仅供参考，不构成投资建议。")


# ============================================================
# 持仓管理页面
# ============================================================

elif page == "持仓管理":
    render_page_header("持仓管理", "管理您的基金持仓")

    tab1, tab2, tab3, tab4 = st.tabs(["持仓总览", "买入/加仓", "卖出/减仓", "交易记录"])

    # ===== 持仓总览 =====
    with tab1:
        with get_db_context() as db:
            summaries = holding_service.get_all_position_summaries(db)

        if not summaries:
            render_empty_state("暂无持仓数据", "请在「买入/加仓」页签添加")
        else:
            total_cost = sum(s.total_cost for s in summaries)
            total_funds = len(summaries)

            col1, col2 = st.columns(2)
            with col1:
                render_stat_card("持仓基金数", f"{total_funds} 只")
            with col2:
                render_stat_card("总投入成本", f"{total_cost:,.2f}")

            st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

            for summary in summaries:
                # 获取净值计算收益
                with get_db_context() as db:
                    nav_list = nav_service.get_nav_history(db, summary.fund_id, limit=1)
                    if nav_list:
                        current_nav = float(nav_list[0].nav)
                        market_value = float(summary.total_shares) * current_nav
                        profit = market_value - float(summary.total_cost)
                        profit_rate = profit / float(summary.total_cost) * 100 if summary.total_cost > 0 else 0

                        render_holding_card(
                            fund_name=summary.fund_name,
                            fund_code=summary.fund_code,
                            total_shares=summary.total_shares,
                            avg_cost=summary.avg_cost,
                            total_cost=summary.total_cost,
                            first_buy_date=summary.first_buy_date,
                            current_nav=current_nav,
                            nav_date=nav_list[0].nav_date,
                            market_value=market_value,
                            profit=profit,
                            profit_rate=profit_rate,
                        )
                    else:
                        render_holding_card(
                            fund_name=summary.fund_name,
                            fund_code=summary.fund_code,
                            total_shares=summary.total_shares,
                            avg_cost=summary.avg_cost,
                            total_cost=summary.total_cost,
                            first_buy_date=summary.first_buy_date,
                        )

    # ===== 加仓 =====
    with tab2:
        render_section_header("买入 / 加仓", "对新基金建仓或对已有持仓加仓，系统自动计算平均成本")

        if "fund_info" not in st.session_state:
            st.session_state["fund_info"] = None

        # 基金查询
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            input_code = st.text_input(
                "基金代码",
                placeholder="输入6位基金代码后点击查询",
                key="add_fund_code",
            )
        with col_s2:
            st.write("")
            st.write("")
            if st.button("查询", key="add_search_btn", use_container_width=True):
                if input_code and len(input_code.strip()) == 6:
                    with st.spinner("正在查询..."):
                        info = fetch_fund_info(input_code.strip())
                        if info:
                            st.session_state["fund_info"] = {
                                "code": info.code,
                                "name": info.name,
                                "nav": float(info.nav) if info.nav else None,
                                "nav_date": info.nav_date.strftime("%Y-%m-%d") if info.nav_date else None,
                            }
                        else:
                            st.session_state["fund_info"] = None
                            st.error("未找到该基金，请检查代码是否正确")
                else:
                    st.warning("请输入6位基金代码")

        fund_info = st.session_state.get("fund_info")
        if fund_info:
            st.success(f"**{fund_info['name']}**（{fund_info['code']}）")
            if fund_info.get("nav"):
                st.caption(f"最新净值：{fund_info['nav']}（{fund_info['nav_date']}）")

            with get_db_context() as db:
                existing_fund = fund_service.get_fund_by_code(db, fund_info["code"])
                if existing_fund:
                    existing_summary = holding_service.get_position_summary(db, existing_fund.id)
                    if existing_summary:
                        st.info(f"已有持仓：{existing_summary.total_shares:,.2f} 份，平均成本 {existing_summary.avg_cost:.4f}")

        st.divider()

        # 加仓输入
        default_code = fund_info["code"] if fund_info else ""
        default_name = fund_info["name"] if fund_info else ""

        col1, col2 = st.columns(2)
        with col1:
            fund_code = st.text_input("基金代码", value=default_code, disabled=bool(fund_info), key="add_fund_code_input")
            fund_name = st.text_input("基金名称", value=default_name, key="add_fund_name_input")
            fund_type = st.selectbox(
                "基金类型",
                options=[t.value for t in FundType],
                format_func=lambda x: {"stock": "股票型", "bond": "债券型", "hybrid": "混合型", "money": "货币型", "index": "指数型", "qdii": "QDII", "other": "其他"}.get(x, x),
                key="add_fund_type_input",
            )

        with col2:
            buy_shares = st.number_input("买入份额", min_value=0.01, value=1000.0, step=100.0, key="add_shares_input")
            buy_price = st.number_input("买入单价", min_value=0.0001, value=fund_info.get("nav", 1.0) if fund_info else 1.0, step=0.01, format="%.4f", key="add_price_input")
            buy_date = st.date_input("买入日期", value=date.today(), key="add_date_input")

        col1, col2 = st.columns(2)
        with col1:
            buy_fee = st.number_input("手续费", min_value=0.0, value=0.0, step=1.0, key="add_fee_input")
        with col2:
            buy_amount = buy_shares * buy_price + buy_fee
            render_stat_card("预计总金额", f"{buy_amount:,.2f}")

        notes = st.text_area("备注", placeholder="可选，记录买入原因等", key="add_notes_input")

        if st.button("确认买入", use_container_width=True, type="primary", key="add_confirm_btn"):
            final_code = fund_info["code"] if fund_info else fund_code.strip()
            final_name = fund_info["name"] if fund_info else fund_name.strip()

            if not final_code or not final_name:
                st.error("请填写基金代码和名称，或先查询基金")
            elif buy_shares <= 0 or buy_price <= 0:
                st.error("份额和单价必须大于0")
            else:
                try:
                    with get_db_context() as db:
                        fund, _ = fund_service.get_or_create_fund(db, final_code, final_name, FundType(fund_type))
                        result = holding_service.add_position(
                            db,
                            fund_id=fund.id,
                            shares=Decimal(str(buy_shares)),
                            price=Decimal(str(buy_price)),
                            trans_date=buy_date,
                            fee=Decimal(str(buy_fee)),
                            notes=notes.strip() if notes else None,
                        )
                    st.session_state["fund_info"] = None
                    if result.success:
                        st.session_state["message"] = {"type": "success", "text": f"{result.message}"}
                    else:
                        st.session_state["message"] = {"type": "error", "text": result.message}
                    st.rerun()
                except Exception as e:
                    st.error(f"操作失败：{str(e)}")

    # ===== 减仓 =====
    with tab3:
        render_section_header("卖出 / 减仓", "卖出部分或全部持仓，系统计算实现盈亏（FIFO先进先出法）")

        with get_db_context() as db:
            summaries = holding_service.get_all_position_summaries(db)

        if not summaries:
            render_empty_state("暂无持仓", "无法减仓")
        else:
            fund_options = {f"{s.fund_name}（{s.fund_code}）": s for s in summaries}
            selected_fund_label = st.selectbox("选择基金", options=list(fund_options.keys()))
            selected_summary = fund_options[selected_fund_label]

            st.info(f"当前持仓：**{selected_summary.total_shares:,.2f}** 份，平均成本 **{selected_summary.avg_cost:.4f}**，总成本 **{selected_summary.total_cost:,.2f}**")

            with get_db_context() as db:
                nav_list = nav_service.get_nav_history(db, selected_summary.fund_id, limit=1)
                default_sell_price = float(nav_list[0].nav) if nav_list else float(selected_summary.avg_cost)
                if nav_list:
                    st.caption(f"参考净值：{default_sell_price:.4f}（{nav_list[0].nav_date}）")

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                sell_shares = st.number_input(
                    "卖出份额",
                    min_value=0.01,
                    max_value=float(selected_summary.total_shares),
                    value=min(100.0, float(selected_summary.total_shares)),
                    step=100.0,
                    key="sell_shares_input"
                )
                sell_price = st.number_input("卖出单价", min_value=0.0001, value=default_sell_price, step=0.01, format="%.4f", key="sell_price_input")

            with col2:
                sell_date = st.date_input("卖出日期", value=date.today(), key="sell_date_input")
                sell_fee = st.number_input("手续费", min_value=0.0, value=0.0, step=1.0, key="sell_fee_input")

            # 预估盈亏
            sell_amount = sell_shares * sell_price - sell_fee
            cost_basis = sell_shares * float(selected_summary.avg_cost)
            est_profit = sell_amount - cost_basis

            col1, col2, col3 = st.columns(3)
            with col1:
                render_stat_card("卖出金额", f"{sell_amount:,.2f}")
            with col2:
                render_stat_card("成本基准", f"{cost_basis:,.2f}")
            with col3:
                profit_color = "#E74C3C" if est_profit >= 0 else "#27AE60"
                render_stat_card("预估盈亏", f"{est_profit:+,.2f}", color=profit_color)

            sell_notes = st.text_area("备注", placeholder="可选", key="sell_notes_input")

            col1, col2 = st.columns(2)
            with col1:
                sell_btn = st.button("确认卖出", use_container_width=True, type="primary", key="sell_confirm_btn")
            with col2:
                clear_btn = st.button("全部清仓", use_container_width=True, key="clear_confirm_btn")

            if sell_btn:
                try:
                    with get_db_context() as db:
                        result = holding_service.reduce_position(
                            db,
                            fund_id=selected_summary.fund_id,
                            shares=Decimal(str(sell_shares)),
                            price=Decimal(str(sell_price)),
                            trans_date=sell_date,
                            fee=Decimal(str(sell_fee)),
                            notes=sell_notes.strip() if sell_notes else None,
                        )
                    if result.success:
                        st.session_state["message"] = {"type": "success", "text": f"{result.message}"}
                    else:
                        st.session_state["message"] = {"type": "error", "text": result.message}
                    st.rerun()
                except Exception as e:
                    st.error(f"操作失败：{str(e)}")

            if clear_btn:
                try:
                    with get_db_context() as db:
                        result = holding_service.clear_position(
                            db,
                            fund_id=selected_summary.fund_id,
                            price=Decimal(str(sell_price)),
                            trans_date=sell_date,
                            fee=Decimal(str(sell_fee)),
                            notes="清仓",
                        )
                    if result.success:
                        st.session_state["message"] = {"type": "success", "text": f"清仓成功！{result.message}"}
                    else:
                        st.session_state["message"] = {"type": "error", "text": result.message}
                    st.rerun()
                except Exception as e:
                    st.error(f"操作失败：{str(e)}")

    # ===== 交易记录 =====
    with tab4:
        render_section_header("交易记录", "最近50笔交易流水")

        with get_db_context() as db:
            transactions = holding_service.get_transactions(db, limit=50)
            from app.data.models import TransactionType
            trans_data = []
            buy_count = 0
            sell_count = 0
            for t in transactions:
                is_buy = t.trans_type == TransactionType.BUY
                trans_type_name = "买入" if is_buy else "卖出"
                if is_buy:
                    buy_count += 1
                else:
                    sell_count += 1
                trans_data.append({
                    "日期": t.trans_date,
                    "类型": trans_type_name,
                    "基金": t.fund.name,
                    "份额": float(t.shares),
                    "单价": float(t.price),
                    "金额": float(t.amount),
                    "手续费": float(t.fee),
                    "交易后份额": float(t.shares_after),
                    "交易后成本": float(t.cost_after),
                })

        if not trans_data:
            render_empty_state("暂无交易记录")
        else:
            df = pd.DataFrame(trans_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                render_stat_card("买入次数", str(buy_count))
            with col2:
                render_stat_card("卖出次数", str(sell_count))


# ============================================================
# 净值数据页面
# ============================================================

elif page == "净值数据":
    render_page_header("净值数据", "查询和更新基金净值")

    tab1, tab2 = st.tabs(["查询净值", "更新净值"])

    with tab1:
        render_section_header("按基金代码查询净值")

        col1, col2 = st.columns([3, 1])
        with col1:
            query_code = st.text_input(
                "基金代码",
                placeholder="输入6位基金代码",
                key="nav_query_code",
            )
        with col2:
            st.write("")
            st.write("")
            query_btn = st.button("查询", key="nav_query_btn", use_container_width=True)

        if query_btn and query_code:
            code = query_code.strip()
            if len(code) != 6:
                st.warning("请输入6位基金代码")
            else:
                with st.spinner("正在查询..."):
                    fund_info = fetch_fund_info(code)
                    if not fund_info:
                        st.error(f"未找到基金：{code}")
                    else:
                        st.success(f"**{fund_info.name}**（{fund_info.code}）")

                        if fund_info.nav:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                render_stat_card("最新净值", f"{fund_info.nav:.4f}")
                            with col2:
                                render_stat_card("净值日期", fund_info.nav_date.strftime("%Y-%m-%d") if fund_info.nav_date else "-")
                            with col3:
                                day_val = fund_info.day_growth
                                if day_val:
                                    color = "#E74C3C" if float(day_val) > 0 else "#27AE60"
                                    render_stat_card("日涨跌", f"{day_val}%", color=color)
                                else:
                                    render_stat_card("日涨跌", "-")

                        st.divider()

                        render_section_header("近30日净值走势")
                        nav_records = fetch_nav_history(code, limit=30)

                        if nav_records:
                            nav_data = []
                            for r in nav_records:
                                nav_data.append({
                                    "日期": r.nav_date,
                                    "单位净值": float(r.nav),
                                    "累计净值": float(r.acc_nav) if r.acc_nav else None,
                                    "日涨跌%": float(r.day_growth) if r.day_growth else None,
                                })
                            df = pd.DataFrame(nav_data)

                            df_chart = df.sort_values("日期")
                            st.line_chart(df_chart.set_index("日期")["单位净值"])

                            st.dataframe(df, use_container_width=True, hide_index=True)
                        else:
                            st.caption("暂无历史净值数据")

    with tab2:
        render_section_header("更新持仓基金净值", "从网络获取最新净值并保存到本地数据库")

        holdings_data = get_holdings_data()
        fund_codes = list(set(h["fund_code"] for h in holdings_data))

        if not fund_codes:
            render_empty_state("暂无持仓基金", "请先添加持仓")
        else:
            st.write(f"当前持仓 **{len(fund_codes)}** 只基金")

            for code in fund_codes:
                fund_names = [h["fund_name"] for h in holdings_data if h["fund_code"] == code]
                st.write(f"- {code} - {fund_names[0]}")

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                days = st.number_input("获取天数", min_value=7, max_value=365, value=30, step=7)

            if st.button("更新所有基金净值", use_container_width=True, type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()

                results = {}
                for i, code in enumerate(fund_codes):
                    status_text.text(f"正在更新：{code}...")
                    progress_bar.progress((i + 1) / len(fund_codes))

                    try:
                        with get_db_context() as db:
                            fund = fund_service.get_fund_by_code(db, code)
                            if fund:
                                count = nav_service.update_fund_nav(db, fund, days=days)
                                results[code] = count
                            else:
                                results[code] = -1
                    except Exception:
                        results[code] = -1

                status_text.empty()
                progress_bar.empty()

                success_count = sum(1 for v in results.values() if v > 0)
                fail_count = sum(1 for v in results.values() if v < 0)

                if success_count > 0:
                    st.success(f"成功更新 {success_count} 只基金的净值")
                if fail_count > 0:
                    st.warning(f"{fail_count} 只基金更新失败")

                with st.expander("查看详情"):
                    for code, count in results.items():
                        if count > 0:
                            st.write(f"- {code}: 更新 {count} 条记录")
                        else:
                            st.write(f"- {code}: 更新失败")

        st.divider()

        # 已保存数据
        render_section_header("已保存的净值数据")

        if fund_codes:
            selected_code = st.selectbox("选择基金", fund_codes)

            if selected_code:
                with get_db_context() as db:
                    fund = fund_service.get_fund_by_code(db, selected_code)
                    if fund:
                        nav_list = nav_service.get_nav_history(db, fund.id, limit=30)
                        if nav_list:
                            saved_data = []
                            for n in nav_list:
                                saved_data.append({
                                    "日期": n.nav_date,
                                    "单位净值": float(n.nav),
                                    "累计净值": float(n.acc_nav) if n.acc_nav else None,
                                    "日涨跌%": float(n.daily_return) if n.daily_return else None,
                                })
                            st.dataframe(pd.DataFrame(saved_data), use_container_width=True, hide_index=True)
                        else:
                            st.caption("该基金暂无已保存的净值数据")


# ============================================================
# 导入持仓页面
# ============================================================

elif page == "导入持仓":
    render_page_header("CSV 导入持仓", "批量导入基金持仓数据")

    st.markdown(
        '<div style="background:#FFFFFF; border-radius:12px; padding:1.2rem 1.5rem; border:1px solid #E8EDF2; margin-bottom:1rem; font-size:0.9rem; color:#4A5568; line-height:1.8;">'
        '<div style="font-weight:600; color:#2C3E50; margin-bottom:0.5rem;">CSV 格式要求</div>'
        '<div>必填字段：fund_code, fund_name, shares, cost_price, buy_date</div>'
        '<div>可选字段：is_auto_invest, notes</div>'
        '<div>日期格式：YYYY-MM-DD</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    template = holding_service.get_csv_template()
    st.download_button(
        "下载CSV模板",
        data=template,
        file_name="holding_template.csv",
        mime="text/csv",
    )

    st.divider()

    uploaded_file = st.file_uploader("上传CSV文件", type=["csv"])

    if uploaded_file is not None:
        try:
            content = uploaded_file.read().decode("utf-8")
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            content = uploaded_file.read().decode("gbk")

        st.text_area("文件预览", content, height=150, disabled=True)

        if st.button("开始导入", use_container_width=True, type="primary"):
            with get_db_context() as db:
                result = holding_service.import_holdings_from_csv(db, content)

            if result.success_count > 0:
                st.success(f"成功导入 {result.success_count} 条记录")
            if result.fail_count > 0:
                st.warning(f"失败 {result.fail_count} 条")
            if result.errors:
                with st.expander("查看错误详情"):
                    for err in result.errors:
                        st.error(err)


# ============================================================
# 系统设置页面
# ============================================================

elif page == "系统设置":
    render_page_header("系统设置", "应用配置和LLM管理")

    tab1, tab2 = st.tabs(["基本信息", "LLM配置"])

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            render_section_header("应用配置")
            st.write(f"**应用名称**: {settings.app_name}")
            st.write(f"**版本**: {settings.app_version}")
            st.write(f"**数据库**: {settings.database_url}")

        with col2:
            render_section_header("当前LLM状态")
            if settings.llm_base_url:
                st.write(f"**API地址**: {settings.llm_base_url}")
                st.write(f"**模型**: {settings.llm_model or '未配置'}")
                st.write(f"**API密钥**: {'已配置' if settings.llm_api_key else '未配置'}")
                if settings.llm_base_url and settings.llm_api_key and settings.llm_model:
                    st.success("LLM 已配置完成")
                else:
                    st.warning("LLM 配置不完整")
            else:
                st.info("LLM未配置，请在「LLM配置」页签中设置")

    with tab2:
        render_section_header("LLM 配置管理", "配置 OpenAI 兼容的大语言模型接口")

        from app.services import llm_config_service

        current_config = llm_config_service.get_current_config()

        if "llm_models" not in st.session_state:
            st.session_state["llm_models"] = current_config.available_models or []
        if "llm_test_result" not in st.session_state:
            st.session_state["llm_test_result"] = None

        st.divider()

        st.markdown("**第一步：API 配置**")

        api_base_url = st.text_input(
            "API 地址",
            value=current_config.base_url,
            placeholder="例如: https://api.openai.com/v1",
            help="OpenAI 兼容的 API 基础地址",
            key="llm_api_url_input",
        )

        api_key = st.text_input(
            "API 密钥",
            value=current_config.api_key,
            type="password",
            placeholder="输入您的 API Key",
            key="llm_api_key_input",
        )

        st.divider()

        st.markdown("**第二步：选择模型**")

        col1, col2 = st.columns([1, 3])

        with col1:
            if st.button("获取模型列表", use_container_width=True):
                if not api_base_url or not api_key:
                    st.error("请先填写 API 地址和密钥")
                else:
                    with st.spinner("正在获取模型列表..."):
                        models, error = llm_config_service.fetch_available_models(
                            api_base_url.strip(),
                            api_key.strip(),
                        )
                    if error:
                        st.error(error)
                        st.session_state["llm_models"] = []
                    else:
                        model_ids = [m.id for m in models]
                        st.session_state["llm_models"] = model_ids
                        st.success(f"成功获取 {len(model_ids)} 个可用模型")

        with col2:
            available_models = st.session_state.get("llm_models", [])

            if available_models:
                default_index = 0
                if current_config.model in available_models:
                    default_index = available_models.index(current_config.model)

                selected_model = st.selectbox(
                    "选择模型",
                    options=available_models,
                    index=default_index,
                    key="llm_model_select",
                )
            else:
                selected_model = st.text_input(
                    "模型名称",
                    value=current_config.model,
                    placeholder="手动输入或点击左侧按钮获取列表",
                    key="llm_model_manual",
                )

        if available_models:
            with st.expander(f"查看全部 {len(available_models)} 个可用模型"):
                for i, model_id in enumerate(available_models, 1):
                    st.write(f"{i}. `{model_id}`")

        st.divider()

        st.markdown("**第三步：测试与保存**")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("测试连接", use_container_width=True):
                if not api_base_url or not api_key or not selected_model:
                    st.error("请填写完整的配置信息")
                else:
                    with st.spinner("正在测试连接..."):
                        success, message = llm_config_service.test_connection(
                            api_base_url.strip(),
                            api_key.strip(),
                            selected_model.strip() if selected_model else "",
                        )
                    st.session_state["llm_test_result"] = (success, message)

        with col2:
            if st.button("保存配置", use_container_width=True, type="primary"):
                if not api_base_url or not api_key:
                    st.error("请至少填写 API 地址和密钥")
                else:
                    new_config = llm_config_service.LLMConfig(
                        base_url=api_base_url.strip(),
                        api_key=api_key.strip(),
                        model=selected_model.strip() if selected_model else "",
                        available_models=st.session_state.get("llm_models", []),
                    )

                    if llm_config_service.save_config(new_config):
                        llm_config_service.update_current_config(new_config)
                        st.session_state["message"] = {"type": "success", "text": "LLM 配置已保存"}
                        st.rerun()
                    else:
                        st.error("保存配置失败")

        with col3:
            if st.button("清除配置", use_container_width=True):
                empty_config = llm_config_service.LLMConfig()
                if llm_config_service.save_config(empty_config):
                    llm_config_service.update_current_config(empty_config)
                    st.session_state["llm_models"] = []
                    st.session_state["llm_test_result"] = None
                    st.session_state["message"] = {"type": "warning", "text": "LLM 配置已清除"}
                    st.rerun()

        test_result = st.session_state.get("llm_test_result")
        if test_result:
            success, message = test_result
            if success:
                st.success(message)
            else:
                st.error(message)

        st.divider()

        with st.expander("配置说明"):
            st.markdown("""
            ### 支持的 API 服务

            | 服务商 | API 地址示例 |
            |--------|-------------|
            | OpenAI | `https://api.openai.com/v1` |
            | 智谱AI | `https://open.bigmodel.cn/api/paas/v4` |
            | 月之暗面 | `https://api.moonshot.cn/v1` |
            | DeepSeek | `https://api.deepseek.com/v1` |
            | 阿里云百炼 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
            | 本地 Ollama | `http://localhost:11434/v1` |

            ### 使用步骤
            1. 填写 API 地址
            2. 填写 API 密钥
            3. 获取模型列表
            4. 选择模型
            5. 测试连接
            6. 保存配置

            ### 注意
            - 配置保存在 `data/llm_config.json`
            - 如果同时存在 `.env` 配置，本页面配置优先
            """)
