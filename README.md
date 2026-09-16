# Automações

Esta pasta reúne automações criadas para simplificar e otimizar meu dia a dia.

O objetivo é automatizar processos repetitivos, reduzir tarefas manuais e tornar
as atividades mais rápidas, organizadas e eficientes. Cada automação nasce de
uma necessidade prática e pode ser aprimorada conforme novas necessidades
aparecem.

## Objetivos

- Eliminar tarefas repetitivas;
- Economizar tempo nas atividades do dia a dia;
- Reduzir erros causados por processos manuais;
- Organizar soluções simples para problemas recorrentes.

## Primeira automação: `organizar.py`

O `organizar.py` foi a primeira automação criada nesta pasta. Ele ajuda a
organizar arquivos encontrados em um diretório específico ou no computador
inteiro.

### Funcionalidades

- Buscar arquivos por nome, prefixo, nome exato ou extensão;
- Usar um ou vários termos de busca;
- Pesquisar em um diretório escolhido ou em todas as unidades do computador;
- Exibir os arquivos encontrados antes de qualquer alteração;
- Criar uma pasta de destino no mesmo local de cada arquivo;
- Mover os arquivos somente após confirmação;
- Evitar sobrescrever arquivos existentes, adicionando um número ao nome
  quando necessário.

### Como executar

No terminal, a partir desta pasta, execute:

```bash
python organizar.py
```

Depois, informe os termos de busca, o tipo de pesquisa, o local onde procurar
e o nome da pasta de destino. A movimentação dos arquivos só será realizada
após a confirmação.

Os próximos scripts e ferramentas também serão desenvolvidos para uso pessoal
e poderão ser adaptados conforme novos processos precisarem ser otimizados.

## Segunda automação: `whatsapp_ai_agent/`

Automação de atendimento via WhatsApp com um agente de IA (Claude). O
agente responde de acordo com um **prompt** e uma **base de conhecimento**
próprios de cada negócio, e agenda/cancela/consulta compromissos
diretamente no **Google Calendar**.

O exemplo incluso é de uma clínica odontológica, mas a estrutura é
multi-tenant e reutilizável: basta copiar a pasta de uma clínica de exemplo
e editar a configuração (prompt, base de conhecimento, horários, número de
WhatsApp e calendário) para atender outro negócio, sem alterar código.

Veja `whatsapp_ai_agent/README.md` para o passo a passo completo de
configuração (Evolution API, Google Calendar e Claude).