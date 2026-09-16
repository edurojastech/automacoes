"""Ponto de entrada da automacao: recebe mensagens do WhatsApp, aciona o
agente de IA (Claude + base de conhecimento + Google Calendar) e responde.

Rodar localmente:
    uvicorn main:app --reload --port 8000

Depois, exponha a porta publicamente (ex: ngrok) e configure a URL
`https://SEU_DOMINIO/webhook/whatsapp` no painel do WhatsApp Business API.
"""
from __future__ import annotations

import logging

from fastapi import BackgroundTasks, FastAPI, Request, Response

import config
from agent.claude_agent import handle_message
from clinics.loader import get_clinic_by_phone_number_id
from integrations import whatsapp_client
from storage import conversation_store as store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp_ai_agent")

app = FastAPI(title="WhatsApp AI Agent")


@app.on_event("startup")
def startup() -> None:
    store.init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/webhook/whatsapp")
def verify_webhook(request: Request) -> Response:
    """Handshake exigido pela Meta ao configurar o webhook."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge", "")

    if mode == "subscribe" and token == config.WHATSAPP_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")

    return Response(status_code=403)


@app.post("/webhook/whatsapp")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks) -> Response:
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not whatsapp_client.verify_signature(raw_body, signature):
        logger.warning("Assinatura invalida recebida no webhook do WhatsApp.")
        return Response(status_code=403)

    payload = await request.json()
    incoming = whatsapp_client.extract_incoming_message(payload)

    # Sempre responde 200 rapido pro Meta nao reenviar o webhook; o
    # processamento (chamada ao Claude, Google Calendar etc.) roda depois.
    if incoming:
        background_tasks.add_task(_process_incoming_message, incoming)

    return Response(status_code=200)


async def _process_incoming_message(incoming: dict) -> None:
    phone_number_id = incoming["phone_number_id"]
    wa_id = incoming["wa_id"]
    user_text = incoming["text"]

    clinic = get_clinic_by_phone_number_id(phone_number_id)
    if clinic is None:
        logger.error(
            "Nenhuma clinica configurada para phone_number_id=%s", phone_number_id
        )
        return

    try:
        reply_text = handle_message(clinic, wa_id, user_text)
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao processar mensagem de %s", wa_id)
        reply_text = (
            "Desculpe, tive um problema tecnico agora. Pode tentar novamente "
            "em instantes?"
        )

    try:
        await whatsapp_client.send_text_message(phone_number_id, wa_id, reply_text)
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao enviar resposta pelo WhatsApp para %s", wa_id)
