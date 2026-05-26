import json
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session
import models
import database
import schema
from auth_schemas import LoginResponse
from urllib.parse import quote_plus

router = APIRouter(tags=["payments"])

# --- ECPay Config ---
import os
ECPAY_MERCHANT_ID = os.getenv("ECPAY_MERCHANT_ID", "3002607")
ECPAY_HASH_KEY = os.getenv("ECPAY_HASH_KEY", "pwFHCqoQZGmho4w6")
ECPAY_HASH_IV = os.getenv("ECPAY_HASH_IV", "EkRm7iFT261dpevs")

def ecpay_url_encode(source: str) -> str:
    encoded = quote_plus(source)
    encoded = encoded.replace('~', '%7E')
    encoded = encoded.lower()
    replacements = {
        '%2d': '-', '%5f': '_', '%2e': '.', '%21': '!',
        '%2a': '*', '%28': '(', '%29': ')',
    }
    for old, new in replacements.items():
        encoded = encoded.replace(old, new)
    return encoded

def generate_ecpay_check_mac_value(params: Dict[str, Any]) -> str:
    filtered_params = {k: str(v) for k, v in params.items() if k.lower() != "checkmacvalue"}
    if "MerchantID" not in filtered_params: 
        filtered_params["MerchantID"] = ECPAY_MERCHANT_ID
    sorted_keys = sorted(filtered_params.keys())
    raw_list = [f"{k}={filtered_params[k]}" for k in sorted_keys]
    raw_str = f"HashKey={ECPAY_HASH_KEY}&{'&'.join(raw_list)}&HashIV={ECPAY_HASH_IV}"
    encoded_str = ecpay_url_encode(raw_str)
    import hashlib
    encrypt_type = params.get("EncryptType", 1)
    if str(encrypt_type) == "0":
        mac = hashlib.md5(encoded_str.encode("utf-8")).hexdigest().upper()
    else:
        mac = hashlib.sha256(encoded_str.encode("utf-8")).hexdigest().upper()
    return mac

class EcpayCheckoutResponse(schema.BaseModel):
    CheckMacValue: str
    MerchantTradeNo: str
    MerchantTradeDate: str
    params: Dict[str, str]

@router.post("/api/ecpay/checkout", response_model=EcpayCheckoutResponse)
def ecpay_checkout(payload: Dict[str, Any], db: Session = Depends(database.get_db)):
    import time
    merchant_trade_no = f"AHA{int(time.time())}"
    merchant_trade_date = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    frontend_base_url = payload.get("ClientBackURL", "").replace("/profile", "")
    if not frontend_base_url: frontend_base_url = "http://localhost:5173"

    ecpay_params = {
        "MerchantID": ECPAY_MERCHANT_ID,
        "MerchantTradeNo": merchant_trade_no,
        "MerchantTradeDate": merchant_trade_date,
        "PaymentType": "aio",
        "TotalAmount": str(payload.get("TotalAmount")),
        "TradeDesc": "AHa_AI_Points_Topup",
        "ItemName": "AHa_AI_Points",
        "ReturnURL": payload.get("ReturnURL"),
        "OrderResultURL": payload.get("ReturnURL").replace("/ecpay/return", "/ecpay/return-client"),
        "ChoosePayment": "ALL",
        "EncryptType": "1",
        "CustomField1": str(payload.get("user_id")),
        "CustomField2": str(payload.get("plan_id") or ""),
        "CustomField3": frontend_base_url,
    }
    ecpay_params = {k: v for k, v in ecpay_params.items() if v is not None}
    mac = generate_ecpay_check_mac_value(ecpay_params)
    ecpay_params["CheckMacValue"] = mac
    return EcpayCheckoutResponse(
        CheckMacValue=mac,
        MerchantTradeNo=merchant_trade_no,
        MerchantTradeDate=merchant_trade_date,
        params=ecpay_params
    )

@router.post("/ecpay/return")
async def ecpay_return(request: Request, db: Session = Depends(database.get_db)):
    return await process_ecpay_payment(request, db)

@router.post("/ecpay/return-client")
async def ecpay_return_client(request: Request, db: Session = Depends(database.get_db)):
    form_data = await request.form()
    params = dict(form_data)
    frontend_url = params.get("CustomField3", "http://localhost:5173")
    await process_ecpay_payment(request, db)
    return HTMLResponse(content=f"""
        <html>
            <head><title>付款成功</title></head>
            <body style="background:#080c16;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
                <div style="text-align:center;">
                    <h1 style="color:#2bc1f1;">付款完成！</h1>
                    <p>正在將您導回系統，請稍候...</p>
                    <script>
                        setTimeout(() => {{ window.location.href = '{frontend_url}/profile'; }}, 1500);
                    </script>
                </div>
            </body>
        </html>
    """)

async def process_ecpay_payment(request: Request, db: Session):
    import hmac
    form_data = await request.form()
    params = dict(form_data)
    received_mac = params.get("CheckMacValue", "")
    calculated_mac = generate_ecpay_check_mac_value(params)
    if not hmac.compare_digest(received_mac, calculated_mac):
        return PlainTextResponse("0|CheckMacValueVerifyFail")
    rtn_code = str(params.get("RtnCode", ""))
    if rtn_code == "1":
        try:
            user_id_str = params.get("CustomField1")
            amount_str = params.get("TradeAmt", "0")
            merchant_trade_no = params.get("MerchantTradeNo")
            if not user_id_str or not merchant_trade_no:
                return PlainTextResponse("0|MissingFields")
            user_id = int(user_id_str)
            amount = int(amount_str)
            existing = db.query(models.RechargeRecord).filter(models.RechargeRecord.order_id == merchant_trade_no).first()
            if existing: return PlainTextResponse("1|OK")
            if amount >= 999: points_to_add = 1100
            elif amount >= 599: points_to_add = 650
            elif amount >= 299: points_to_add = 300
            else: points_to_add = amount
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user:
                user.points = (user.points or 0) + points_to_add
                record = models.RechargeRecord(
                    user_id=user.id,
                    date=datetime.now().strftime("%Y/%m/%d"),
                    order_id=merchant_trade_no,
                    amount=amount,
                    points=points_to_add,
                    balance_after=user.points,
                    plan_content=f"ECPay: {params.get('ItemName', 'Points')}",
                    payment_method="ECPay",
                    plan_id=params.get("CustomField2")
                )
                db.add(record)
                db.commit()
                return PlainTextResponse("1|OK")
        except Exception:
            db.rollback()
    return PlainTextResponse("0|Fail")
