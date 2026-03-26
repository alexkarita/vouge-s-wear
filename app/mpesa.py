import requests
import base64
from datetime import datetime
import os
from dotenv import load_dotenv

# Load variables from your .env file
load_dotenv()

def get_access_token():
    """Gets the OAuth2 Access Token from Safaricom."""
    consumer_key = os.getenv('DARAJA_CONSUMER_KEY')
    consumer_secret = os.getenv('DARAJA_CONSUMER_SECRET')
    
    api_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    
    try:
        # We use 'auth' to pass the Key and Secret
        r = requests.get(api_URL, auth=(consumer_key, consumer_secret))
        token = r.json().get('access_token')
        return token
    except Exception as e:
        print(f"Error getting access token: {e}")
        return None

def send_stk_push(phone, amount, order_number):
    """Triggers the STK Push prompt on the customer's phone."""
    access_token = get_access_token()
    if not access_token:
        return {"Error": "Failed to get access token"}

    # 1. Generate Timestamp (Format: YYYYMMDDHHMMSS)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    
    # 2. Setup Shortcode & Passkey (Standard Sandbox values)
    shortcode = "174379"
    passkey = os.getenv('DARAJA_PASSKEY')
    
    # 3. Create Password (Base64 encoded: Shortcode + Passkey + Timestamp)
    data_to_encode = shortcode + passkey + timestamp
    password = base64.b64encode(data_to_encode.encode()).decode('utf-8')
    
    # 4. Prepare the Request
    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline", # Paybill simulation
        "Amount": int(amount),
        "PartyA": phone, # Customer phone (must start with 254)
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": "https://elidible-ungroundable-cheryll.ngrok-free.app/mpesa/callback", # We will build this listener next
        "AccountReference": order_number,
        "TransactionDesc": f"Vogues Wear Order {order_number}"
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        print(f"Safaricom Response: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Error triggering STK Push: {e}")
        return {"Error": str(e)}