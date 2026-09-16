"""Integracao com a Evolution API (https://github.com/EvolutionAPI/evolution-api),
um servidor open-source de WhatsApp (via Baileys/WhatsApp Web multi-device).

Cada numero de WhatsApp e uma "instance" na Evolution API. E a instance que
identifica para qual clinica uma mensagem recebida pertence (equivalente ao
`phone_number_id` da API oficial da Meta).
"""
from __future__ import annotations

import hmac

import httpx

import config


def verify_webhook_secret(received_secret: str | None) -> bool:
    """Valida o segredo enviado na URL do webhook (?secret=...).

    A Evolution API nao assina o payload como a Meta faz (X-Hub-Signature),
    entao a forma recomendada de proteger o endpoint e usar uma URL de
    webhook com um segredo dificil de adivinhar, configurado por instance.
    """
    if not config.EVOLUTION_WEBHOOK_SECRET:
        # Sem segredo configurado, nao ha o que validar (uso em dev).
        return True
    if not received_secret:
        return False
    return hmac.compare_digest(config.EVOLUTION_WEBHOOK_SECRET, received_secret)


async def send_text_message(instance: str, to: str, text: str) -> None:
    """Envia uma mensagem de texto simples pela instance da clinica."""
    url = f"{config.EVOLUTION_API_URL}/message/sendText/{instance}"
    headers = {
        "apikey": config.EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {"number": to, "text": text}

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()


def extract_incoming_message(instance_name: str, webhook_body: dict) -> dict | None:
    """Extrai a mensagem de texto de um evento `messages.upsert` da Evolution API.

    Retorna None quando o evento nao e uma mensagem de texto nova de um
    paciente (ex: e eco de mensagem enviada por nos mesmos, e de um grupo,
    ou e outro tipo de evento como atualizacao de conexao).
    """
    if webhook_body.get("event") != "messages.upsert":
        return None

    data = webhook_body.get("data") or {}
    key = data.get("key") or {}

    if key.get("fromMe"):
        return None

    remote_jid = key.get("remoteJid") or ""
    if not remote_jid or remote_jid.endswith("@g.us"):
        # Ignora mensagens de grupo; o agente atende conversas individuais.
        return None

    message = data.get("message") or {}
    text = (
        message.get("conversation")
        or (message.get("extendedTextMessage") or {}).get("text")
        or (message.get("buttonsResponseMessage") or {}).get("selectedDisplayText")
        or (message.get("listResponseMessage") or {}).get("title")
        or ""
    ).strip()

    if not text:
        return None

    wa_id = remote_jid.split("@")[0]

    return {
        "instance": instance_name,
        "wa_id": wa_id,
        "message_id": key.get("id", ""),
        "text": text,
    }
