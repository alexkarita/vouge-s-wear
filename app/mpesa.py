import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import base64
import os
from dotenv import load_dotenv

load_dotenv()

def get_access_token():
    consumer_key    = os.getenv("DARAJA_CONSUMER_KEY")
    consumer_secret = os.getenv("DARAJA_CONSUMER_SECRET")
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    try:
        response = requests.get(api_url, auth=HTTPBasicAuth(consumer_key, consumer_secret))
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"Access Token Error: {response.text}")
            return None
    except Exception as e:
        print(f"Error getting access token: {e}")
        return None


def send_stk_push(phone, amount, order_number):
    access_token = get_access_token()
    if not access_token:
        return {"ResponseCode": "1", "ResponseDescription": "Failed to get access token"}

    shortcode = "174379"
    passkey   = os.getenv("DARAJA_PASSKEY")
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    # Generate password
    data_to_encode = shortcode + passkey + timestamp
    password = base64.b64encode(data_to_encode.encode()).decode('utf-8')

    # ── CALLBACK URL ─────────────────────────────────────────────
    # Read from .env so you only change it in one place when ngrok restarts
    # In your .env file add:  CALLBACK_URL=https://YOUR-NGROK-URL.ngrok-free.app/mpesa/callback
    callback_url = os.getenv(
        "CALLBACK_URL",
        "https://elidible-ungroundable-cheryll.ngrok-free.dev/mpesa/callback"
    )

    # Format phone: must be 2547XXXXXXXX (12 digits, no + or spaces)
    phone = format_phone(phone)

    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": f"Bearer {access_token}"}

    payload = {
        "BusinessShortCode": shortcode,
        "Password":          password,
        "Timestamp":         timestamp,
        "TransactionType":   "CustomerPayBillOnline",
        "Amount":            int(float(amount)),
        "PartyA":            phone,
        "PartyB":            shortcode,
        "PhoneNumber":       phone,
        "CallBackURL":       callback_url,
        "AccountReference":  order_number,
        "TransactionDesc":   f"Payment for Order {order_number}"
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        print(f"STK Push payload: {payload}")
        print(f"Safaricom Response: {response.text}")
        return response.json()
    except Exception as e:
        print(f"STK Push Error: {e}")
        return {"ResponseCode": "1", "ResponseDescription": str(e)}


def format_phone(phone):
    """
    Converts any Kenyan phone format to 2547XXXXXXXX
    Accepts: 0712345678 / +254712345678 / 254712345678 / 712345678
    """
    phone = str(phone).strip().replace(' ', '').replace('-', '')

    if phone.startswith('+'):
        phone = phone[1:]          # remove +

    if phone.startswith('0'):
        phone = '254' + phone[1:]  # 07XX → 2547XX

    if phone.startswith('7') or phone.startswith('1'):
        phone = '254' + phone      # 7XX → 2547XX

    return phone