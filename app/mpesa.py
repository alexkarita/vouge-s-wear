import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import base64
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (2 levels up from this file)
# This file is at: app/mpesa.py
# .env is at:      vogueswear/.env
load_dotenv(Path(__file__).parent.parent / '.env')


def get_access_token():
    consumer_key    = os.getenv("DARAJA_CONSUMER_KEY")
    consumer_secret = os.getenv("DARAJA_CONSUMER_SECRET")

    if not consumer_key or not consumer_secret:
        print("❌ ERROR: DARAJA_CONSUMER_KEY or DARAJA_CONSUMER_SECRET not found in .env")
        return None

    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    try:
        response = requests.get(api_url, auth=HTTPBasicAuth(consumer_key, consumer_secret))
        if response.status_code == 200:
            token = response.json().get("access_token")
            print(f"✅ Access token obtained: {token[:20]}...")
            return token
        else:
            print(f"❌ Access Token Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error getting access token: {e}")
        return None


def send_stk_push(phone, amount, order_number):
    access_token = get_access_token()
    if not access_token:
        return {"ResponseCode": "1", "ResponseDescription": "Failed to get access token"}

    shortcode = "174379"
    passkey   = os.getenv("DARAJA_PASSKEY")

    if not passkey:
        print("❌ ERROR: DARAJA_PASSKEY not found in .env")
        return {"ResponseCode": "1", "ResponseDescription": "Passkey missing"}

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    # Generate password
    data_to_encode = shortcode + passkey + timestamp
    password = base64.b64encode(data_to_encode.encode()).decode('utf-8')

    # Callback URL — update this in .env when ngrok restarts
    callback_url = os.getenv(
        "CALLBACK_URL",
        "https://elidible-ungroundable-cheryll.ngrok-free.dev/mpesa/callback"
    )

    # Format phone to 2547XXXXXXXX
    phone = format_phone(phone)
    print(f"📱 Sending STK push to: {phone}")

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
        print(f"📤 STK Push sent to Safaricom")
        print(f"📩 Safaricom Response: {response.text}")
        return response.json()
    except Exception as e:
        print(f"❌ STK Push Error: {e}")
        return {"ResponseCode": "1", "ResponseDescription": str(e)}


def format_phone(phone):
    """
    Converts any Kenyan phone format to 2547XXXXXXXX
    Accepts: 0712345678 / +254712345678 / 254712345678 / 712345678
    """
    phone = str(phone).strip().replace(' ', '').replace('-', '')

    if phone.startswith('+'):
        phone = phone[1:]

    if phone.startswith('0'):
        phone = '254' + phone[1:]

    if phone.startswith('7') or phone.startswith('1'):
        phone = '254' + phone

    return phone