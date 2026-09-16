"""Loop do agente de IA: recebe a mensagem do paciente, conversa com o
Claude (com acesso a ferramentas de agenda) e devolve a resposta final em
texto para ser enviada de volta pelo WhatsApp.
"""
from __future__ import annotations

import datetime as dt
import logging

from anthropic import Anthropic
from zoneinfo import ZoneInfo

import config
from agent import tools
from integrations.google_calendar_client import AgendaError
from storage import conversation_store as store

logger = logging.getLogger(__name__)

_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

MAX_TOOL_ITERATIONS = 6
MAX_HISTORY_MESSAGES = 20


def _system_prompt(clinic) -> str:
    now = dt.datetime.now(ZoneInfo(clinic.timezone))
    contexto_data = (
        f"\n## Contexto atual\nData e hora agora: {now.strftime('%A, %d/%m/%Y %H:%M')} "
        f"({clinic.timezone}). Use isso para interpretar termos como 'hoje', "
        f"'amanha' ou 'semana que vem'.\n"
    )
    return clinic.build_system_prompt() + contexto_data


def _run_tool_loop(clinic, wa_id: str, messages: list[dict]) -> str:
    for _ in range(MAX_TOOL_ITERATIONS):
        response = _client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=1024,
            system=_system_prompt(clinic),
            tools=tools.TOOL_SCHEMAS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            return "".join(
                block.text for block in response.content if block.type == "text"
            ).strip()

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                result = tools.dispatch(clinic, wa_id, block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": store.dumps(result),
                    }
                )
            except AgendaError as exc:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(exc),
                        "is_error": True,
                    }
                )
            except Exception:  # noqa: BLE001
                logger.exception("Erro executando a ferramenta %s", block.name)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Erro interno ao executar a ferramenta. Tente novamente.",
                        "is_error": True,
                    }
                )

        messages.append({"role": "user", "content": tool_results})

    return (
        "Desculpe, tive um problema para concluir sua solicitacao agora. "
        "Pode tentar novamente em instantes ou pedir para falar com a recepcao?"
    )


def handle_message(clinic, wa_id: str, user_text: str) -> str:
    """Processa a mensagem do paciente e retorna a resposta do agente."""
    history = store.get_recent_history(clinic.clinic_id, wa_id, MAX_HISTORY_MESSAGES)
    messages = [{"role": h["role"], "content": h["content"]} for h in history]
    messages.append({"role": "user", "content": user_text})

    store.append_message(clinic.clinic_id, wa_id, "user", user_text)

    reply_text = _run_tool_loop(clinic, wa_id, messages)

    store.append_message(clinic.clinic_id, wa_id, "assistant", reply_text)

    return reply_text
