"""
Streamlit 自定义样式配置

淡蓝白色金融主题设计（养基宝风格）
- 主色调：#4A90D9（蓝色）
- 辅助色：#6CB2EB（浅蓝）
- 背景色：#F5F7FA（极浅蓝灰）
- 卡片色：#FFFFFF（纯白）
- 涨色：#E74C3C（红色）
- 跌色：#27AE60（绿色）

响应式设计：
- 桌面端（>1024px）：完整布局
- 平板端（768px-1024px）：适度调整
- 手机端（<768px）：垂直布局、增大触摸区域
"""

import streamlit as st
from decimal import Decimal


def apply_custom_theme():
    """应��淡蓝白色金融主题（含完整响应式支持）"""

    custom_css = """
    <style>
    /* ===== 全局基础 ===== */
    .stApp {
        background-color: #F5F7FA;
    }

    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    /* 隐藏默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ===== 侧边栏 ===== */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E8EDF2;
    }

    section[data-testid="stSidebar"] .stRadio > label {
        font-size: 0.9rem;
        font-weight: 600;
        color: #7B8B9E;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }

    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        padding: 0.7rem 1rem;
        border-radius: 10px;
        margin-bottom: 2px;
        transition: all 0.2s ease;
        font-size: 0.95rem;
    }

    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
        background-color: #F0F4F8;
    }

    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label[data-checked="true"] {
        background-color: #EBF3FD;
        color: #4A90D9;
    }

    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label[data-checked="true"] p {
        color: #4A90D9;
        font-weight: 600;
    }

    /* ===== 标题 ===== */
    h1 {
        color: #2C3E50 !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.3px;
    }

    h2 {
        color: #34495E;
        font-size: 1.2rem;
        font-weight: 600;
    }

    h3 {
        color: #4A5568;
        font-size: 1.05rem;
        font-weight: 600;
    }

    /* ===== Metric 卡片 ===== */
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        border: 1px solid #E8EDF2;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }

    [data-testid="stMetric"] > label {
        font-size: 0.8rem;
        color: #7B8B9E;
        font-weight: 500;
    }

    [data-testid="stMetric"] > div {
        font-size: 1.3rem;
        font-weight: 700;
        color: #2C3E50;
    }

    /* ===== 按钮 ===== */
    .stButton button {
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.9rem;
        transition: all 0.2s ease;
        border: 1px solid transparent;
        min-height: 44px;
    }

    .stButton button[kind="primary"] {
        background-color: #4A90D9;
        color: white;
        border-color: #3A80C9;
    }

    .stButton button[kind="primary"]:hover {
        background-color: #3A80C9;
        box-shadow: 0 2px 8px rgba(74,144,217,0.3);
    }

    .stButton button[kind="secondary"] {
        background-color: #FFFFFF;
        color: #4A5568;
        border-color: #D1D9E0;
    }

    .stButton button[kind="secondary"]:hover {
        background-color: #F5F7FA;
        border-color: #4A90D9;
        color: #4A90D9;
    }

    /* ===== Tab 标签 ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background-color: #F0F4F8;
        border-radius: 12px;
        padding: 4px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 0.55rem 1.2rem;
        font-weight: 500;
        color: #7B8B9E;
        font-size: 0.9rem;
        min-height: 44px;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #4A90D9;
        background-color: #E8EFF8;
    }

    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #4A90D9 !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }

    /* ===== 数据表格 ===== */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #E8EDF2;
    }

    /* ===== 输入框 ===== */
    .stTextInput input,
    .stNumberInput input {
        border-radius: 10px;
        border: 1px solid #D1D9E0;
        font-size: 0.95rem;
        min-height: 44px;
    }

    .stTextInput input:focus,
    .stNumberInput input:focus {
        border-color: #4A90D9;
        box-shadow: 0 0 0 2px rgba(74,144,217,0.15);
    }

    .stTextInput label,
    .stNumberInput label,
    .stSelectbox label,
    .stDateInput label {
        font-weight: 500;
        color: #4A5568;
        font-size: 0.88rem;
    }

    /* ===== 选择框 ===== */
    .stSelectbox div[data-baseweb="select"] > div {
        border-radius: 10px;
        border: 1px solid #D1D9E0;
        min-height: 44px;
    }

    .stSelectbox div[data-baseweb="select"] > div:focus-within {
        border-color: #4A90D9;
        box-shadow: 0 0 0 2px rgba(74,144,217,0.15);
    }

    /* ===== 日期输入 ===== */
    .stDateInput input {
        border-radius: 10px;
        border: 1px solid #D1D9E0;
        min-height: 44px;
    }

    .stDateInput input:focus {
        border-color: #4A90D9;
        box-shadow: 0 0 0 2px rgba(74,144,217,0.15);
    }

    /* ===== 文本区域 ===== */
    .stTextArea textarea {
        border-radius: 10px;
        border: 1px solid #D1D9E0;
    }

    .stTextArea textarea:focus {
        border-color: #4A90D9;
        box-shadow: 0 0 0 2px rgba(74,144,217,0.15);
    }

    /* ===== 信息提示 ===== */
    .stSuccess {
        border-radius: 10px;
    }
    .stWarning {
        border-radius: 10px;
    }
    .stError {
        border-radius: 10px;
    }
    .stInfo {
        border-radius: 10px;
    }

    /* ===== 展开面板 ===== */
    .streamlit-expanderHeader {
        background-color: #FFFFFF;
        border: 1px solid #E8EDF2;
        border-radius: 12px;
        font-weight: 500;
        color: #4A5568;
        min-height: 48px;
    }

    .streamlit-expanderHeader:hover {
        background-color: #F5F7FA;
        border-color: #4A90D9;
    }

    /* ===== 分隔线 ===== */
    hr {
        border-top: 1px solid #E8EDF2;
        margin: 1.2rem 0;
    }

    /* ===== 文件上传 ===== */
    .stFileUploader {
        border: 2px dashed #D1D9E0;
        border-radius: 12px;
        background-color: #FAFBFC;
    }

    .stFileUploader:hover {
        border-color: #4A90D9;
        background-color: #F0F4F8;
    }

    /* ===== 下载按钮 ===== */
    .stDownloadButton button {
        background-color: #FFFFFF;
        color: #4A90D9;
        border: 1px solid #4A90D9;
        min-height: 44px;
    }

    .stDownloadButton button:hover {
        background-color: #EBF3FD;
    }

    /* ===== 进度条 ===== */
    .stProgress > div > div > div {
        background-color: #4A90D9;
    }

    .stProgress > div > div {
        background-color: #E8EDF2;
    }

    /* ===== 滚动条 ===== */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }

    ::-webkit-scrollbar-track {
        background: #F0F4F8;
        border-radius: 3px;
    }

    ::-webkit-scrollbar-thumb {
        background: #C1CCD8;
        border-radius: 3px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #A0B0C0;
    }

    /* ===== 链接 ===== */
    .stMarkdown a {
        color: #4A90D9;
        text-decoration: none;
    }

    .stMarkdown a:hover {
        color: #3A80C9;
        text-decoration: underline;
    }

    /* ===== 表格标题 ===== */
    .stMarkdown table th {
        background-color: #F5F7FA;
        color: #4A5568;
        font-weight: 600;
    }

    .stMarkdown table td {
        border-bottom: 1px solid #E8EDF2;
    }

    /* ===== 平板端响应式（768px - 1024px）===== */
    @media (max-width: 1024px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }

        h1 { font-size: 1.4rem !important; }

        .stTabs [data-baseweb="tab"] {
            padding: 0.5rem 1rem;
            font-size: 0.85rem;
        }
    }

    /* ===== 手机端响应式（<768px）===== */
    @media (max-width: 768px) {
        /* 全局调整 */
        .main .block-container {
            padding-left: 0.6rem;
            padding-right: 0.6rem;
            padding-top: 1rem;
        }

        h1 { font-size: 1.25rem !important; }
        h2 { font-size: 1.05rem; }
        h3 { font-size: 0.95rem; }

        /* 按钮触摸区域 */
        .stButton button {
            min-height: 48px;
            font-size: 0.95rem;
        }

        /* Tab 标签紧凑化 */
        .stTabs [data-baseweb="tab-list"] {
            border-radius: 10px;
            padding: 3px;
        }

        .stTabs [data-baseweb="tab"] {
            padding: 0.5rem 0.8rem;
            font-size: 0.8rem;
            min-height: 44px;
        }

        /* 输入框触摸友好 */
        .stTextInput input,
        .stNumberInput input,
        .stDateInput input {
            min-height: 48px;
            font-size: 1rem;
        }

        .stSelectbox div[data-baseweb="select"] > div {
            min-height: 48px;
        }

        /* Metric 卡片紧凑 */
        [data-testid="stMetric"] {
            padding: 0.8rem 1rem;
        }

        [data-testid="stMetric"] > div {
            font-size: 1.1rem;
        }

        /* 数据表格横向滚动提示 */
        .stDataFrame::before {
            content: "← 左右滑动查看更多 →";
            display: block;
            text-align: center;
            font-size: 0.75rem;
            color: #A0AEC0;
            padding: 0.3rem 0;
            background: #F5F7FA;
        }

        /* 侧边栏优化 */
        section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
            padding: 0.8rem 1rem;
            font-size: 1rem;
            min-height: 48px;
        }

        /* 展开面板触摸友好 */
        .streamlit-expanderHeader {
            min-height: 52px;
            font-size: 0.95rem;
        }
    }

    /* ===== 小屏手机（<480px）===== */
    @media (max-width: 480px) {
        .main .block-container {
            padding-left: 0.4rem;
            padding-right: 0.4rem;
        }

        h1 { font-size: 1.1rem !important; }

        .stTabs [data-baseweb="tab"] {
            padding: 0.4rem 0.6rem;
            font-size: 0.75rem;
        }

        [data-testid="stMetric"] {
            padding: 0.7rem 0.8rem;
        }

        [data-testid="stMetric"] > label {
            font-size: 0.72rem;
        }

        [data-testid="stMetric"] > div {
            font-size: 1rem;
        }
    }

    /* ===== 自定义卡片移动端适配类 ===== */
    .mobile-hero-card {
        padding: 1.2rem 1rem;
    }

    .mobile-fund-card {
        padding: 1rem;
    }

    .mobile-fund-card-footer {
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    .mobile-fund-card-footer > div {
        flex: 0 0 calc(33.33% - 0.3rem);
        text-align: center;
        padding: 0.4rem 0;
    }

    @media (max-width: 768px) {
        .mobile-hero-card {
            padding: 1.2rem 0.8rem !important;
        }

        .mobile-hero-card .hero-value {
            font-size: 1.8rem !important;
        }

        .mobile-fund-card-footer {
            display: grid !important;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.3rem;
        }

        .mobile-fund-card-footer > div:nth-child(4),
        .mobile-fund-card-footer > div:nth-child(5) {
            grid-column: span 1;
        }
    }
    </style>
    """

    st.markdown(custom_css, unsafe_allow_html=True)


# ============================================================
# 自定义 HTML 组件 - 养基宝风格（含移动端适配）
# ============================================================

def render_hero_card(total_value, total_cost, total_profit, total_profit_rate,
                     yesterday_profit, yesterday_rate, today_profit, today_rate):
    """渲染顶部资产总览 Hero 卡片（渐变蓝色背景，移动端适配）"""

    # 格式化数值
    value_str = f"{total_value:,.2f}" if total_value > 0 else "--"
    profit_str = f"{total_profit:+,.2f}" if total_value > 0 else "--"
    rate_str = f"{total_profit_rate:+.2f}%" if total_value > 0 else "--"
    yesterday_str = f"{yesterday_profit:+,.2f}" if yesterday_profit != 0 else "--"
    yesterday_rate_str = f"{yesterday_rate:+.2f}%" if yesterday_profit != 0 else ""
    today_str = f"{today_profit:+,.2f}" if today_profit != 0 else "--"
    today_rate_str = f"{today_rate:+.2f}%" if today_profit != 0 else ""

    html = (
        f'<div class="mobile-hero-card" style="background:linear-gradient(135deg,#4A90D9 0%,#6CB2EB 100%); border-radius:16px; padding:1.8rem 2rem; margin-bottom:1.5rem; color:white; box-shadow:0 4px 16px rgba(74,144,217,0.25);">'
        f'<div style="font-size:0.85rem; opacity:0.85; margin-bottom:4px;">总资产（元）</div>'
        f'<div class="hero-value" style="font-size:2.4rem; font-weight:700; letter-spacing:-1px; margin-bottom:0.5rem;">{value_str}</div>'
        f'<div style="display:flex; flex-wrap:wrap; gap:0.8rem 1.5rem; align-items:center; margin-bottom:1rem;">'
        f'<div><span style="font-size:0.8rem; opacity:0.8;">累计收益</span>'
        f'<span style="font-size:1rem; font-weight:600; margin-left:6px;">{profit_str}</span>'
        f'<span style="font-size:0.85rem; opacity:0.9; margin-left:4px;">{rate_str}</span></div>'
        f'<div><span style="font-size:0.8rem; opacity:0.8;">总成本</span>'
        f'<span style="font-size:1rem; font-weight:600; margin-left:6px;">{total_cost:,.2f}</span></div>'
        f'</div>'
        f'<div style="display:flex; gap:0; background:rgba(255,255,255,0.15); border-radius:10px; padding:0; overflow:hidden;">'
        f'<div style="flex:1; padding:0.7rem 1rem; border-right:1px solid rgba(255,255,255,0.15);">'
        f'<div style="font-size:0.75rem; opacity:0.8;">昨日收益</div>'
        f'<div style="font-size:1.1rem; font-weight:600; margin-top:2px;">{yesterday_str}'
        f'<span style="font-size:0.8rem; opacity:0.9; margin-left:4px;">{yesterday_rate_str}</span></div>'
        f'</div>'
        f'<div style="flex:1; padding:0.7rem 1rem;">'
        f'<div style="font-size:0.75rem; opacity:0.8;">今日收益（估）</div>'
        f'<div style="font-size:1.1rem; font-weight:600; margin-top:2px;">{today_str}'
        f'<span style="font-size:0.8rem; opacity:0.9; margin-left:4px;">{today_rate_str}</span></div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_fund_card(fund_name, fund_code, market_value, total_cost,
                     profit, profit_rate, shares, avg_cost, current_nav,
                     nav_date, yesterday_return, today_growth):
    """渲染单只基金持仓卡片（移动端适配）"""

    # 收益颜色（红涨绿跌）
    if isinstance(profit, (int, float, Decimal)) and profit != 0:
        profit_color = "#E74C3C" if profit > 0 else "#27AE60"
        profit_str = f"{float(profit):+,.2f}"
        rate_str = f"{float(profit_rate):+.2f}%"
    else:
        profit_color = "#7B8B9E"
        profit_str = "--"
        rate_str = "--"

    # 市值
    if isinstance(market_value, (int, float, Decimal)) and market_value > 0:
        mv_str = f"{float(market_value):,.2f}"
    else:
        mv_str = "--"

    # 昨日涨跌
    if isinstance(yesterday_return, (int, float)) and yesterday_return != 0:
        yd_color = "#E74C3C" if yesterday_return > 0 else "#27AE60"
        yd_str = f"{yesterday_return:+.2f}%"
    else:
        yd_color = "#7B8B9E"
        yd_str = "--"

    # 今日估值
    if today_growth is not None and today_growth != "-":
        td_val = float(today_growth)
        td_color = "#E74C3C" if td_val > 0 else "#27AE60" if td_val < 0 else "#7B8B9E"
        td_str = f"{td_val:+.2f}%"
    else:
        td_color = "#7B8B9E"
        td_str = "--"

    # 净值显示
    if isinstance(current_nav, (int, float, Decimal)):
        nav_str = f"{float(current_nav):.4f}"
    else:
        nav_str = "--"

    nav_date_str = str(nav_date) if nav_date and nav_date != "-" else ""

    html = (
        f'<div class="mobile-fund-card" style="background:#FFFFFF; border-radius:14px; padding:1.2rem 1.4rem; margin-bottom:0.8rem; border:1px solid #E8EDF2; box-shadow:0 1px 4px rgba(0,0,0,0.03);">'
        f'<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.8rem;">'
        f'<div style="flex:1; min-width:0;">'
        f'<div style="font-size:1rem; font-weight:600; color:#2C3E50; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{fund_name}</div>'
        f'<div style="font-size:0.8rem; color:#A0AEC0; margin-top:2px;">{fund_code}</div>'
        f'</div>'
        f'<div style="text-align:right; margin-left:0.8rem; flex-shrink:0;">'
        f'<div style="font-size:1.1rem; font-weight:700; color:#2C3E50;">{mv_str}</div>'
        f'<div style="font-size:0.82rem; color:{profit_color}; font-weight:600; margin-top:2px;">{profit_str} {rate_str}</div>'
        f'</div>'
        f'</div>'
        f'<div class="mobile-fund-card-footer" style="display:flex; justify-content:space-between; padding-top:0.7rem; border-top:1px solid #F0F4F8; font-size:0.78rem; color:#7B8B9E;">'
        f'<div style="text-align:center; flex:1;"><div>净值</div><div style="color:#2C3E50; font-weight:600; margin-top:2px;">{nav_str}</div></div>'
        f'<div style="text-align:center; flex:1;"><div>份额</div><div style="color:#2C3E50; font-weight:600; margin-top:2px;">{float(shares):,.2f}</div></div>'
        f'<div style="text-align:center; flex:1;"><div>成本</div><div style="color:#2C3E50; font-weight:600; margin-top:2px;">{float(avg_cost):.4f}</div></div>'
        f'<div style="text-align:center; flex:1;"><div>昨日</div><div style="color:{yd_color}; font-weight:600; margin-top:2px;">{yd_str}</div></div>'
        f'<div style="text-align:center; flex:1;"><div>今日估</div><div style="color:{td_color}; font-weight:600; margin-top:2px;">{td_str}</div></div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_section_header(title, subtitle=None):
    """渲染统一的区块标题"""
    sub_html = f'<div style="font-size:0.82rem; color:#A0AEC0; margin-top:2px;">{subtitle}</div>' if subtitle else ""
    html = f'<div style="margin:1.2rem 0 0.8rem 0;"><div style="font-size:1.1rem; font-weight:600; color:#2C3E50;">{title}</div>{sub_html}</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_empty_state(message, hint=None):
    """渲染空状态提示"""
    hint_html = f'<div style="font-size:0.82rem; color:#A0AEC0; margin-top:6px;">{hint}</div>' if hint else ""
    html = (
        f'<div style="text-align:center; padding:3rem 2rem; color:#7B8B9E; background:#FFFFFF; border-radius:14px; border:1px solid #E8EDF2;">'
        f'<div style="font-size:2.5rem; margin-bottom:0.8rem;">&#128203;</div>'
        f'<div style="font-size:1rem; font-weight:500;">{message}</div>'
        f'{hint_html}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_stat_card(label, value, sub_value=None, color=None):
    """渲染统计小卡片（白色背景）"""
    color_style = f"color:{color};" if color else "color:#2C3E50;"
    sub_html = f'<div style="font-size:0.78rem; color:#A0AEC0; margin-top:2px;">{sub_value}</div>' if sub_value else ""
    html = (
        f'<div style="background:#FFFFFF; border-radius:12px; padding:1rem 1.2rem; border:1px solid #E8EDF2; box-shadow:0 1px 3px rgba(0,0,0,0.03);">'
        f'<div style="font-size:0.78rem; color:#7B8B9E; font-weight:500;">{label}</div>'
        f'<div style="font-size:1.3rem; font-weight:700; {color_style} margin-top:4px;">{value}</div>'
        f'{sub_html}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_risk_badge(level_text, score=None):
    """渲染风险等级徽章"""
    color_map = {
        "低风险": ("#27AE60", "#EAFAF1"),
        "中低风险": ("#85C440", "#F4FAE8"),
        "中等风险": ("#F39C12", "#FEF9E7"),
        "中高风险": ("#E67E22", "#FDF2E9"),
        "高风险": ("#E74C3C", "#FDEDEC"),
    }
    color, bg = color_map.get(level_text, ("#7B8B9E", "#F5F7FA"))
    score_html = f'<span style="margin-left:6px; font-size:0.78rem;">({score}/100)</span>' if score else ""
    html = f'<span style="display:inline-block; background:{bg}; color:{color}; padding:4px 12px; border-radius:20px; font-size:0.82rem; font-weight:600;">{level_text}{score_html}</span>'
    return html


def render_holding_card(fund_name, fund_code, total_shares, avg_cost,
                        total_cost, first_buy_date, current_nav=None,
                        nav_date=None, market_value=None, profit=None,
                        profit_rate=None):
    """渲染持仓管理的基金卡片（移动端适配）"""

    # 收益信息
    if profit is not None:
        profit_color = "#E74C3C" if profit > 0 else "#27AE60" if profit < 0 else "#7B8B9E"
        profit_html = (
            f'<div style="display:flex; flex-wrap:wrap; gap:0.8rem 1.5rem; padding-top:0.8rem; border-top:1px solid #F0F4F8; margin-top:0.8rem;">'
            f'<div><div style="font-size:0.75rem; color:#A0AEC0;">最新净值</div>'
            f'<div style="font-size:0.95rem; font-weight:600; color:#2C3E50; margin-top:2px;">{current_nav:.4f}'
            f'<span style="font-size:0.72rem; color:#A0AEC0; margin-left:4px;">{nav_date}</span></div></div>'
            f'<div><div style="font-size:0.75rem; color:#A0AEC0;">当前市值</div>'
            f'<div style="font-size:0.95rem; font-weight:600; color:#2C3E50; margin-top:2px;">{market_value:,.2f}</div></div>'
            f'<div><div style="font-size:0.75rem; color:#A0AEC0;">持仓盈亏</div>'
            f'<div style="font-size:0.95rem; font-weight:600; color:{profit_color}; margin-top:2px;">{profit:+,.2f}'
            f'<span style="font-size:0.78rem;">({profit_rate:+.2f}%)</span></div></div>'
            f'</div>'
        )
    else:
        profit_html = '<div style="padding-top:0.8rem; border-top:1px solid #F0F4F8; margin-top:0.8rem; font-size:0.82rem; color:#A0AEC0;">暂无净值数据，请到净值查询更新</div>'

    html = (
        f'<div style="background:#FFFFFF; border-radius:14px; padding:1.2rem 1.4rem; margin-bottom:0.8rem; border:1px solid #E8EDF2; box-shadow:0 1px 4px rgba(0,0,0,0.03);">'
        f'<div style="display:flex; justify-content:space-between; align-items:flex-start;">'
        f'<div style="flex:1; min-width:0;"><div style="font-size:1.05rem; font-weight:600; color:#2C3E50; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{fund_name}</div>'
        f'<div style="font-size:0.78rem; color:#A0AEC0; margin-top:2px;">{fund_code}</div></div>'
        f'<div style="text-align:right; margin-left:0.8rem; flex-shrink:0;"><div style="font-size:0.75rem; color:#A0AEC0;">总投入</div>'
        f'<div style="font-size:1.1rem; font-weight:700; color:#2C3E50;">{float(total_cost):,.2f}</div></div>'
        f'</div>'
        f'<div style="display:flex; flex-wrap:wrap; gap:0.5rem 1.5rem; margin-top:0.8rem; font-size:0.82rem; color:#7B8B9E;">'
        f'<div>份额 <span style="color:#2C3E50; font-weight:600;">{float(total_shares):,.2f}</span></div>'
        f'<div>成本价 <span style="color:#2C3E50; font-weight:600;">{float(avg_cost):.4f}</span></div>'
        f'<div>首次买入 <span style="color:#2C3E50; font-weight:600;">{first_buy_date}</span></div>'
        f'</div>'
        f'{profit_html}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_page_header(title, subtitle=None):
    """渲染页面顶部标题"""
    sub_html = f'<div style="font-size:0.85rem; color:#7B8B9E; margin-top:4px;">{subtitle}</div>' if subtitle else ""
    html = f'<div style="margin-bottom:1.5rem;"><div style="font-size:1.5rem; font-weight:700; color:#2C3E50;">{title}</div>{sub_html}</div>'
    st.markdown(html, unsafe_allow_html=True)
