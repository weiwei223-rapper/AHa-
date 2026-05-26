import hashlib

from routers.payments import ECPAY_MERCHANT_ID, generate_ecpay_check_mac_value


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
    # Expected value for MerchantID 3002607 with standard test keys
    expected = "D1CAEB2BB4FA9809527E40592FE082BAB3CB779E3B9E12D05FD9262BDDB7CFE6"
    assert result == expected


def test_generate_ecpay_check_mac_value_includes_empty_values():
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
        "Remark": "",  # Included in AHa-old logic
        "CustomField1": None,  # Included as 'None' in AHa-old logic
    }

    result = generate_ecpay_check_mac_value(params)

    # Expected value for MerchantID 3002607 including empty fields
    expected = "C0E2A7996214EB1B44635C1A8D3A2D9855BA53494B623CE1B924C3A187A58611"
    assert result == expected
