import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "API_key.env")
load_dotenv(env_path)
load_dotenv()

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("EMAIL_USER", "aha.ai.service@gmail.com")
SENDER_PASSWORD = os.getenv("EMAIL_PASSWORD") # This should be a Gmail App Password

def send_refund_email(user_email: str, user_name: str, item_title: str, is_valid: bool, refund_points: int = 0, reason: str = ""):
    """
    Sends an email to the user regarding their error report status.
    """
    if not SENDER_PASSWORD:
        print("DEBUG: EMAIL_PASSWORD not set, skipping email notification.")
        return False

    subject = f"【AHa AI 學習助理】錯誤回報處理結果通知 - {item_title}"
    
    if is_valid:
        body = f"""
        Dear {user_name},

        感謝您對『{item_title}』提出的錯誤回報。

        經 AI 系統初步審核，您的回報屬實且符合退款標準。
        判定理由：{reason}

        我們已將原始消耗點數的 1.5 倍（共 {refund_points} 點）歸還至您的帳戶。

        您可以登入 AHa 系統查看最新的點數餘額。
        再次感謝您協助我們提升服務品質！

        AHa AI 團隊 敬上
        """
    else:
        body = f"""
        Dear {user_name},

        感謝您對『{item_title}』提出的錯誤回報。

        經系統審核，您的回報內容暫時不符合退款標準。
        判定理由：{reason}
        
        如果您對判定結果有異議，或有更詳細的補充說明，歡迎隨時聯繫我們。

        AHa AI 團隊 敬上
        """

    msg = MIMEMultipart()
    msg['From'] = f"AHa AI Service <{SENDER_EMAIL}>"
    msg['To'] = user_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"DEBUG: Email sent to {user_email}")
        return True
    except Exception as e:
        print(f"DEBUG: Failed to send email: {e}")
        return False
