"""Carrega a configuracao de cada clinica (multi-tenant).

Cada clinica vive em uma subpasta de `clinics/`, com um `config.yaml` e uma
base de conhecimento em Markdown. Isso permite reaproveitar toda a automacao
para clinicas diferentes: basta copiar uma pasta de exemplo, editar o prompt,
a base de conhecimento e os dados de integracao (WhatsApp/Google Calendar).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from config import CLINICS_DIR


@dataclass
class Service:
    name: str
    duration_minutes: int
    description: str = ""


@dataclass
class Clinic:
    clinic_id: str
    name: str
    timezone: str
    evolution_instance: str
    google_calendar_id: str
    business_hours: dict
    appointment_duration_minutes: int
    persona_name: str
    system_prompt: str
    knowledge_base: str
    services: list[Service] = field(default_factory=list)

    def build_system_prompt(self) -> str:
        """Monta o prompt final: persona + regras + servicos + base de conhecimento."""
        services_txt = "\n".join(
            f"- {s.name} ({s.duration_minutes} min): {s.description}".strip()
            for s in self.services
        ) or "Nenhum servico cadastrado."

        horarios_txt = "\n".join(
            f"- {dia}: {intervalos}" for dia, intervalos in self.business_hours.items()
        )

        return f"""{self.system_prompt.strip()}

## Servicos oferecidos
{services_txt}

## Horario de funcionamento ({self.timezone})
{horarios_txt}

Duracao padrao de consulta, caso o servico nao tenha duracao propria: \
{self.appointment_duration_minutes} minutos.

## Base de conhecimento da clinica
{self.knowledge_base.strip()}

## Regras de agendamento
- Sempre confirme data, horario, nome do paciente e servico antes de usar a \
ferramenta de criar agendamento.
- Use a ferramenta `check_availability` antes de oferecer horarios ao paciente.
- Nunca invente horarios livres: baseie-se sempre no resultado das ferramentas.
- Se o paciente pedir algo fora do escopo da clinica (ex: emergencia medica \
grave), oriente a procurar atendimento presencial ou ligar para a clinica.
- Seja objetivo, cordial e use o nome {self.persona_name} ao se apresentar.
"""


def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _load_clinic_dir(clinic_dir: Path) -> Clinic:
    cfg = _load_yaml(clinic_dir / "config.yaml")

    kb_file = clinic_dir / cfg["agent"]["knowledge_base_file"]
    knowledge_base = kb_file.read_text(encoding="utf-8") if kb_file.exists() else ""

    services = [
        Service(
            name=s["name"],
            duration_minutes=s.get("duration_minutes", cfg.get("appointment_duration_minutes", 30)),
            description=s.get("description", ""),
        )
        for s in cfg["agent"].get("services", [])
    ]

    return Clinic(
        clinic_id=cfg["clinic_id"],
        name=cfg["name"],
        timezone=cfg.get("timezone", "America/Sao_Paulo"),
        evolution_instance=str(cfg["evolution_instance"]),
        google_calendar_id=cfg["google_calendar_id"],
        business_hours=cfg.get("business_hours", {}),
        appointment_duration_minutes=cfg.get("appointment_duration_minutes", 30),
        persona_name=cfg["agent"].get("persona_name", "Assistente Virtual"),
        system_prompt=cfg["agent"]["system_prompt"],
        knowledge_base=knowledge_base,
        services=services,
    )


@lru_cache(maxsize=1)
def _load_all() -> dict[str, Clinic]:
    clinics: dict[str, Clinic] = {}
    for clinic_dir in CLINICS_DIR.iterdir():
        if not clinic_dir.is_dir():
            continue
        config_file = clinic_dir / "config.yaml"
        if not config_file.exists():
            continue
        clinic = _load_clinic_dir(clinic_dir)
        clinics[clinic.evolution_instance] = clinic
    return clinics


def get_clinic_by_evolution_instance(instance_name: str) -> Clinic | None:
    """Retorna a clinica dona da instance da Evolution API que recebeu a mensagem."""
    return _load_all().get(str(instance_name))


def reload_clinics() -> None:
    """Limpa o cache (util apos editar configs sem reiniciar o servidor)."""
    _load_all.cache_clear()
