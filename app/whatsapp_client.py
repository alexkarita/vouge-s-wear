import requests
import json
import os
from dotenv import load_dotenv

# Load variables from your .env file
load_dotenv()

def send_whatsapp_message(recipient_phone, message_text):
    """
    The Core Engine: Sends any text to a phone number.
    DEBUGGING ADDED: This will print the exact Meta error to your terminal.
    """
    token = os.getenv('WHATSAPP_TOKEN')
    phone_id = os.getenv('WHATSAPP_PHONE_ID')
    
    # Clean the phone number (removes +, spaces, and dashes)
    # WhatsApp needs: 254712345678
    clean_phone = str(recipient_phone).replace("+", "").replace(" ", "").replace("-", "")

    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message_text
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
            # --- DEBUG SECTION ---
            print(f"❌ FAILED: Meta rejected the message (Status {response.status_code})")
            print("🔍 DEBUG DATA FROM META:")
            print(json.dumps(res_data, indent=4)) 
            
            error_code = res_data.get('error', {}).get('code')
            if error_code == 190:
                print("💡 FIX: Your Access Token has expired. Get a new one from Meta Dashboard.")
            elif error_code == 100:
                print("💡 FIX: Check your phone number format or ensure it's 'Verified' in Sandbox.")
            return res_data

    except Exception as e:
        print(f"⚠️ CONNECTION ERROR: {e}")
        return {"error": str(e)}

def send_order_receipt(order):
    """
    Formats the Vogue's Wear receipt using real order data.
    """
    items_list = order.get_whatsapp_items()
    delivery_date = order.get_delivery_date()

    message = (
        f"🛍️ *VOGUE'S WEAR: ORDER CONFIRMED*\n"
        f"--------------------------------\n"
        f"Hi *{order.customer_name}*,\n"
        f"Your payment of KSh {order.total:,} was successful!\n\n"
        f"📌 *Order:* #{order.order_number}\n"
        f"📦 *Items:*\n{items_list}\n"
        f"📍 *Delivery:* {order.delivery_address}\n"
        f"📅 *Est. Arrival:* {delivery_date}\n\n"
        f"🚚 *Track:* https://vogueswear.com/track/{order.order_number}\n"
        f"--------------------------------\n"
        f"_Style meets convenience._"
    )

    return send_whatsapp_message(order.customer_phone, message)

def send_shipping_notification(order):
    """
    NEW: Formats the shipping update when the Admin marks as Shipped.
    """
    message = (
        f"🚀 *VOGUE'S WEAR: ORDER SHIPPED*\n"
        f"--------------------------------\n"
        f"Hi *{order.customer_name}*,\n"
        f"Great news! Your order *#{order.order_number}* is on the move.\n\n"
        f"📦 *Status:* Out for Delivery\n"
        f"📅 *Expected:* Tomorrow\n"
        f"📍 *To:* {order.delivery_address}\n\n"
        f"Get ready to rock your new style! ✨\n"
        f"--------------------------------"
    )

    return send_whatsapp_message(order.customer_phone, message)

if __name__ == "__main__":
    # Test your connection directly: 'python app/whatsapp_client.py'
    test_num = os.getenv('WHATSAPP_RECIPIENT')
    if test_num:
        send_whatsapp_message(test_num, "🚀 Vogue's Wear Debug Test: System is Live!")
    else:
        print("⚠️ No test recipient found in .env file.")