"""测试基金数据抓取"""
import sys
sys.path.insert(0, "C:/Users/yf_yht/Desktop/jj")

from app.services.fund_data_fetcher import fetch_fund_info, fetch_nav_history

# 测试获取基金信息
print("测试获取基金信息...")
info = fetch_fund_info("000001")
if info:
    print(f"  代码: {info.code}")
    print(f"  名称: {info.name}")
    print(f"  净值: {info.nav}")
    print(f"  日期: {info.nav_date}")
else:
    print("  获取失败")

print()

# 测试获取历史净值
print("测试获取历史净值...")
navs = fetch_nav_history("000001", limit=5)
print(f"  获取到 {len(navs)} 条记录")
for nav in navs[:3]:
    print(f"    {nav.nav_date}: {nav.nav}")

print()
print("测试完成")
