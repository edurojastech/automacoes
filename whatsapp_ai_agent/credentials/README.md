Coloque aqui o arquivo JSON da Service Account do Google (ex:
`service_account.json`), baixado no Google Cloud Console. Esse arquivo é
sensível e não deve ser commitado — o `.gitignore` do projeto já ignora
`*.json` nesta pasta.

Passos:
1. No Google Cloud Console, crie um projeto (ou use um existente) e ative a
   "Google Calendar API".
2. Crie uma Service Account e gere uma chave JSON.
3. Salve o JSON como `credentials/service_account.json`.
4. No Google Calendar, compartilhe o calendário de cada clínica com o
   e-mail da service account (campo `client_email` no JSON), com permissão
   "Fazer alterações em eventos".
