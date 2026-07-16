from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from config.settings import KNOWLEDGE_SYNC_TOKEN
from knowledge.answer_service import answer_knowledge_question
from line.webhook import handle_line_webhook
from storage.google_oauth import create_authorization_url, exchange_callback

app = FastAPI(title="LINE AI Assistant", version="0.9.1.1")

def _verify_token(token: str | None) -> None:
    if not KNOWLEDGE_SYNC_TOKEN or token != KNOWLEDGE_SYNC_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/")
def health_check():
    return {"status":"ok","service":"LINE AI Assistant","version":"0.9.1.1"}

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature")
    result, status_code = await handle_line_webhook(body, signature)
    return JSONResponse(content=result, status_code=status_code)

@app.get("/knowledge/answer")
def knowledge_answer(
    q: str = Query(min_length=2, max_length=500),
    x_knowledge_token: str | None = Header(default=None),
):
    _verify_token(x_knowledge_token)
    return answer_knowledge_question(question=q)

@app.get("/google/oauth/start")
def google_oauth_start(token: str = Query(min_length=10)):
    _verify_token(token)
    return RedirectResponse(create_authorization_url())

@app.get("/google/oauth/callback", response_class=HTMLResponse)
def google_oauth_callback(request: Request, state: str):
    result = exchange_callback(
        authorization_response=str(request.url),
        state=state,
    )

    refresh_token = result["refresh_token"]
    folder_id = result["folder_id"]
    folder_link = result.get("folder_web_view_link") or "#"

    return HTMLResponse(f"""
    <html>
      <head><meta charset="utf-8"><title>Google OAuth 完成</title></head>
      <body style="font-family:sans-serif;max-width:800px;margin:40px auto;">
        <h1>Google OAuth 授權完成</h1>
        <p>請立即把以下兩個值加入 Render Environment。</p>
        <h2>GOOGLE_OAUTH_REFRESH_TOKEN</h2>
        <textarea style="width:100%;height:120px;">{refresh_token}</textarea>
        <h2>GOOGLE_ATTACHMENT_FOLDER_ID</h2>
        <textarea style="width:100%;height:70px;">{folder_id}</textarea>
        <p><a href="{folder_link}" target="_blank">開啟 LINE_AI_Attachments 資料夾</a></p>
        <p>設定完成後請關閉此頁，不要分享 Refresh Token。</p>
      </body>
    </html>
    """)
