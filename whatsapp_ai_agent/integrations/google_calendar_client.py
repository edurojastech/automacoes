"""Integracao com Google Calendar: disponibilidade, criacao e cancelamento
de agendamentos.

Usa uma Service Account do Google. Cada calendario de clinica precisa ser
compartilhado com o e-mail dessa conta de servico (permissao "Fazer
alteracoes em eventos").
"""
from __future__ import annotations

import datetime as dt
from functools import lru_cache
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

import config

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Marca todo evento criado pela automacao, para depois localizar os
# agendamentos de um paciente (busca por wa_id) sem depender de banco externo.
_SOURCE_TAG = "whatsapp-ai-agent"

_DIA_SEMANA_PT = {
    0: "segunda",
    1: "terca",
    2: "quarta",
    3: "quinta",
    4: "sexta",
    5: "sabado",
    6: "domingo",
}


class AgendaError(Exception):
    """Erro de negocio (ex: horario fora do expediente) reportado ao agente."""


@lru_cache(maxsize=1)
def _service():
    credentials = service_account.Credentials.from_service_account_file(
        config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


def _parse_business_hours(hours_str: str) -> list[tuple[dt.time, dt.time]]:
    """Converte "08:00-12:00, 13:00-18:00" em [(time, time), ...]. "fechado" -> []."""
    hours_str = (hours_str or "").strip().lower()
    if not hours_str or hours_str == "fechado":
        return []

    intervalos = []
    for parte in hours_str.split(","):
        inicio_str, fim_str = [p.strip() for p in parte.split("-")]
        inicio = dt.datetime.strptime(inicio_str, "%H:%M").time()
        fim = dt.datetime.strptime(fim_str, "%H:%M").time()
        intervalos.append((inicio, fim))
    return intervalos


def _day_intervals(clinic, date: dt.date) -> list[tuple[dt.time, dt.time]]:
    dia_pt = _DIA_SEMANA_PT[date.weekday()]
    hours_str = clinic.business_hours.get(dia_pt, "fechado")
    return _parse_business_hours(hours_str)


def check_availability(clinic, date_str: str, duration_minutes: int | None = None) -> list[str]:
    """Retorna a lista de horarios livres (HH:MM) para a data informada.

    Considera o expediente do dia da semana e os eventos ja existentes no
    calendario da clinica (via freebusy).
    """
    tz = ZoneInfo(clinic.timezone)
    try:
        date = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise AgendaError(f"Data invalida: {date_str}. Use o formato AAAA-MM-DD.") from exc

    duration = duration_minutes or clinic.appointment_duration_minutes
    intervalos = _day_intervals(clinic, date)
    if not intervalos:
        return []

    day_start = dt.datetime.combine(date, dt.time.min, tzinfo=tz)
    day_end = dt.datetime.combine(date, dt.time.max, tzinfo=tz)

    freebusy = _service().freebusy().query(
        body={
            "timeMin": day_start.isoformat(),
            "timeMax": day_end.isoformat(),
            "timeZone": clinic.timezone,
            "items": [{"id": clinic.google_calendar_id}],
        }
    ).execute()

    busy_raw = freebusy["calendars"][clinic.google_calendar_id].get("busy", [])
    busy = [
        (dt.datetime.fromisoformat(b["start"]), dt.datetime.fromisoformat(b["end"]))
        for b in busy_raw
    ]

    slots: list[str] = []
    step = dt.timedelta(minutes=duration)
    now = dt.datetime.now(tz)

    for inicio_time, fim_time in intervalos:
        cursor = dt.datetime.combine(date, inicio_time, tzinfo=tz)
        intervalo_fim = dt.datetime.combine(date, fim_time, tzinfo=tz)

        while cursor + step <= intervalo_fim:
            slot_fim = cursor + step
            if cursor < now:
                cursor += step
                continue
            conflita = any(cursor < b_fim and slot_fim > b_ini for b_ini, b_fim in busy)
            if not conflita:
                slots.append(cursor.strftime("%H:%M"))
            cursor += step

    return slots


def create_appointment(
    clinic,
    date_str: str,
    time_str: str,
    patient_name: str,
    service_name: str,
    wa_id: str,
    duration_minutes: int | None = None,
    notes: str = "",
) -> dict:
    """Cria o evento no Google Calendar e retorna {event_id, start, end}."""
    tz = ZoneInfo(clinic.timezone)
    try:
        start = dt.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    except ValueError as exc:
        raise AgendaError("Data/horario invalidos. Use AAAA-MM-DD e HH:MM.") from exc

    duration = duration_minutes or clinic.appointment_duration_minutes
    end = start + dt.timedelta(minutes=duration)

    disponiveis = check_availability(clinic, date_str, duration)
    if time_str not in disponiveis:
        raise AgendaError(
            f"O horario {time_str} em {date_str} nao esta mais disponivel. "
            f"Verifique novamente com check_availability."
        )

    event = {
        "summary": f"{service_name} - {patient_name}",
        "description": (notes or f"Agendado via WhatsApp AI Agent para {patient_name}."),
        "start": {"dateTime": start.isoformat(), "timeZone": clinic.timezone},
        "end": {"dateTime": end.isoformat(), "timeZone": clinic.timezone},
        "extendedProperties": {
            "private": {
                "source": _SOURCE_TAG,
                "clinic_id": clinic.clinic_id,
                "wa_id": wa_id,
                "patient_name": patient_name,
                "service": service_name,
            }
        },
    }

    created = _service().events().insert(calendarId=clinic.google_calendar_id, body=event).execute()

    return {
        "event_id": created["id"],
        "start": start.isoformat(),
        "end": end.isoformat(),
    }


def cancel_appointment(clinic, event_id: str) -> None:
    try:
        _service().events().delete(calendarId=clinic.google_calendar_id, eventId=event_id).execute()
    except Exception as exc:  # noqa: BLE001 - repassa como erro de negocio pro agente
        raise AgendaError(f"Nao foi possivel cancelar o agendamento {event_id}: {exc}") from exc


def list_appointments_by_wa_id(clinic, wa_id: str) -> list[dict]:
    """Lista os proximos agendamentos futuros do paciente (identificado pelo wa_id)."""
    tz = ZoneInfo(clinic.timezone)
    now = dt.datetime.now(tz)

    result = _service().events().list(
        calendarId=clinic.google_calendar_id,
        timeMin=now.isoformat(),
        privateExtendedProperty=[f"wa_id={wa_id}", f"clinic_id={clinic.clinic_id}"],
        singleEvents=True,
        orderBy="startTime",
        maxResults=10,
    ).execute()

    agendamentos = []
    for item in result.get("items", []):
        agendamentos.append(
            {
                "event_id": item["id"],
                "summary": item.get("summary", ""),
                "start": item["start"].get("dateTime", item["start"].get("date")),
            }
        )
    return agendamentos
