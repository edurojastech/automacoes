# WhatsApp AI Agent — Atendimento + Agendamento (Google Calendar)

Automação genérica que recebe mensagens do WhatsApp (via [Evolution
API](https://github.com/EvolutionAPI/evolution-api), um servidor
self-hosted e gratuito), responde com um agente de IA (Claude) configurado
por **prompt** e **base de conhecimento** próprios de cada negócio, e
agenda/cancela/consulta compromissos direto no **Google Calendar**.

O exemplo incluso é de uma clínica odontológica (`clinics/clinica_odonto_exemplo`),
mas a estrutura é multi-tenant: para atender outra clínica (ou qualquer outro
negócio baseado em agendamento — barbearia, salão, consultório, pet shop
etc.) basta **copiar a pasta de exemplo** e editar os arquivos de
configuração, sem tocar no código.

## Como funciona

```
WhatsApp (paciente) ──► Evolution API ──► Webhook (FastAPI) ──► Agente (Claude + tools) ──► Google Calendar
                                                 │                        │
                                                 └────── histórico (SQLite) ┘
```

1. O paciente manda uma mensagem no WhatsApp da clínica.
2. A Evolution API (conectada a esse número via QR Code) chama o webhook
   `POST /webhook/evolution/{instance}`.
3. O nome da `instance` (parte da própria URL do webhook) identifica **qual
   clínica** deve atender (ver `clinics/*/config.yaml`), permitindo várias
   clínicas na mesma automação — cada uma com sua própria instance/número.
4. O agente monta o prompt do sistema (persona + regras + serviços +
   horário de funcionamento + base de conhecimento da clínica) e conversa
   com o Claude, que tem acesso a 4 ferramentas:
   - `check_availability` — consulta horários livres no Google Calendar;
   - `book_appointment` — cria o agendamento;
   - `cancel_appointment` — cancela um agendamento existente;
   - `list_my_appointments` — lista os agendamentos futuros do paciente.
5. A resposta final em texto é enviada de volta pelo WhatsApp.
6. O histórico recente da conversa fica salvo em SQLite local, só para dar
   contexto de curto prazo ao agente (o Google Calendar continua sendo a
   fonte da verdade dos agendamentos).

## Estrutura de pastas

```
whatsapp_ai_agent/
├── main.py                     # servidor FastAPI + webhook do WhatsApp
├── config.py                   # variáveis de ambiente
├── agent/
│   ├── claude_agent.py         # loop de conversa com o Claude (tool use)
│   └── tools.py                # definição e execução das ferramentas
├── integrations/
│   ├── evolution_client.py     # envio de mensagens + parsing do webhook (Evolution API)
│   └── google_calendar_client.py
├── storage/
│   └── conversation_store.py   # histórico de conversa (SQLite)
├── clinics/
│   └── clinica_odonto_exemplo/
│       ├── config.yaml         # prompt, serviços, horários, IDs de integração
│       └── knowledge_base.md   # base de conhecimento (FAQ, preços, políticas...)
└── credentials/                # service_account.json (não versionado)
```

## Configuração passo a passo

### 1. Pré-requisitos

```bash
cd whatsapp_ai_agent
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Claude (Anthropic)

Gere uma chave em https://console.anthropic.com e preencha no `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-5
```

### 3. WhatsApp — Evolution API

A [Evolution API](https://github.com/EvolutionAPI/evolution-api) é um
servidor open-source que conecta ao WhatsApp via QR Code (como o WhatsApp
Web), sem precisar de aprovação da Meta nem número comercial verificado.
Você mesmo hospeda o servidor dela (Docker é o jeito mais simples).

1. Suba a Evolution API (exemplo rápido com Docker):
   ```bash
   docker run -d --name evolution-api -p 8080:8080 \
     -e AUTHENTICATION_API_KEY=escolha-uma-api-key-forte \
     atendai/evolution-api:latest
   ```
   Para produção, use o `docker-compose` oficial do projeto (com Postgres/
   Redis) — veja a documentação em https://doc.evolution-api.com.
2. Preencha no `.env`:
   ```
   EVOLUTION_API_URL=http://localhost:8080
   EVOLUTION_API_KEY=escolha-uma-api-key-forte   # a mesma do AUTHENTICATION_API_KEY
   EVOLUTION_WEBHOOK_SECRET=escolha-outra-string-secreta
   ```
3. Crie uma instance para a clínica (uma instance = um número de WhatsApp)
   e escaneie o QR Code para conectar:
   ```bash
   curl -X POST http://localhost:8080/instance/create \
     -H "apikey: escolha-uma-api-key-forte" \
     -H "Content-Type: application/json" \
     -d '{"instanceName": "clinica_sorriso_feliz", "qrcode": true}'
   ```
   O QR Code é retornado na resposta (ou pode ser visto no painel da
   Evolution API); escaneie com o WhatsApp que vai atender a clínica.
4. Configure o webhook dessa instance para apontar para a automação
   (rode o servidor localmente e exponha com um túnel, ex: `ngrok http 8000`):
   ```bash
   curl -X POST http://localhost:8080/webhook/set/clinica_sorriso_feliz \
     -H "apikey: escolha-uma-api-key-forte" \
     -H "Content-Type: application/json" \
     -d '{
       "webhook": {
         "url": "https://SEU_TUNEL/webhook/evolution/clinica_sorriso_feliz?secret=escolha-outra-string-secreta",
         "webhook_by_events": true,
         "events": ["MESSAGES_UPSERT"]
       }
     }'
   ```
5. Use o mesmo nome de instance (`clinica_sorriso_feliz` no exemplo) no
   campo `evolution_instance` do `clinics/<sua_clinica>/config.yaml` — é
   isso que roteia a mensagem para a clínica certa.

### 4. Google Calendar

1. No Google Cloud Console, crie/ative a **Google Calendar API**.
2. Crie uma **Service Account** e gere uma chave JSON.
3. Salve o arquivo em `credentials/service_account.json` (veja
   `credentials/README.md`).
4. No Google Calendar, compartilhe o calendário da clínica com o
   `client_email` da service account, com permissão de **fazer alterações
   em eventos**.
5. Coloque o ID do calendário (em "Configurações e compartilhamento" >
   "Integrar agenda" > "ID da agenda") em `google_calendar_id` no
   `config.yaml` da clínica.

### 5. Rodar

```bash
uvicorn main:app --reload --port 8000
```

Mande uma mensagem para o número de WhatsApp configurado e acompanhe os
logs no terminal.

## Adicionando uma nova clínica (ou outro negócio)

1. Copie `clinics/clinica_odonto_exemplo` para `clinics/minha_clinica`.
2. Edite `config.yaml`:
   - `clinic_id`, `name`, `timezone`;
   - `evolution_instance` (o nome da instance/número de WhatsApp dessa clínica);
   - `google_calendar_id` (o calendário do Google dessa clínica);
   - `business_hours`, `appointment_duration_minutes`, `services`;
   - `agent.persona_name` e `agent.system_prompt` (tom de voz e regras).
3. Reescreva `knowledge_base.md` com as informações reais do negócio
   (endereço, preços, políticas, FAQ etc.).
4. Reinicie o servidor (ou chame `clinics.loader.reload_clinics()` se
   estiver rodando em modo interativo).

Não é necessário alterar nenhum código-fonte — cada clínica é isolada pela
sua própria pasta de configuração, e o webhook já roteia automaticamente
pela `evolution_instance` de cada uma (basta criar uma instance nova na
Evolution API e apontar o webhook dela para
`/webhook/evolution/<nome_da_instance>`).

## Limitações conhecidas / próximos passos

- Suporta apenas mensagens de **texto** e respostas de botões/listas
  simples; áudio e imagem ainda não são transcritos/analisados.
- A Evolution API não assina o payload do webhook (diferente da Meta), então
  a proteção usada é um segredo na própria URL (`?secret=...`). Mantenha
  essa URL privada e, em produção, prefira HTTPS com um domínio próprio.
- Não há fila/retry robusto para falhas de envio no WhatsApp — falhas são
  apenas logadas. Para produção, considere uma fila (ex: Redis + worker).
- O histórico de conversa é local (SQLite); para múltiplas instâncias do
  servidor, migre para um banco compartilhado (Postgres, por exemplo).
- A base de conhecimento é injetada inteira no prompt (funciona bem até
  alguns milhares de palavras). Para bases muito grandes, migre para busca
  vetorial (RAG) antes de injetar no prompt.
