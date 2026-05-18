# Pipeline de Extração de Dados - OracleElixir

## Visão Geral
Este projeto extrai estatísticas de jogadores e times de League of Legends do site OracleElixir e as armazena em um banco de dados PostgreSQL. A execução é configurada para rodar diariamente via Cron Job, atualizando os dados existentes sem duplicá-los.

## Estrutura de Arquivos
- `extractor.py`: Script principal em Python que realiza o scraping e a inserção no banco.
- `requirements.txt`: Dependências do projeto.
- `run_extractor.sh`: Script shell wrapper para facilitar a execução.
- `.env.example`: Modelo para configuração das variáveis de ambiente.

## Pré-requisitos
1. Python 3.8+
2. Banco de dados PostgreSQL instalado e rodando.
3. Acesso à internet para o scraping.

## Instalação

1. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure o Banco de Dados:**
   Crie um arquivo `.env` na pasta `backend` baseado no `.env.example`:
   ```bash
   cp .env.example .env
   ```
   Edite o arquivo `.env` com suas credenciais reais do PostgreSQL.

3. **Crie o Banco de Dados e Tabelas:**
   Conecte-se ao seu PostgreSQL e crie o banco:
   ```sql
   CREATE DATABASE lol_stats;
   ```
   *Nota: O script criará as tabelas automaticamente na primeira execução se elas não existirem.*

## Execução Manual
Para testar a extração manualmente:
```bash
./run_extractor.sh
```
Ou diretamente com Python (certifique-se de carregar as variáveis de ambiente):
```bash
python extractor.py
```

## Agendamento Diário (Cron Job)

Para agendar a execução diária (ex: todo dia às 08:00 da manhã):

1. Abra o crontab do usuário:
   ```bash
   crontab -e
   ```

2. Adicione a seguinte linha:
   ```bash
   0 8 * * * cd /workspace/backend && ./run_extractor.sh >> /var/log/lol_extractor.log 2>&1
   ```

   *Explicação:*
   - `0 8 * * *`: Roda às 08:00 todos os dias.
   - `cd ... && ./run_extractor.sh`: Muda para o diretório e executa o script.
   - `>> ...`: Salva os logs de saída e erro em um arquivo para auditoria.

## Lógica de Atualização (Upsert)
O script utiliza uma estratégia de "Delete + Insert" para garantir dados atualizados:
1. Antes de inserir os novos dados extraídos de uma competição específica (ex: CBLOL Split 1), ele remove todos os registros existentes no banco que pertençam àquela mesma competição (`league` + `split`).
2. Em seguida, insere os dados frescos.
Isso garante que, se um jogador mudar de time ou as estatísticas forem retificadas no site, o banco reflita a versão mais recente sem criar duplicatas.

## Colunas Extraídas

**Players:**
- `player_name`, `team_name`, `role`, `games_played`, `kda`, `gd10`, `cspm`, `dpm`
- Metadados: `league`, `split`

**Teams:**
- `team_name`, `games_played`, `wins`, `losses`
- Metadados: `league`, `split`
