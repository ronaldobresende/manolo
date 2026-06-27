"""Conexão e helpers do banco de dados PostgreSQL."""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Configuração básica de log
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Se estiver rodando dentro do Docker, o host do banco de dados não é 'localhost',
# mas sim o nome do serviço do docker-compose, que é 'db'.
if DATABASE_URL and "localhost" in DATABASE_URL and os.path.exists('/.dockerenv'):
    logger.info("Ambiente Docker detectado. Alterando host do banco de 'localhost' para 'db'.")
    DATABASE_URL = DATABASE_URL.replace("localhost", "db")

def get_connection():
    """
    Retorna uma conexão ativa com o banco de dados.
    Utiliza RealDictCursor para que os resultados sejam dicionários.
    """
    if not DATABASE_URL:
        raise ValueError("A variável de ambiente DATABASE_URL não está configurada.")
    
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    """
    Inicializa o banco de dados criando a extensão pgvector e todas as tabelas,
    respeitando a ordem das chaves estrangeiras.
    """
    commands = [
        # Extensão pgvector (deve ser criada antes das tabelas)
        "CREATE EXTENSION IF NOT EXISTS vector;",
        
        # ==========================================
        # 4.1 Núcleo — Identidade e Acesso
        # ==========================================
        """
        CREATE TABLE IF NOT EXISTS accounts (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          nome TEXT NOT NULL,
          tipo TEXT CHECK (tipo IN ('família', 'clínica', 'terapeuta_independente')),
          criado_em TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS usuarios (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID REFERENCES accounts(id),
          nome TEXT NOT NULL,
          telefone_whatsapp TEXT UNIQUE NOT NULL,
          email TEXT,
          perfil TEXT CHECK (perfil IN ('admin', 'família', 'terapeuta')),
          ativo BOOLEAN DEFAULT TRUE,
          criado_em TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS criancas (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID REFERENCES accounts(id),
          nome TEXT NOT NULL,
          data_nascimento DATE NOT NULL,
          diagnosticos JSONB DEFAULT '[]',
          criado_em TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS criancas_terapeutas (
          crianca_id UUID REFERENCES criancas(id),
          usuario_id UUID REFERENCES usuarios(id),
          especialidade TEXT NOT NULL,
          ativo BOOLEAN DEFAULT TRUE,
          desde DATE DEFAULT CURRENT_DATE,
          PRIMARY KEY (crianca_id, usuario_id)
        );
        """,
        
        # ==========================================
        # 4.2 Histórico Clínico — Documentos
        # ==========================================
        """
        CREATE TABLE IF NOT EXISTS documentos (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          crianca_id UUID REFERENCES criancas(id),
          usuario_id UUID REFERENCES usuarios(id),
          tipo TEXT CHECK (tipo IN ('laudo', 'relatorio_sessao', 'avaliacao', 'receita', 'outro')),
          especialidade TEXT,
          titulo TEXT NOT NULL,
          data_documento DATE,
          storage_path TEXT NOT NULL,
          processado BOOLEAN DEFAULT FALSE,
          criado_em TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS documento_chunks (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          documento_id UUID REFERENCES documentos(id),
          crianca_id UUID REFERENCES criancas(id),
          conteudo TEXT NOT NULL,
          embedding VECTOR(1536),
          metadata JSONB DEFAULT '{}',
          criado_em TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_doc_chunks_embedding ON documento_chunks USING ivfflat (embedding vector_cosine_ops);",
        "CREATE INDEX IF NOT EXISTS idx_doc_chunks_crianca_id ON documento_chunks (crianca_id);",
        
        # ==========================================
        # 4.3 Avaliações Estruturadas
        # ==========================================
        """
        CREATE TABLE IF NOT EXISTS avaliacoes (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          crianca_id UUID REFERENCES criancas(id),
          tipo TEXT NOT NULL,
          data_avaliacao DATE NOT NULL,
          profissional TEXT,
          documento_id UUID REFERENCES documentos(id),
          criado_em TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS avaliacoes_dominios (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          avaliacao_id UUID REFERENCES avaliacoes(id),
          dominio TEXT CHECK (dominio IN (
            'cognitivo', 'motor_fino', 'motor_grosso',
            'linguagem_receptiva', 'linguagem_expressiva', 'socio_emocional'
          )),
          pontuacao_bruta NUMERIC,
          pontuacao_composta NUMERIC,
          idade_equivalente_meses INTEGER,
          classificacao TEXT CHECK (classificacao IN (
            'muito_abaixo', 'abaixo', 'medio', 'acima', 'muito_acima'
          ))
        );
        """,

        # ==========================================
        # 4.4 Checklist Diário
        # ==========================================
        """
        CREATE TABLE IF NOT EXISTS checklists (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          crianca_id UUID REFERENCES criancas(id),
          usuario_id UUID REFERENCES usuarios(id),
          data DATE NOT NULL,
          resumo_dia TEXT CHECK (resumo_dia IN ('muito_bom', 'bom', 'regular', 'difícil')),
          origem TEXT CHECK (origem IN (
            'whatsapp_audio', 'whatsapp_video', 'whatsapp_texto', 'web', 'terminal'
          )),
          criado_em TIMESTAMPTZ DEFAULT NOW(),
          UNIQUE (crianca_id, data)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS checklist_sono (
          checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
          dormiu_as TIME,
          acordou_as TIME,
          acordou_noite BOOLEAN,
          cochilo BOOLEAN,
          notas TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS checklist_tela (
          checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
          usou_tela BOOLEAN,
          tempo_minutos INTEGER,
          conteudo TEXT,
          reacao_retirada TEXT CHECK (reacao_retirada IN ('tranquilo', 'resistencia', 'crise'))
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS checklist_alimentacao (
          checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
          comeu_bem BOOLEAN,
          aceitou TEXT[],
          recusou TEXT[],
          comeu_sentado BOOLEAN,
          utensilio TEXT CHECK (utensilio IN ('colher', 'garfo', 'mao', 'misto'))
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS checklist_comunicacao (
          checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
          usou_gestos BOOLEAN,
          palavras_ditas TEXT[],
          apontou BOOLEAN,
          puxou_mao TEXT CHECK (puxou_mao IN ('nunca', 'às_vezes', 'maioria', 'sempre')),
          respondeu_nome TEXT CHECK (respondeu_nome IN ('nunca', 'às_vezes', 'sempre')),
          imitou BOOLEAN
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS checklist_brincar (
          checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
          com_que_brincou TEXT[],
          modo TEXT CHECK (modo IN ('sozinho', 'com_adulto', 'misto')),
          fez_faz_de_conta BOOLEAN,
          tempo_sem_tela_minutos INTEGER
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS checklist_higiene (
          checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
          banho TEXT CHECK (banho IN ('tranquilo', 'resistencia', 'crise')),
          escovou_dentes BOOLEAN,
          sinalizou_banheiro BOOLEAN
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS checklist_vestuario (
          checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
          colaborou_roupa BOOLEAN,
          incomodo_sensorial BOOLEAN
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS checklist_movimento (
          checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
          atividades TEXT[],
          caiu_muito BOOLEAN,
          buscou_colo BOOLEAN
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS checklist_humor (
          checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
          humor_geral TEXT CHECK (humor_geral IN ('muito_bom', 'bom', 'regular', 'agitado', 'difícil')),
          teve_crise BOOLEAN,
          o_que_acalmou TEXT,
          notas TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS checklist_rotina (
          checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
          guardou_brinquedos BOOLEAN,
          ajudou_tarefa BOOLEAN,
          aceitou_transicao BOOLEAN
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS checklist_observacoes (
          checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
          conquistas TEXT,
          dificuldades TEXT,
          diferente_hoje TEXT
        );
        """,

        # ==========================================
        # 4.5 Mídia / 4.6 Atividades / 4.7 Perfil
        # ==========================================
        """
        CREATE TABLE IF NOT EXISTS midias (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          crianca_id UUID REFERENCES criancas(id),
          usuario_id UUID REFERENCES usuarios(id),
          tipo TEXT CHECK (tipo IN ('audio', 'video', 'foto')),
          contexto TEXT CHECK (contexto IN ('checklist', 'registro_livre', 'sessao')),
          checklist_id UUID REFERENCES checklists(id),
          storage_path TEXT NOT NULL,
          duracao_segundos INTEGER,
          transcricao TEXT,
          analise_agente TEXT,
          processado BOOLEAN DEFAULT FALSE,
          criado_em TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS atividades (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID REFERENCES accounts(id),
          criada_por UUID REFERENCES usuarios(id),
          titulo TEXT NOT NULL,
          descricao TEXT NOT NULL,
          tipo TEXT CHECK (tipo IN (
            'brincadeira', 'alimentacao', 'comunicacao',
            'motor', 'higiene', 'rotina'
          )),
          objetivo TEXT,
          materiais TEXT[],
          duracao_minutos INTEGER,
          criado_em TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS atividades_criancas (
          atividade_id UUID REFERENCES atividades(id),
          crianca_id UUID REFERENCES criancas(id),
          recomendada_por UUID REFERENCES usuarios(id),
          data_recomendacao DATE DEFAULT CURRENT_DATE,
          status TEXT CHECK (status IN ('pendente', 'em_andamento', 'concluida')),
          feedback TEXT,
          PRIMARY KEY (atividade_id, crianca_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS perfil_crianca (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          crianca_id UUID UNIQUE REFERENCES criancas(id),
          atualizado_em TIMESTAMPTZ DEFAULT NOW(),
          comunicacao JSONB DEFAULT '{}',
          motor JSONB DEFAULT '{}',
          alimentacao JSONB DEFAULT '{}',
          sono JSONB DEFAULT '{}',
          regulacao JSONB DEFAULT '{}',
          resumo_geral TEXT
        );
        """
    ]

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                for command in commands:
                    cur.execute(command)
            conn.commit()
            logger.info("Banco de dados, extensão pgvector e tabelas inicializados com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")


if __name__ == "__main__":
    init_db()