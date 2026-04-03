import requests
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (2 levels up from this file)
# This file is at: app/whatsapp_client.py
# .env is at:      vogueswear/.env
load_dotenv(Path(__file__).parent.parent / '.env')


def send_whatsapp_message(recipient_phone, message_text):
    """
    The Core Engine: Sends any text message to a phone number via WhatsApp Cloud API.
    """
    token    = os.getenv('WHATSAPP_TOKEN')
    phone_id = os.getenv('WHATSAPP_PHONE_ID')

    if not token or not phone_id:
        print("❌ ERROR: WHATSAPP_TOKEN or WHATSAPP_PHONE_ID not found in .env")
        return {"error": "Missing WhatsApp credentials"}

    # Clean phone number — WhatsApp needs: 254712345678
    clean_phone = str(recipient_phone).replace("+", "").replace(" ", "").replace("-", "")

    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                clean_phone,
        "type":              "text",
        "text": {
            "preview_url": False,
            "body":        message_text
        }
    }

    try:
        print(f"\n--- 📲 WhatsApp Gateway: Attempting send to {clean_phone} ---")
        response = requests.post(url, headers=headers, json=data, timeout=10)
        res_data = response.json()

        if response.status_code == 200:
            print("✅ SUCCESS: WhatsApp delivered to Meta's servers.")
            return res_data
        else:
            print(f"❌ FAILED: Meta rejected the message (Status {response.status_code})")
            print("🔍 DEBUG DATA FROM META:")
            print(json.dumps(res_data, indent=4))

            error_code = res_data.get('error', {}).get('code')
            if error_code == 190:
                print("💡 FIX: Your Access Token has expired. Get a new one from Meta Dashboard.")
            elif error_code == 100:
                print("💡 FIX: Check your phone number format or ensure it's verified in Sandbox.")
            return res_data

    except Exception as e:
        print(f"⚠️ CONNECTION ERROR: {e}")
        return {"error": str(e)}


def send_order_receipt(order):
    """Sends order confirmation WhatsApp to customer after payment."""
    items_list    = order.get_whatsapp_items()
    delivery_date = order.get_delivery_date()

    message = (
        f"🛍️ *VOGUE'S WEAR: ORDER CONFIRMED*\n"
        f"--------------------------------\n"
        f"Hi *{order.customer_name}*,\n"
        f"Your order has been placed successfully!\n\n"
        f"📌 *Order:* #{order.order_number}\n"
        f"📦 *Items:*\n{items_list}\n"
        f"💰 *Total:* KSh {order.total:,}\n"
        f"📍 *Delivery:* {order.delivery_address}\n"
        f"📅 *Est. Arrival:* {delivery_date}\n\n"
        f"--------------------------------\n"
        f"_Style meets convenience. — Vogue's Wear_"
    )

    return send_whatsapp_message(order.customer_phone, message)


def send_shipping_notification(order):
    """Sends shipping update when admin marks order as Shipped."""
    message = (
        f"🚀 *VOGUE'S WEAR: ORDER SHIPPED*\n"
        f"--------------------------------\n"
        f"Hi *{order.customer_name}*,\n"
        f"Great news! Your order *#{order.order_number}* is on the move! 🎉\n\n"
        f"📦 *Status:* Out for Delivery\n"
        f"📅 *Expected:* {order.get_delivery_date()}\n"
        f"📍 *To:* {order.delivery_address}\n\n"
        f"Get ready to rock your new style! ✨\n"
        f"--------------------------------"
    )

    return send_whatsapp_message(order.customer_phone, message)


if __name__ == "__main__":
    # Test your connection: python app/whatsapp_client.py
    test_num = os.getenv('WHATSAPP_RECIPIENT')
    if test_num:
        send_whatsapp_message(test_num, "🚀 Vogue's Wear Test: WhatsApp is connected!")
    else:
        print("⚠️ No WHATSAPP_RECIPIENT found in .env file.")