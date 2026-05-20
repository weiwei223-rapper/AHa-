import hashlib
from urllib.parse import quote_plus
hash_key='5294y06JbISpM5x9'
hash_iv='v77hoKGq4kWxNNIS'
params = {'CustomField1': '7', 'CustomField2': 'NT$ 599', 'CustomField3': '', 'CustomField4': '', 'MerchantID': '2000132', 'MerchantTradeNo': 'AHA1779203524', 'PaymentDate': '2026/05/19 23:12:20', 'PaymentType': 'Credit_CreditCard', 'PaymentTypeChargeFee': '13', 'RtnCode': '1', 'RtnMsg': 'paid', 'SimulatePaid': '0', 'StoreID': '', 'TradeAmt': '599', 'TradeDate': '2026/05/19 23:12:03', 'TradeNo': '2605192312038748'}
sorted_keys = sorted(params.keys())
raw_list = [f"{k}={params[k]}" for k in sorted_keys]
raw_str = f"HashKey={hash_key}&{'&'.join(raw_list)}&HashIV={hash_iv}"
encoded_str = quote_plus(raw_str).lower().replace('%7e', '~')
mac = hashlib.sha256(encoded_str.encode('utf-8')).hexdigest().upper()
print('MAC with empty:', mac)

params_no_empty = {k: v for k, v in params.items() if v}
sorted_keys_no_empty = sorted(params_no_empty.keys())
raw_list_no_empty = [f"{k}={params_no_empty[k]}" for k in sorted_keys_no_empty]
raw_str_no_empty = f"HashKey={hash_key}&{'&'.join(raw_list_no_empty)}&HashIV={hash_iv}"
encoded_str_no_empty = quote_plus(raw_str_no_empty).lower().replace('%7e', '~')
mac_no_empty = hashlib.sha256(encoded_str_no_empty.encode('utf-8')).hexdigest().upper()
print('MAC without empty:', mac_no_empty)
