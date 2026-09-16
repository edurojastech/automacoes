"""Ponto de entrada da automacao: recebe mensagens do WhatsApp (via
Evolution API), aciona o agente de IA (Claude + base de conhecimento +
Google Calendar) e responde.

Rodar localmente:
    uvicorn main:app --reload --port 8000

Depois, exponha a porta publicamente (ex: ngrok) e configure a URL
`https://SEU_DOMINIO/webhook/evolution/<instance>?secret=SEU_SEGREDO` como
webhook da instance correspondente na Evolution API.
"""
from __future__ import annotations

import logging

from fastapi import BackgroundTasks, FastAPI, Request, Response

from agent.claude_agent import handle_message
from clinics.loader import get_clinic_by_evolution_instance
from integrations import evolution_client
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


@app.post("/webhook/evolution/{instance_name}")
async def receive_webhook(
    instance_name: str, request: Request, background_tasks: BackgroundTasks
) -> Response:
    if not evolution_client.verify_webhook_secret(request.query_params.get("secret")):
        logger.warning("Segredo invalido no webhook da instance %s.", instance_name)
        return Response(status_code=403)

    payload = await request.json()
    incoming = evolution_client.extract_incoming_message(instance_name, payload)

    # Responde 200 rapido para a Evolution API nao reenviar o webhook; o
    # processamento (chamada ao Claude, Google Calendar etc.) roda depois.
    if incoming:
        background_tasks.add_task(_process_incoming_message, incoming)

    return Response(status_code=200)


async def _process_incoming_message(incoming: dict) -> None:
    instance_name = incoming["instance"]
    wa_id = incoming["wa_id"]
    user_text = incoming["text"]

    clinic = get_clinic_by_evolution_instance(instance_name)
    if clinic is None:
        logger.error("Nenhuma clinica configurada para a instance=%s", instance_name)
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
        await evolution_client.send_text_message(clinic.evolution_instance, wa_id, reply_text)
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao enviar resposta pelo WhatsApp para %s", wa_id)
