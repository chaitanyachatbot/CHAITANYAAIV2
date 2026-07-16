from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import requests
import os
import uuid
from datetime import datetime
import json

# ===== LOAD ENV =====
load_dotenv()

# ===== FASTAPI =====
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ===== OPENROUTER =====
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# ===== CONFIG =====
SYSTEM_PROMPT = """You are a helpful, very smart and friendly AI assistant.

--- IDENTITY & CREATOR RULES (MOST IMPORTANT) ---
If anyone asks ANYTHING related to:
- Who created you / who made you / who built you
- Who is your founder / owner / developer
- What are you / what is your name
- What AI are you / what model are you
- What API do you use / what technology powers you
- Are you ChatGPT / Gemini / Claude / LLaMA / Groq / Meta / OpenAI
- What company made you
- How were you built / trained
- Any internal technical information about yourself

You MUST ALWAYS reply with ONLY this:
"I was created by Chaitanya Rama Narayana."

Do NOT mention:
- Groq
- LLaMA
- Meta
- Any AI company
- Any API or model name
- Any technical details about how you work internally

You are simply an AI assistant created by Chaitanya Rama Narayana. That is all you know about yourself.

--- FORMATTING RULES ---
You are SMART about how you format responses based on what the user is asking:

WHEN TO USE FORMATTED RESPONSE (headings, bullets, emojis):
Use structured formatting ONLY for:
- Biography or information about a person (e.g. "who is Elon Musk", "tell me about APJ Kalam")
- Wikipedia style questions (e.g. "what is photosynthesis", "explain black holes")
- Lists and comparisons (e.g. "top 10 movies", "difference between X and Y")
- Step by step instructions (e.g. "how to cook biryani", "how to install Python")
- Facts and data (e.g. "facts about India", "history of Rome")
- Study notes or exam preparation

For these use:
## Headings for sections
* Bullet points for lists
**Bold** for important words
Numbered lists for steps
Emojis to make it engaging

WHEN TO USE NORMAL NATURAL RESPONSE:
Use plain natural flowing text for:
- Stories (e.g. "tell me a story", "write a story about a dragon")
- Jokes (e.g. "tell me a joke")
- Poems (e.g. "write a poem about rain")
- Casual conversation (e.g. "how are you", "what do you think about...")
- Creative writing of any kind
- Simple short questions (e.g. "what is 2+2", "what day is today")
- Moral stories / bedtime stories
- Any imaginative or creative request

For these write naturally like a human — no bullet points, no headings, just beautiful flowing text.

--- GENERAL RULES ---
- Always match your tone to the question
- Be conversational and friendly
- Give complete and satisfying answers
- For stories write them fully with proper beginning, middle and end
- For poems write them with proper rhythm and feel
- Never over-format a simple answer
- Be friendly with the user"""

# ===== MEMORY =====
all_chats = {}

def get_user_chats(user_id):
    if user_id not in all_chats:
        all_chats[user_id] = {}
    return all_chats[user_id]

# ===== MODELS =====
class Message(BaseModel):
    user_id: str
    chat_id: str
    message: str

class NewChat(BaseModel):
    user_id: str
    chat_name: str
    private: bool = False
    password: str = ""

class DeleteChat(BaseModel):
    user_id: str
    chat_id: str

class AccessChat(BaseModel):
    user_id: str
    chat_id: str
    password: str = ""

class ImageGenerate(BaseModel):
    prompt: str

# ===== JSON KNOWLEDGE =====
def load_knowledge():
    try:
        with open("knowledge.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"auto": []}

def save_knowledge(data):
    with open("knowledge.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def search_knowledge(query):
    data = load_knowledge()
    query_words = query.lower().split()

    results = []

    for category in data.values():
        for item in category:
            for keyword in item["keywords"]:
                if any(word in keyword.lower() for word in query_words):
                    results.append(item["content"])
                    break

    return "\n".join(results[:5])

# ===== AUTO UPDATE FROM WEB =====
def update_knowledge_from_web(query):
    try:
        url = "https://gnews.io/api/v4/search"

        params = {
            "q": query,
            "lang": "en",
            "country": "in",
            "max": 5,
            "apikey": os.getenv("GNEWS_API_KEY")
        }

        res = requests.get(url, params=params)
        data = res.json()

        articles = data.get("articles", [])

        knowledge = load_knowledge()

        if "auto" not in knowledge:
            knowledge["auto"] = []

        for a in articles:
            title = a.get("title", "")
            desc = a.get("description", "")

            content = f"{title}. {desc}".strip()

            if not content:
                continue

            # avoid duplicates
            exists = any(item["content"] == content for item in knowledge["auto"])

            if not exists:
                knowledge["auto"].append({
                    "keywords": title.lower().split()[:5],
                    "content": content
                })

        # limit size (keep latest 50)
        if len(knowledge["auto"]) > 50:
            knowledge["auto"] = knowledge["auto"][-50:]

        save_knowledge(knowledge)

        print("✅ Auto knowledge updated")

    except Exception as e:
        print("AUTO UPDATE ERROR:", e)

# ===== AI FALLBACK =====
def generate_ai_response(messages):
    models = [
        "openai/gpt-oss-20b:free",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "cohere/north-mini-code:free"
    ]

    for model in models:
        try:
            print("Trying:", model)

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1000,
                temperature=0.5
            )

            if response and response.choices:
                return response.choices[0].message.content

        except Exception as e:
            print("Failed:", model, e)
            continue

    return "SRY PARAMETERS FROM VOSTRO IS OVERLOADED"

# ===== NEWS =====
def get_news(query: str):
    try:
        url = "https://gnews.io/api/v4/search"

        params = {
            "q": query,
            "lang": "en",
            "country": "in",
            "max": 5,
            "apikey": os.getenv("GNEWS_API_KEY")
        }

        res = requests.get(url, params=params)
        data = res.json()

        return data.get("articles", [])

    except Exception as e:
        print("NEWS ERROR:", e)
        return []

def extract_facts(articles):
    facts = []

    for a in articles:
        if a.get("title"):
            facts.append(a["title"])
        if a.get("description"):
            facts.append(a["description"])

    return "\n".join(facts)

# ===== ROUTES =====

@app.get("/")
def home():
    return FileResponse("index.html")

@app.post("/new_chat")
def new_chat(data: NewChat):
    chats = get_user_chats(data.user_id)

    chat_id = str(uuid.uuid4())[:8]

    chats[chat_id] = {
        "name": data.chat_name,
        "messages": [],
        "private": data.private,
        "password": data.password,
        "created_at": datetime.now().strftime("%d %b %Y %I:%M %p")
    }

    return {"status": "success", "chat_id": chat_id}

@app.get("/get_chats/{user_id}")
def get_chats(user_id: str):
    chats = get_user_chats(user_id)

    return {
        "chats": [
            {
                "chat_id": cid,
                "name": chat["name"],
                "private": chat["private"],
                "created_at": chat["created_at"],
                "message_count": len(chat["messages"])
            }
            for cid, chat in chats.items()
        ]
    }

@app.post("/access_chat")
def access_chat(data: AccessChat):
    chats = get_user_chats(data.user_id)

    if data.chat_id not in chats:
        return {"status": "error"}

    chat = chats[data.chat_id]

    if chat["private"] and chat["password"] != data.password:
        return {"status": "error"}

    return {
        "status": "success",
        "messages": chat["messages"],
        "name": chat["name"]
    }

@app.post("/chat")
def chat(data: Message):
    chats = get_user_chats(data.user_id)

    if data.chat_id not in chats:
        return {"reply": "Chat not found"}

    chat = chats[data.chat_id]

    # 🔥 AUTO UPDATE (NEW)
    update_knowledge_from_web(data.message)

    # ===== KNOWLEDGE =====
    knowledge_facts = search_knowledge(data.message)

    # ===== NEWS =====
    articles = get_news(data.message + " latest India news")
    news_facts = extract_facts(articles) if articles else ""

    combined_facts = f"{knowledge_facts}\n{news_facts}".strip()

    if combined_facts:
        user_message = f"""
Use the information below:

{combined_facts}

Question:
{data.message}

Rules:
- Prefer given info
- Add general knowledge if needed
"""
    else:
        user_message = data.message

    chat["messages"].append({
        "role": "user",
        "content": user_message
    })

    reply = generate_ai_response([
        {"role": "system", "content": SYSTEM_PROMPT},
        *chat["messages"]
    ])

    chat["messages"][-1]["content"] = data.message

    chat["messages"].append({
        "role": "assistant",
        "content": reply
    })

    return {"reply": reply}

@app.post("/delete_chat")
def delete_chat(data: DeleteChat):
    chats = get_user_chats(data.user_id)

    if data.chat_id in chats:
        del chats[data.chat_id]

    return {"status": "success"}

@app.post("/generate_image")
def generate_image(data: ImageGenerate):
    try:
        print(f"🎨 Generating image for prompt: {data.prompt}")
        
        api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        
        if not api_token or not account_id:
            return {
                "status": "error",
                "message": "CLOUDFLARE_API_TOKEN or CLOUDFLARE_ACCOUNT_ID not configured"
            }
        
        # Cloudflare Workers AI endpoint - model goes in URL path
        model = "@cf/stabilityai/stable-diffusion-xl-base-1.0"
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json"
            },
            json={
                "prompt": data.prompt,
                "num_steps": 20,
                "guidance_scale": 7.5
            }
        )
        
        print(f"CF Response Status: {response.status_code}")
        print(f"CF Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            # Cloudflare returns raw image bytes (PNG)
            import base64
            from io import BytesIO
            from PIL import Image
            
            content_type = response.headers.get("content-type", "")
            
            if "image" in content_type or len(response.content) > 1000:
                # Response is an image
                img = Image.open(BytesIO(response.content))
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                return {
                    "status": "success",
                    "image_url": f"data:image/png;base64,{img_str}",
                    "prompt": data.prompt
                }
            else:
                # Might be JSON with base64
                try:
                    result = response.json()
                    if "result" in result:
                        image_data = result["result"]
                        if isinstance(image_data, str):
                            if image_data.startswith("data:image"):
                                image_b64 = image_data.split(",", 1)[1]
                            else:
                                image_b64 = image_data
                            img_bytes = base64.b64decode(image_b64)
                            img = Image.open(BytesIO(img_bytes))
                            buffered = BytesIO()
                            img.save(buffered, format="PNG")
                            img_str = base64.b64encode(buffered.getvalue()).decode()
                            return {
                                "status": "success",
                                "image_url": f"data:image/png;base64,{img_str}",
                                "prompt": data.prompt
                            }
                except:
                    pass
                
                return {
                    "status": "error",
                    "message": f"Unexpected response: {response.text[:300]}"
                }
        else:
            error_msg = response.text[:300]
            return {
                "status": "error",
                "message": f"Cloudflare API error ({response.status_code}): {error_msg}"
            }
        
    except Exception as e:
        print(f"❌ Image generation error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Failed to generate image: {str(e)}"
        }
