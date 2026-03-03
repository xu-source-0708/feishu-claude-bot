from fastapi import FastAPI, Request
import requests
import json
import anthropic
import os

app = FastAPI()

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)


def get_tenant_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    })
    return resp.json()["tenant_access_token"]


def send_feishu_message(user_id, content):
    token = get_tenant_token()
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=user_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "receive_id": user_id,
        "msg_type": "text",
        "content": json.dumps({"text": content})
    }
    requests.post(url, headers=headers, json=data)

from fastapi.responses import JSONResponse

@app.post("/webhook")
async def feishu_webhook(request: Request):
    body = await request.json()

    # 飞书验证
    if "challenge" in body:
        return JSONResponse(content={"challenge": body["challenge"]})

    event = body.get("event", {})
    message = event.get("message", {})
    sender = event.get("sender", {})

    if not message:
        return {"status": "ok"}

    user_id = sender.get("sender_id", {}).get("user_id")
    content = json.loads(message.get("content", "{}")).get("text", "")

    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=500,
        messages=[
            {"role": "user", "content": content}
        ]
    )

    reply_text = response.content[0].text
    send_feishu_message(user_id, reply_text)

    return {"status": "ok"}

