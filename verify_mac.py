import hashlib
import hmac
import urllib.parse
from typing import Dict, Any

def ecpay_url_encode(source: str) -> str:
    """對應 ECPay 官方 UrlService::ecpayUrlEncode() 邏輯"""
    # 1. urllib.parse.quote_plus 將空格編碼為 +
    encoded = urllib.parse.quote_plus(source)
    # 2. Python quote_plus 不編碼 ~，但 PHP urlencode 會編碼為 %7E
    encoded = encoded.replace('~', '%7E')
    # 3. 全部轉小寫
    encoded = encoded.lower()
    # 4. .NET 特殊字元還原
    replacements = {
        '%2d': '-', '%5f': '_', '%2e': '.', '%21': '!',
        '%2a': '*', '%28': '(', '%29': ')',
    }
    for old, new in replacements.items():
        encoded = encoded.replace(old, new)
    return encoded

def generate_check_mac_value(params: Dict[str, Any], hash_key: str, hash_iv: str, method: str = 'sha256') -> str:
    """產生 ECPay CheckMacValue"""
    # 1. 移除既有 CheckMacValue
    filtered = {k: str(v) for k, v in params.items() if k != 'CheckMacValue'}
    # 2. Key 不區分大小寫排序 (str.lower)
    sorted_params = sorted(filtered.items(), key=lambda x: x[0].lower())
    # 3. 組合字串
    param_str = '&'.join(f'{k}={v}' for k, v in sorted_params)
    raw = f'HashKey={hash_key}&{param_str}&HashIV={hash_iv}'
    # 4. ECPay URL encode
    encoded = ecpay_url_encode(raw)
    # 5. Hash
    if method.lower() == 'md5':
        hashed = hashlib.md5(encoded.encode('utf-8')).hexdigest()
    else:
        hashed = hashlib.sha256(encoded.encode('utf-8')).hexdigest()
    # 6. 轉大寫
    return hashed.upper()

def verify_check_mac_value(params: Dict[str, Any], hash_key: str, hash_iv: str, method: str = 'sha256') -> bool:
    """驗證 CheckMacValue (Timing-safe)"""
    received = params.get('CheckMacValue', '')
    calculated = generate_check_mac_value(params, hash_key, hash_iv, method)
    return hmac.compare_digest(received, calculated)

if __name__ == "__main__":
    # 使用 AIO 測試帳號驗證
    test_params = {
        "MerchantID": "3002607",
        "MerchantTradeNo": "TOPUP123",
        "MerchantTradeDate": "2026/05/06 12:34:56",
        "PaymentType": "aio",
        "TotalAmount": 100,
        "TradeDesc": "AHA 點數充值",
        "ItemName": "100 點",
        "ReturnURL": "http://127.0.0.1:8000/ecpay/return",
        "ClientBackURL": "http://localhost/profile",
        "ChoosePayment": "ALL",
        "EncryptType": 1,
    }
    
    # AIO 測試密鑰
    hash_key = "pwFHCqoQZGmho4w6"
    hash_iv = "EkRm7iFT261dpevs"
    
    calculated_mac = generate_check_mac_value(test_params, hash_key, hash_iv)
    print(f"Calculated MAC: {calculated_mac}")
    
    # 將產生的 MAC 放回 params 測試驗證功能
    test_params["CheckMacValue"] = calculated_mac
    is_valid = verify_check_mac_value(test_params, hash_key, hash_iv)
    print(f"Verify Result: {is_valid}")
