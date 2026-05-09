import sys
import os
import argparse
from datetime import datetime
from sqlalchemy.orm import Session

# Add current directory to path so we can import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import database
    import models
    from main import calculate_points_from_amount, get_plan_description
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def manual_recharge(user_id: int, amount: int = None, points: int = None, reason: str = None):
    """
    手動為使用者充值點數
    """
    db = next(database.get_db())
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            print(f"❌ 找不到使用者 ID: {user_id}")
            return

        points_to_add = 0
        final_amount = amount or 0
        
        if points is not None:
            points_to_add = points
            plan_content = reason or f"手動補充 {points} 點數"
        elif amount is not None:
            points_to_add = calculate_points_from_amount(amount)
            plan_content = reason or get_plan_description(amount)
        else:
            print("❌ 必須提供 amount 或 points")
            return
            
        print(f"正在為使用者 {user.name} (ID: {user.id}) 充值...")
        if amount is not None:
            print(f"付款金額: NT$ {amount}")
        print(f"增加點數: {points_to_add} 點")
        print(f"紀錄描述: {plan_content}")
        
        # 更新使用者點數
        old_points = user.points
        user.points += points_to_add
        
        # 建立充值紀錄
        order_id = f"MANUAL{datetime.utcnow():%Y%m%d%H%M%S}"
        record = models.RechargeRecord(
            user_id=user.id,
            date=datetime.utcnow().strftime("%Y/%m/%d"),
            order_id=order_id,
            amount=final_amount,
            points=points_to_add,
            balance_after=user.points,
            plan_content=plan_content,
            payment_method="Manual",
        )
        
        db.add(record)
        db.add(user)
        db.commit()
        
        print(f"✅ 充值成功！")
        print(f"原始點數: {old_points}")
        print(f"目前點數: {user.points}")
        print(f"訂單編號: {order_id}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 充值失敗: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="手動為 AHa 使用者充值點數")
    parser.add_argument("user_id", type=int, help="使用者 ID")
    parser.add_argument("--amount", type=int, help="付款金額 (會根據預設方案計算點數)")
    parser.add_argument("--points", type=int, help="直接增加的點數")
    parser.add_argument("--reason", type=str, help="儲值理由/描述")
    
    args = parser.parse_args()
    
    if args.amount is None and args.points is None:
        print("用法提示: 必須提供 --amount 或 --points 其中之一")
        parser.print_help()
        sys.exit(1)
        
    manual_recharge(args.user_id, amount=args.amount, points=args.points, reason=args.reason)
