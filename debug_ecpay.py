import hashlib
import urllib.parse
from typing import Dict, Any

def generate_mac(params: Dict[str, Any], hash_key: str, hash_iv: str, sort_func, quote_func, hash_func_name, keep_connectors):
    filtered_params = {k: str(v) for k, v in params.items() if k != "CheckMacValue"}
    sorted_keys = sorted(filtered_params.keys(), key=sort_func)
    raw_list = [f"{k}={filtered_params[k]}" for k in sorted_keys]
    raw_str = f"HashKey={hash_key}&{'&'.join(raw_list)}&HashIV={hash_iv}"
    
    encoded_str = quote_func(raw_str).lower()
    
    if keep_connectors:
        # Some implementations might keep & and =
        # But wait, if we quote the whole string, they are encoded.
        # Let's try to encode ONLY the values, or replace them back.
        encoded_str = encoded_str.replace("%3d", "=").replace("%26", "&")

    encoded_str = (
        encoded_str.replace("%2d", "-")
        .replace("%5f", "_")
        .replace("%2e", ".")
        .replace("%21", "!")
        .replace("%2a", "*")
        .replace("%28", "(")
        .replace("%29", ")")
    )
    
    if hash_func_name == "sha256":
        return hashlib.sha256(encoded_str.encode("utf-8")).hexdigest().upper()
    elif hash_func_name == "md5":
        return hashlib.md5(encoded_str.encode("utf-8")).hexdigest().upper()
    return None

test_params_base = {
    "MerchantID": "2000132",
    "MerchantTradeNo": "TOPUP123",
    "MerchantTradeDate": "2026/05/06 12:34:56",
    "PaymentType": "aio",
    "TotalAmount": 100,
    "TradeDesc": "AHA 點數充值",
    "ItemName": "100 點",
    "ReturnURL": "http://127.0.0.1:8000/ecpay/return",
    "ClientBackURL": "http://localhost/profile",
    "ChoosePayment": "ALL",
}

hash_keys = ["5294y06JbISpM5x9"]
hash_ivs = ["v77hoKGq4uF4s1uL", "v77hoKGq4kWxNNUE"]
expected = "F6682943D647930773041C78AF1D36F4"

for iv in hash_ivs:
    for et in [1, 0, None]:
        params = test_params_base.copy()
        if et is not None:
            params["EncryptType"] = et
        for s_name, s_func in [("ASCII", None), ("Lower", str.lower)]:
            for q_name, q_func in [("quote_plus", urllib.parse.quote_plus), ("quote", urllib.parse.quote)]:
                for h_name in ["md5", "sha256"]:
                    for keep in [True, False]:
                        res = generate_mac(params, hash_keys[0], iv, s_func, q_func, h_name, keep)
                        if res == expected:
                            print(f"MATCH FOUND!")
                            print(f"IV: {iv}, ET: {et}, Sort: {s_name}, Quote: {q_name}, Hash: {h_name}, KeepConnectors: {keep}")
                            exit(0)
print("No match.")
