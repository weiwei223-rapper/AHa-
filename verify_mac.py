import hashlib
from urllib.parse import quote_plus

def calculate_check_mac_value(params, hash_key, hash_iv):
    # 1. Sort by ASCII
    sorted_params = sorted(params.items())
    
    # 2. HashKey=...&SortedParams&HashIV=...
    param_str = "&".join([f"{k}={v}" for k, v in sorted_params])
    raw_str = f"HashKey={hash_key}&{param_str}&HashIV={hash_iv}"
    print(f"Raw string: {raw_str}")
    
    # 3. URL Encode (RFC 1866 / quote_plus, lowercase)
    encoded_str = quote_plus(raw_str).lower()
    
    # 4. ECPay URL Encode replacements:
    # - `-` -> `-` (not encoded)
    # - `_` -> `_` (not encoded)
    # - `.` -> `.` (not encoded)
    # - `~` -> `~` (not encoded)
    # Space -> `+` (already done by quote_plus)
    # Other characters MUST be encoded (e.g. `!`, `*`, `(`, `)` should be encoded).
    
    # Python's quote_plus(raw_str, safe='') will encode most things.
    # We need to ensure -, _, ., ~ are NOT encoded (or replaced back if encoded).
    # quote_plus by default does NOT encode - . _
    # Let's check what quote_plus does.
    
    # If the user says "Other characters MUST be encoded", and gives !, *, (, ) as examples,
    # it means they SHOULD be in %XX form in the final string.
    
    # Let's perform the replacements as specified.
    # The rule says: "-", "_", ".", "~" -> not encoded.
    # "Space" -> "+"
    # "Other characters MUST be encoded"
    
    # We can achieve this by using quote_plus with safe='*()!-_.~' and then replacing those we WANT encoded.
    # OR just use quote_plus and replace back ONLY what is allowed.
    
    # Default quote_plus behavior:
    # safe default is '' (empty) in quote_plus? No, in quote it's '/'. In quote_plus it's ''.
    # Let's verify.
    
    # Actually, let's just do it manually to be safe.
    def ecpay_quote(s):
        # RFC 1866 is similar to quote_plus but we need to be careful.
        res = quote_plus(s).lower()
        # Replacements:
        # quote_plus already leaves - . _ unencoded.
        # It encodes ~ to %7e. ECPay says ~ should be ~ (not encoded).
        res = res.replace("%7e", "~")
        # The user says ! * ( ) MUST be encoded. 
        # quote_plus encodes them by default? 
        # ! -> %21, * -> %2a, ( -> %28, ) -> %29.
        # Let's verify this in the script.
        return res

    encoded_str = ecpay_quote(raw_str)
    print(f"Encoded string: {encoded_str}")
    
    # 5. SHA256 and Uppercase
    mac = hashlib.sha256(encoded_str.encode("utf-8")).hexdigest().upper()
    return mac

params = {
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
    "EncryptType": 1,
}
hash_key = "5294y06JbISpM5x9"
hash_iv = "v77hoKGq4kWxNNIS"

result = calculate_check_mac_value(params, hash_key, hash_iv)
expected = "24C3B815B1F26AD004EDF1E1A99DD4F95AACE0C2A0D222E44DB0061CF6E77A7A"


print(f"Calculated: {result}")
print(f"Expected:   {expected}")
print(f"Match:      {result == expected}")
