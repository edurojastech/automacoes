# WhatsApp AI Agent — Atendimento + Agendamento (Google Calendar)

Automação genérica que recebe mensagens do WhatsApp, responde com um agente
de IA (Claude) configurado por **prompt** e **base de conhecimento** próprios
de cada negócio, e agenda/cancela/consulta compromissos direto no **Google
Calendar**.

O exemplo incluso é de uma clínica odontológica (`clinics/clinica_odonto_exemplo`),
mas a estrutura é multi-tenant: para atender outra clínica (ou qualquer outro
negócio baseado em agendamento — barbearia, salão, consultório, pet shop
etc.) basta **copiar a pasta de exemplo** e editar os arquivos de
configuração, sem tocar no código.

## Como funciona

```
WhatsApp (paciente) ──► Webhook (FastAPI) ──► Agente (Claude + tools) ──► Google Calendar
                              │                        │
                              └────── histórico (SQLite) ┘
```

1. O paciente manda uma mensagem no WhatsApp da clínica.
2. A Meta (WhatsApp Cloud API) chama o webhook `POST /webhook/whatsapp`.
3. O `phone_number_id` do webhook identifica **qual clínica** deve atender
   (ver `clinics/*/config.yaml`), permitindo várias clínicas na mesma
   automação.
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
│   ├── whatsapp_client.py      # envio de mensagens + validação do webhook
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

### 3. WhatsApp Cloud API (Meta)

1. Crie um app em https://developers.facebook.com/apps com o produto
   **WhatsApp**.
2. Em "API Setup", pegue o **token temporário** (ou gere um permanente via
   System User) e o **Phone number ID** do número de teste/produção.
3. Preencha no `.env`:
   ```
   WHATSAPP_TOKEN=...
   WHATSAPP_APP_SECRET=...   # em App Settings > Basic
   WHATSAPP_VERIFY_TOKEN=escolha-uma-string-secreta
   ```
4. Rode o servidor localmente e exponha com um túnel (ex: `ngrok http 8000`).
5. Em "WhatsApp > Configuration", configure o webhook:
   - **Callback URL**: `https://SEU_TUNEL/webhook/whatsapp`
   - **Verify token**: o mesmo valor de `WHATSAPP_VERIFY_TOKEN`
   - Assine o campo `messages`.
6. Copie o **Phone number ID** para `whatsapp_phone_number_id` no
   `clinics/<sua_clinica>/config.yaml` — é isso que roteia a mensagem para a
   clínica certa.

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
   - `whatsapp_phone_number_id` (o número de WhatsApp dessa clínica);
   - `google_calendar_id` (o calendário do Google dessa clínica);
   - `business_hours`, `appointment_duration_minutes`, `services`;
   - `agent.persona_name` e `agent.system_prompt` (tom de voz e regras).
3. Reescreva `knowledge_base.md` com as informações reais do negócio
   (endereço, preços, políticas, FAQ etc.).
4. Reinicie o servidor (ou chame `clinics.loader.reload_clinics()` se
   estiver rodando em modo interativo).

Não é necessário alterar nenhum código-fonte — cada clínica é isolada pela
sua própria pasta de configuração, e o webhook já roteia automaticamente
pelo `phone_number_id` de cada uma.

## Limitações conhecidas / próximos passos

- Suporta apenas mensagens de **texto** e respostas de botões/listas
  simples; áudio e imagem ainda não são transcritos/analisados.
- Não há fila/retry robusto para falhas de envio no WhatsApp — falhas são
  apenas logadas. Para produção, considere uma fila (ex: Redis + worker).
- O histórico de conversa é local (SQLite); para múltiplas instâncias do
  servidor, migre para um banco compartilhado (Postgres, por exemplo).
- A base de conhecimento é injetada inteira no prompt (funciona bem até
  alguns milhares de palavras). Para bases muito grandes, migre para busca
  vetorial (RAG) antes de injetar no prompt.
