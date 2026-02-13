"""验证服务层导入"""
import sys
sys.path.insert(0, "C:/Users/yf_yht/Desktop/jj")

from app.services import fund_service, holding_service
from app.data.database import get_db_context

print("模块导入成功")

# 测试查询
with get_db_context() as db:
    funds = fund_service.get_all_funds(db)
    holdings = holding_service.get_all_holdings(db)
    print(f"基金数量: {len(funds)}")
    print(f"持仓数量: {len(holdings)}")

print("验证完成")
