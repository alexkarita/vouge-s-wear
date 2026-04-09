import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_styling_advice(product_name, category):
    """Original function for general text-based styling tips."""
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert fashion stylist for Vogue's Wear. Give 3 short, punchy styling tips."},
                {"role": "user", "content": f"What should I wear with a {product_name} ({category})?"}
            ],
            temperature=0.7,
            max_tokens=200
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Stylist is away: {str(e)}"

def get_complete_the_look(current_product, inventory_list):
    """
    Feeds real database items to Groq and asks for 2 specific matches.
    Returns a dictionary with a tip and product IDs.
    """
    inventory_data = "\n".join([
        f"ID: {p.id} | Name: {p.name} | Cat: {p.category}" 
        for p in inventory_list
    ])

    prompt = f"""
    CUSTOMER IS VIEWING: {current_product.name} ({current_product.category})
    
    AVAILABLE INVENTORY:
    {inventory_data}

    TASK:
    1. Pick exactly 2 items from the AVAILABLE INVENTORY that best 'Complete the Look'.
    2. Provide a 1-sentence styling tip.
    3. Respond ONLY in this JSON format, no extra text:
    {{
        "tip": "styling advice here",
        "recommended_ids": [id1, id2]
    }}
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a database-aware fashion coordinator. You only recommend IDs that exist in the provided list. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=200
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"Groq JSON Error: {e}")
        return {"tip": "Mix and match for a unique look!", "recommended_ids": []}

def get_chat_recommendations(messages, inventory_list):
    """
    Handles conversational chat with context and product awareness.
    'messages' is the list of conversation history from the Flask session.
    """
    inventory_text = "\n".join([
        f"- {p.name} (KES {p.price}) | Cat: {p.category}" 
        for p in inventory_list
    ])
    
    system_prompt = {
        "role": "system", 
        "content": f"""You are the official Vogue's Wear AI Stylist. 
        Your goal is to help customers find outfits for specific events (weddings, interviews, dates).
        
        CURRENT STOCK AT VOGUE'S WEAR:
        {inventory_text}
        
        RULES:
        1. Use the inventory above to make recommendations. 
        2. If a customer mentions an event, remember it throughout the chat.
        3. Keep your tone chic, helpful, and professional.
        4. When suggesting a product, mention its price from the list.
        """
    }
    
    full_payload = [system_prompt] + messages

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=full_payload,
            temperature=0.6,
            max_tokens=500
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Chat AI Error: {e}")
        return "I'm having a bit of trouble accessing my wardrobe right now. How else can I help?"