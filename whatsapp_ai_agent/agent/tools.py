"""Definicao das ferramentas (tools) que o agente de IA pode chamar.

Cada ferramenta e generica o bastante para funcionar com qualquer clinica:
o `clinic` (config + calendario) e sempre injetado pelo agente, nunca pelo
modelo.
"""
from __future__ import annotations

from integrations import google_calendar_client as calendar

TOOL_SCHEMAS = [
    {
        "name": "check_availability",
        "description": (
            "Verifica os horarios disponiveis para agendamento em uma data "
            "especifica, respeitando o expediente da clinica e os "
            "compromissos ja existentes na agenda. Sempre chame esta "
            "ferramenta antes de oferecer um horario ao paciente."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Data no formato AAAA-MM-DD.",
                },
                "service_name": {
                    "type": "string",
                    "description": (
                        "Nome do servico desejado (usado para saber a "
                        "duracao do horario). Opcional."
                    ),
                },
            },
            "required": ["date"],
        },
    },
    {
        "name": "book_appointment",
        "description": (
            "Cria um agendamento no Google Calendar da clinica, apos "
            "confirmar com o paciente a data, horario, nome e servico. So "
            "chame depois de confirmar disponibilidade com check_availability."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "AAAA-MM-DD"},
                "time": {"type": "string", "description": "HH:MM (24h)"},
                "patient_name": {"type": "string"},
                "service_name": {"type": "string"},
                "notes": {
                    "type": "string",
                    "description": "Observacoes extras (convenio, queixa, etc).",
                },
            },
            "required": ["date", "time", "patient_name", "service_name"],
        },
    },
    {
        "name": "cancel_appointment",
        "description": "Cancela um agendamento existente do paciente, dado o event_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "list_my_appointments",
        "description": (
            "Lista os proximos agendamentos futuros do paciente que esta "
            "conversando (usa o numero de WhatsApp dele automaticamente)."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]


def _service_duration(clinic, service_name: str | None) -> int | None:
    if not service_name:
        return None
    for service in clinic.services:
        if service.name.strip().lower() == service_name.strip().lower():
            return service.duration_minutes
    return None


def dispatch(clinic, wa_id: str, tool_name: str, tool_input: dict) -> dict:
    """Executa a ferramenta pedida pelo modelo e retorna um dict serializavel."""
    if tool_name == "check_availability":
        duration = _service_duration(clinic, tool_input.get("service_name"))
        slots = calendar.check_availability(clinic, tool_input["date"], duration)
        return {"date": tool_input["date"], "available_times": slots}

    if tool_name == "book_appointment":
        duration = _service_duration(clinic, tool_input.get("service_name"))
        result = calendar.create_appointment(
            clinic,
            date_str=tool_input["date"],
            time_str=tool_input["time"],
            patient_name=tool_input["patient_name"],
            service_name=tool_input["service_name"],
            wa_id=wa_id,
            duration_minutes=duration,
            notes=tool_input.get("notes", ""),
        )
        return {"status": "confirmed", **result}

    if tool_name == "cancel_appointment":
        calendar.cancel_appointment(clinic, tool_input["event_id"])
        return {"status": "cancelled", "event_id": tool_input["event_id"]}

    if tool_name == "list_my_appointments":
        appointments = calendar.list_appointments_by_wa_id(clinic, wa_id)
        return {"appointments": appointments}

    raise ValueError(f"Ferramenta desconhecida: {tool_name}")
