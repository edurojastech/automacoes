"""Cliente da WhatsApp Cloud API (Meta) e utilidades de webhook."""
from __future__ import annotations

import hashlib
import hmac

import httpx

import config

GRAPH_BASE_URL = "https://graph.facebook.com"


def verify_signature(payload: bytes, signature_header: str | None) -> bool:
    """Valida o header X-Hub-Signature-256 usando o App Secret do Meta."""
    if not config.WHATSAPP_APP_SECRET:
        # Sem app secret configurado, nao ha o que validar (uso em dev).
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        config.WHATSAPP_APP_SECRET.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


async def send_text_message(phone_number_id: str, to: str, text: str) -> None:
    """Envia uma mensagem de texto simples para o numero `to`."""
    url = f"{GRAPH_BASE_URL}/{config.WHATSAPP_API_VERSION}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {config.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text, "preview_url": False},
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()


async def mark_as_read(phone_number_id: str, message_id: str) -> None:
    url = f"{GRAPH_BASE_URL}/{config.WHATSAPP_API_VERSION}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {config.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()


def extract_incoming_message(webhook_body: dict) -> dict | None:
    """Extrai a primeira mensagem de texto de um payload de webhook do Meta.

    Retorna None se o payload nao contiver uma mensagem de texto suportada
    (ex: e um evento de status/delivery, ou uma midia nao suportada ainda).
    """
    try:
        entry = webhook_body["entry"][0]
        change = entry["changes"][0]
        value = change["value"]
        phone_number_id = value["metadata"]["phone_number_id"]

        messages = value.get("messages")
        if not messages:
            return None

        message = messages[0]
        wa_id = message["from"]
        msg_type = message.get("type")

        if msg_type == "text":
            body = message["text"]["body"]
        elif msg_type == "interactive":
            interactive = message["interactive"]
            body = (
                interactive.get("button_reply", {}).get("title")
                or interactive.get("list_reply", {}).get("title")
                or ""
            )
        elif msg_type == "button":
            body = message["button"]["text"]
        else:
            body = None

        if not body:
            return None

        return {
            "phone_number_id": phone_number_id,
            "wa_id": wa_id,
            "message_id": message["id"],
            "text": body,
        }
    except (KeyError, IndexError, TypeError):
        return None
