import hashlib

from main import ECPAY_MERCHANT_ID, generate_ecpay_check_mac_value


def test_generate_ecpay_check_mac_value_excludes_checkmacvalue():
    params = {
        "MerchantID": ECPAY_MERCHANT_ID,
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
        "CheckMacValue": "SHOULD_BE_IGNORED",
    }

    result = generate_ecpay_check_mac_value(params)

    assert isinstance(result, str)
    assert result == "F6682943D647930773041C78AF1D36F4"


def test_generate_ecpay_check_mac_value_includes_merchantid_when_missing():
    params = {
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

    result = generate_ecpay_check_mac_value(params)

    assert result == "F6682943D647930773041C78AF1D36F4"
