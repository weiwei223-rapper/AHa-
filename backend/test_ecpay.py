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
    assert result == "24C3B815B1F26AD004EDF1E1A99DD4F95AACE0C2A0D222E44DB0061CF6E77A7A"


def test_generate_ecpay_check_mac_value_excludes_empty_values():
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
        "Remark": "",  # Should be ignored
        "CustomField1": None,  # Should be ignored
    }

    result = generate_ecpay_check_mac_value(params)

    # Expected value should be same as the one without Remark and CustomField1
    expected = "24C3B815B1F26AD004EDF1E1A99DD4F95AACE0C2A0D222E44DB0061CF6E77A7A"
    assert result == expected
