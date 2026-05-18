import os
import cloudscraper
import pandas as pd
from io import StringIO
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Configuração do Scraper
scraper = cloudscraper.create_scraper()

# URLs de Players
PLAYER_URLS = [
    {"url": "https://oracleselixir.com/stats/players/byTournament/LCS%2F2026%20Season%2FSpring%20Season", "league": "LCS", "split": "Spring"},
    {"url": "https://oracleselixir.com/stats/players/byTournament/LCK%2F2026%20Season%2FRounds%201-2", "league": "LCK", "split": "Rounds 1-2"},
    {"url": "https://oracleselixir.com/stats/players/byTournament/LEC%2F2026%20Season%2FSpring%20Season", "league": "LEC", "split": "Spring"},
    {"url": "https://oracleselixir.com/stats/players/byTournament/LPL%2F2026%20Season%2FSplit%202", "league": "LPL", "split": "Split 2"},
    {"url": "https://oracleselixir.com/stats/players/byTournament/CBLOL%2F2026%20Season%2FSplit%201", "league": "CBLOL", "split": "Split 1"},
    {"url": "https://oracleselixir.com/stats/players/byTournament/CBLOL%2F2026%20Season%2FSplit%201%20Playoffs", "league": "CBLOL", "split": "Playoffs"}
]

# URLs de Times
TEAM_URLS = [
    {"url": "https://oracleselixir.com/stats/teams/byTournament/LCS%2F2026%20Season%2FSpring%20Season", "league": "LCS", "split": "Spring"},
    {"url": "https://oracleselixir.com/stats/teams/byTournament/LCK%2F2026%20Season%2FRounds%201-2", "league": "LCK", "split": "Rounds 1-2"},
    {"url": "https://oracleselixir.com/stats/teams/byTournament/LEC%2F2026%20Season%2FSpring%20Season", "league": "LEC", "split": "Spring"},
    {"url": "https://oracleselixir.com/stats/teams/byTournament/LPL%2F2026%20Season%2FSplit%202", "league": "LPL", "split": "Split 2"},
    {"url": "https://oracleselixir.com/stats/teams/byTournament/CBLOL%2F2026%20Season%2FSplit%201", "league": "CBLOL", "split": "Split 1"},
    {"url": "https://oracleselixir.com/stats/teams/byTournament/CBLOL%2F2026%20Season%2FSplit%201%20Playoffs", "league": "CBLOL", "split": "Playoffs"}
]

# Mapeamento de colunas (Nome no Site -> Nome no Banco)
PLAYER_COLS_MAP = {
    "player": "player_name",
    "team": "team_name",
    "position": "role",
    "games played": "games_played",
    "kda": "kda",
    "average gold difference at 10 minutes": "gd10",
    "cspm": "cspm",
    "dpm": "dpm"
}

TEAM_COLS_MAP = {
    "team": "team_name",
    "g": "games_played",
    "w": "wins",
    "l": "losses"
}

def get_db_connection():
    """Retorna a engine do SQLAlchemy baseada em variáveis de ambiente."""
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME", "lol_stats")
    
    return create_engine(f"postgresql://{user}:{password}@{host}:{port}/{database}")

def fetch_and_clean_table(url_info, cols_map, type_name):
    """Busca a tabela, limpa e renomeia colunas."""
    try:
        print(f"Buscando {type_name}: {url_info['url']}")
        response = scraper.get(url_info['url'])
        response.raise_for_status()
        
        tables = pd.read_html(StringIO(response.text))
        if not tables:
            print(f"Nenhuma tabela encontrada em {url_info['url']}")
            return None
        
        df = tables[0]
        
        # Normalizar nomes das colunas para lower case para facilitar matching
        df.columns = df.columns.str.lower().str.strip()
        
        # Verificar quais colunas desejadas existem no dataframe
        available_cols = []
        for site_col, db_col in cols_map.items():
            if site_col.lower() in df.columns:
                available_cols.append(site_col.lower())
            else:
                # Tentativa de match parcial ou variação comum
                # Ex: 'games played' pode vir como 'games' ou 'gp' dependendo da tabela
                if site_col == "games played" and "g" in df.columns:
                    available_cols.append("g") 
                elif site_col == "average gold difference at 10 minutes" and "gd@10" in df.columns:
                    available_cols.append("gd@10")
        
        if not available_cols:
            print(f"Nenhuma coluna relevante encontrada em {url_info['url']}. Colunas disponíveis: {list(df.columns)}")
            return None

        # Selecionar apenas colunas relevantes + adicionar metadados
        select_cols = available_cols.copy()
        df = df[select_cols].copy()
        
        # Renomear para o padrão do banco
        rename_dict = {}
        for site_col, db_col in cols_map.items():
            if site_col.lower() in df.columns:
                rename_dict[site_col.lower()] = db_col
            elif site_col == "games played" and "g" in df.columns:
                rename_dict["g"] = db_col
            elif site_col == "average gold difference at 10 minutes" and "gd@10" in df.columns:
                rename_dict["gd@10"] = db_col
                
        df = df.rename(columns=rename_dict)
        
        # Adicionar metadados de liga e split
        df['league'] = url_info['league']
        df['split'] = url_info['split']
        
        return df

    except Exception as e:
        print(f"Erro ao processar {url_info['url']}: {e}")
        return None

def upsert_data(engine, df, table_name, unique_columns):
    """Realiza o UPSERT (Insert or Update) no PostgreSQL."""
    if df is None or df.empty:
        print(f"Nenhum dado para salvar na tabela {table_name}.")
        return

    try:
        with engine.connect() as conn:
            # Garantir que a tabela existe (criação simples baseada no DF)
            # Em produção, use migrations (Alembic)
            df.to_sql(table_name, conn, if_exists='append', index=False, method='multi')
            
            # Nota: O pandas to_sql com 'append' pode duplicar se rodar várias vezes no mesmo dia
            # Para um UPSERT real (atualizar se existir), precisamos de lógica SQL específica.
            # Abaixo uma abordagem simplificada: deletar registros antigos do mesmo league/split antes de inserir
            # Isso garante que os dados mais recentes substituam os antigos daquela competição específica.
            
            # Construir cláusula WHERE para deletar antigos
            leagues = tuple(df['league'].unique())
            splits = tuple(df['split'].unique())
            
            # Se tiver múltiplos splits/leagues no mesmo batch, a deleção precisa ser cuidadosa.
            # Vamos fazer linha por linha ou agrupar. Para simplificar, vamos usar a abordagem de 
            # criar uma tabela temporária e fazer merge, OU simplesmente confiar que a extração diária
            # substitui o snapshot da competição.
            
            # Abordagem escolhida: Deletar entradas existentes para este League+Split antes de inserir o novo batch
            # Isso assume que a extração diária traz o estado atual completo daquela liga.
            
            # Criar string de condições para DELETE
            # Precisamos agrupar por league e split para otimizar
            conditions = []
            for l in df['league'].unique():
                for s in df[df['league']==l]['split'].unique():
                    conditions.append(f"(league = '{l}' AND split = '{s}')")
            
            if conditions:
                where_clause = " OR ".join(conditions)
                delete_query = f"DELETE FROM {table_name} WHERE {where_clause}"
                conn.execute(text(delete_query))
                conn.commit()
                print(f"Registros antigos de {table_name} para as competições extraídas removidos.")

            # Reinserir dados atualizados
            df.to_sql(table_name, conn, if_exists='append', index=False, method='multi')
            conn.commit()
            print(f"{len(df)} registros salvos/atualizados em {table_name}.")

    except SQLAlchemyError as e:
        print(f"Erro de banco de dados: {e}")
    except Exception as e:
        print(f"Erro geral ao salvar: {e}")

def main():
    print("Iniciando pipeline de extração...")
    
    # Conexão DB
    try:
        engine = get_db_connection()
        # Teste de conexão
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Conexão com PostgreSQL estabelecida.")
    except Exception as e:
        print(f"Falha na conexão com o banco de dados: {e}")
        print("Certifique-se de que as variáveis de ambiente DB_USER, DB_PASSWORD, etc., estão configuradas.")
        return

    # Extração de Players
    all_players = []
    for info in PLAYER_URLS:
        df = fetch_and_clean_table(info, PLAYER_COLS_MAP, "Player")
        if df is not None:
            all_players.append(df)
    
    if all_players:
        df_players_final = pd.concat(all_players, ignore_index=True)
        # Definir chaves únicas para lógica de atualização: player_name, team_name, league, split
        upsert_data(engine, df_players_final, 'players', ['player_name', 'team_name', 'league', 'split'])
    else:
        print("Nenhum dado de players extraído.")

    # Extração de Teams
    all_teams = []
    for info in TEAM_URLS:
        df = fetch_and_clean_table(info, TEAM_COLS_MAP, "Team")
        if df is not None:
            all_teams.append(df)
    
    if all_teams:
        df_teams_final = pd.concat(all_teams, ignore_index=True)
        # Chave única: team_name, league, split
        upsert_data(engine, df_teams_final, 'teams', ['team_name', 'league', 'split'])
    else:
        print("Nenhum dado de times extraído.")

    print("Pipeline finalizada.")

if __name__ == "__main__":
    main()
