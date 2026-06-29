"""Rotas REST para o Web App Manolo (Fase 4).

Todas as rotas /api/* são consumidas pelo frontend Next.js.
Sem autenticação no MVP (Fase 4) — débito técnico registrado em DEBITOS_TECNICOS.md.
A lógica de negócio permanece no backend; o frontend é apenas consumidor.
"""

import logging
import os
import tempfile
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Depends
from pydantic import BaseModel

from channels.schemas import ChecklistPayload

from core.database import get_connection, _query_one, _query_many, _execute, _execute_returning
from core.config import settings
from core.security import get_current_user, get_password_hash
from core.storage import upload_file_to_r2

logger = logging.getLogger(__name__)

# Aplicar proteção a todas as rotas deste router
api_router = APIRouter(prefix="/api", tags=["web"], dependencies=[Depends(get_current_user)])


# ============================================================
# HEALTH CHECK DA API WEB
# ============================================================

@api_router.get("/status")
async def api_status():
    """Verifica se a API web está no ar."""
    return {"status": "ok", "versao": "fase4"}


# ============================================================
# CRIANÇAS — SELETOR
# ============================================================

@api_router.get("/criancas")
async def listar_criancas():
    """Retorna dados simplificados das crianças disponíveis."""
    rows = _query_many("""
        SELECT id, nome, data_nascimento, foto_url
        FROM criancas
        ORDER BY nome
    """)
    # Retorna o perfil atual junto
    res = []
    for r in rows:
        d = dict(r)
        d["perfil_vivo"] = _query_one(
            "SELECT * FROM perfil_crianca WHERE crianca_id = %s",
            (r["id"],)
        )
        res.append(d)
    return res

@api_router.post("/criancas/{crianca_id}/foto")
async def upload_foto_crianca(crianca_id: str, file: UploadFile = File(...)):
    """Faz upload de uma nova foto de perfil para a criança usando o bucket R2."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo inválido")
    
    ext = file.filename.split(".")[-1]
    object_name = f"criancas/{crianca_id}/foto_perfil.{ext}"
    
    # Salvar em arquivo temporário para usar a função upload_file_to_r2
    fd, tmp_path = tempfile.mkstemp(suffix=f".{ext}")
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(await file.read())
        
        # Upload para o R2
        public_url = upload_file_to_r2(tmp_path, object_name)
        if not public_url:
            raise HTTPException(status_code=500, detail="Erro ao enviar foto para o R2.")
        
        # Salvar a URL no banco de dados
        _execute("""
            UPDATE criancas
            SET foto_url = %s
            WHERE id = %s
        """, (public_url, crianca_id))
        
        return {"foto_url": public_url}
    except Exception as e:
        logger.error(f"[API] Erro no upload de foto da criança: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao processar imagem: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ============================================================
# PERFIL VIVO
# ============================================================

@api_router.get("/perfil/{crianca_id}")
async def obter_perfil(crianca_id: str):
    """Retorna o perfil vivo completo da criança."""
    row = _query_one("""
        SELECT p.*, c.nome AS nome_crianca, c.data_nascimento
        FROM perfil_crianca p
        JOIN criancas c ON c.id = p.crianca_id
        WHERE p.crianca_id = %s
    """, (crianca_id,))

    if not row:
        raise HTTPException(status_code=404, detail="Perfil não encontrado para esta criança.")

    return dict(row)


# ============================================================
# CHECKLISTS
# ============================================================

@api_router.get("/checklists/{crianca_id}")
async def listar_checklists(
    crianca_id: str,
    inicio: Optional[str] = Query(None, description="Data início YYYY-MM-DD"),
    fim: Optional[str] = Query(None, description="Data fim YYYY-MM-DD"),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(30, ge=1, le=100),
):
    """Retorna lista paginada de checklists com resumo de cada seção."""
    offset = (pagina - 1) * por_pagina

    filtro_data = ""
    params: list = [crianca_id]

    if inicio:
        filtro_data += " AND ch.data >= %s"
        params.append(inicio)
    if fim:
        filtro_data += " AND ch.data <= %s"
        params.append(fim)

    params += [por_pagina, offset]

    rows = _query_many(f"""
        SELECT
            ch.id,
            ch.data,
            ch.resumo_dia,
            ch.origem,
            ch.criado_em,
            -- Sono
            cs.dormiu_as,
            cs.acordou_as,
            cs.acordou_noite,
            -- Tela
            ct.usou_tela,
            ct.tempo_minutos AS tempo_tela_minutos,
            -- Humor
            ch2.humor_geral,
            ch2.teve_crise,
            -- Comunicação
            cc.palavras_ditas,
            cc.usou_gestos,
            cc.respondeu_nome,
            -- Alimentação
            ca.comeu_bem,
            ca.utensilio,
            -- Brincar
            cb.tempo_sem_tela_minutos,
            cb.modo AS modo_brincar
        FROM checklists ch
        LEFT JOIN checklist_sono cs ON cs.checklist_id = ch.id
        LEFT JOIN checklist_tela ct ON ct.checklist_id = ch.id
        LEFT JOIN checklist_humor ch2 ON ch2.checklist_id = ch.id
        LEFT JOIN checklist_comunicacao cc ON cc.checklist_id = ch.id
        LEFT JOIN checklist_alimentacao ca ON ca.checklist_id = ch.id
        LEFT JOIN checklist_brincar cb ON cb.checklist_id = ch.id
        WHERE ch.crianca_id = %s
        {filtro_data}
        ORDER BY ch.data DESC
        LIMIT %s OFFSET %s
    """, tuple(params))

    # Total para paginação
    count_params = [crianca_id]
    count_filtro = ""
    if inicio:
        count_filtro += " AND data >= %s"
        count_params.append(inicio)
    if fim:
        count_filtro += " AND data <= %s"
        count_params.append(fim)

    count_row = _query_one(
        f"SELECT COUNT(*) as total FROM checklists WHERE crianca_id = %s {count_filtro}",
        tuple(count_params)
    )
    total = count_row["total"] if count_row else 0

    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "checklists": [dict(r) for r in rows],
    }


@api_router.get("/checklists/{crianca_id}/{data}")
async def obter_checklist_detalhado(crianca_id: str, data: str):
    """Retorna checklist completo de uma data específica (YYYY-MM-DD)."""
    checklist = _query_one("""
        SELECT id, data, resumo_dia, origem, criado_em
        FROM checklists
        WHERE crianca_id = %s AND data = %s
    """, (crianca_id, data))

    if not checklist:
        raise HTTPException(status_code=404, detail=f"Checklist não encontrado para {data}.")

    checklist_id = checklist["id"]

    # Buscar todas as seções
    secoes = {}
    tabelas = [
        ("sono", "checklist_sono"),
        ("tela", "checklist_tela"),
        ("alimentacao", "checklist_alimentacao"),
        ("comunicacao", "checklist_comunicacao"),
        ("brincar", "checklist_brincar"),
        ("higiene", "checklist_higiene"),
        ("vestuario", "checklist_vestuario"),
        ("movimento", "checklist_movimento"),
        ("humor", "checklist_humor"),
        ("rotina", "checklist_rotina"),
        ("observacoes", "checklist_observacoes"),
    ]
    for nome, tabela in tabelas:
        row = _query_one(f"SELECT * FROM {tabela} WHERE checklist_id = %s", (checklist_id,))
        secoes[nome] = dict(row) if row else None

    return {**dict(checklist), "secoes": secoes}


@api_router.post("/checklists/{crianca_id}")
async def criar_checklist(
    crianca_id: str, 
    payload: ChecklistPayload,
    user: dict = Depends(get_current_user)
):
    """Cria um checklist novo para a criança na data fornecida."""
    logger.info(f"[CHECKLIST] Criando checklist para {crianca_id}. Payload: {payload.model_dump()}")
    # Verificar se já existe (não deve duplicar)
    existente = _query_one(
        "SELECT id FROM checklists WHERE crianca_id = %s AND data = %s",
        (crianca_id, payload.data)
    )
    if existente:
        raise HTTPException(status_code=400, detail="Checklist para esta data já existe. Use PATCH para atualizar.")

    # Inserir checklist principal
    checklist_id = _execute_returning(
        """
        INSERT INTO checklists (crianca_id, usuario_id, data, resumo_dia, origem)
        VALUES (%s, %s, %s, %s, 'web')
        RETURNING id
        """,
        (crianca_id, user["id"], payload.data, payload.resumo_dia if payload.resumo_dia != "" else None)
    )["id"]

    # Função auxiliar para inserir seções se enviadas
    def inserir_secao(tabela: str, obj):
        if not obj: return
        raw_dados = obj.model_dump(exclude_unset=True)
        if not raw_dados: return
        
        dados = {}
        for k, v in raw_dados.items():
            if v is None: continue
            if isinstance(v, str) and v == "": v = None
            if isinstance(v, list) and len(v) == 0: v = None
            dados[k] = v
            
        if not dados: return
        
        colunas = ["checklist_id"] + list(dados.keys())
        valores = [checklist_id] + list(dados.values())
        
        placeholders = ", ".join(["%s"] * len(colunas))
        cols_str = ", ".join(colunas)
        
        _execute(f"INSERT INTO {tabela} ({cols_str}) VALUES ({placeholders})", tuple(valores))

    inserir_secao("checklist_sono", payload.sono)
    inserir_secao("checklist_tela", payload.tela)
    inserir_secao("checklist_alimentacao", payload.alimentacao)
    inserir_secao("checklist_comunicacao", payload.comunicacao)
    inserir_secao("checklist_brincar", payload.brincar)
    inserir_secao("checklist_higiene", payload.higiene)
    inserir_secao("checklist_vestuario", payload.vestuario)
    inserir_secao("checklist_movimento", payload.movimento)
    inserir_secao("checklist_humor", payload.humor)
    inserir_secao("checklist_rotina", payload.rotina)
    inserir_secao("checklist_observacoes", payload.observacoes)

    # Dispara a atualização do perfil em background (sem bloquear o response)
    from agent.profile import atualizar_perfil
    asyncio.create_task(asyncio.to_thread(atualizar_perfil, crianca_id))

    return {"status": "success", "id": checklist_id}


@api_router.patch("/checklists/{crianca_id}/{data}")
async def atualizar_checklist(
    crianca_id: str,
    data: str,
    payload: ChecklistPayload,
    user: dict = Depends(get_current_user)
):
    """Atualiza um checklist existente (merge/upsert)."""
    logger.info(f"[CHECKLIST] Atualizando checklist para {crianca_id} na data {data}. Payload: {payload.model_dump()}")
    checklist = _query_one(
        "SELECT id FROM checklists WHERE crianca_id = %s AND data = %s",
        (crianca_id, data)
    )
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist não encontrado para atualizar.")

    checklist_id = checklist["id"]

    # Atualiza cabeçalho (apenas se fornecido e não None)
    if payload.resumo_dia is not None:
        _execute(
            "UPDATE checklists SET resumo_dia = %s WHERE id = %s",
            (payload.resumo_dia if payload.resumo_dia != "" else None, checklist_id)
        )

    # Upsert seções
    def upsert_secao(tabela: str, obj):
        if not obj: return
        raw_dados = obj.model_dump(exclude_unset=True)
        if not raw_dados: return
        
        dados = {}
        for k, v in raw_dados.items():
            if v is None: continue
            if isinstance(v, str) and v == "": v = None
            if isinstance(v, list) and len(v) == 0: v = None
            dados[k] = v
            
        if not dados: return
        
        # Testa se existe
        existe = _query_one(f"SELECT checklist_id FROM {tabela} WHERE checklist_id = %s", (checklist_id,))
        if existe:
            set_clause = ", ".join([f"{k} = %s" for k in dados.keys()])
            _execute(f"UPDATE {tabela} SET {set_clause} WHERE checklist_id = %s", tuple(list(dados.values()) + [checklist_id]))
        else:
            colunas = ["checklist_id"] + list(dados.keys())
            valores = [checklist_id] + list(dados.values())
            placeholders = ", ".join(["%s"] * len(colunas))
            cols_str = ", ".join(colunas)
            _execute(f"INSERT INTO {tabela} ({cols_str}) VALUES ({placeholders})", tuple(valores))

    upsert_secao("checklist_sono", payload.sono)
    upsert_secao("checklist_tela", payload.tela)
    upsert_secao("checklist_alimentacao", payload.alimentacao)
    upsert_secao("checklist_comunicacao", payload.comunicacao)
    upsert_secao("checklist_brincar", payload.brincar)
    upsert_secao("checklist_higiene", payload.higiene)
    upsert_secao("checklist_vestuario", payload.vestuario)
    upsert_secao("checklist_movimento", payload.movimento)
    upsert_secao("checklist_humor", payload.humor)
    upsert_secao("checklist_rotina", payload.rotina)
    upsert_secao("checklist_observacoes", payload.observacoes)

    # Dispara a atualização do perfil em background
    from agent.profile import atualizar_perfil
    asyncio.create_task(asyncio.to_thread(atualizar_perfil, crianca_id))

    return {"status": "success", "id": checklist_id}




# ============================================================
# DOCUMENTOS
# ============================================================

@api_router.get("/documentos/{crianca_id}")
async def listar_documentos(crianca_id: str):
    """Lista todos os documentos indexados da criança."""
    rows = _query_many("""
        SELECT id, tipo, especialidade, titulo, data_documento,
               storage_path, processado, criado_em
        FROM documentos
        WHERE crianca_id = %s
        ORDER BY data_documento DESC NULLS LAST, criado_em DESC
    """, (crianca_id,))
    return [dict(r) for r in rows]


@api_router.post("/documentos/{crianca_id}")
async def upload_documento(
    crianca_id: str,
    arquivo: UploadFile = File(...),
    tipo: str = Form(...),
    especialidade: str = Form(default=""),
    titulo: str = Form(...),
    data_documento: str = Form(default=""),
):
    """
    Recebe PDF, salva no R2 e dispara pipeline de ingestão em background.
    Retorna o documento criado com processado=False (pipeline roda em background).
    """
    if not arquivo.filename or not arquivo.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos.")

    # Salvar temporariamente para enviar ao pipeline
    conteudo = await arquivo.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(conteudo)
        tmp_path = tmp.name

    try:
        # Importar aqui para evitar import circular no nível do módulo
        from ingestion.ingestion_pdf import processar_pdf

        usuario_id = settings.USUARIO_ID_PILOTO
        data_doc = data_documento if data_documento else None
        esp = especialidade if especialidade else ""

        # Assinatura: processar_pdf(file_path, tipo, especialidade, titulo, data, crianca_id, usuario_id)
        await asyncio.to_thread(
            processar_pdf,
            tmp_path,      # file_path
            tipo,          # tipo
            esp,           # especialidade
            titulo,        # titulo
            data_doc,      # data
            crianca_id,    # crianca_id
            usuario_id,    # usuario_id
        )

        # processar_pdf retorna None — buscar o documento mais recente inserido
        documento = _query_one("""
            SELECT id, tipo, especialidade, titulo, data_documento, processado, criado_em
            FROM documentos
            WHERE crianca_id = %s AND titulo = %s
            ORDER BY criado_em DESC
            LIMIT 1
        """, (crianca_id, titulo))

        return dict(documento) if documento else {"processado": True, "titulo": titulo}

    except Exception as e:
        logger.error(f"[API] Erro no upload de documento: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao processar documento: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ============================================================
# MARCOS
# ============================================================

@api_router.get("/marcos/{crianca_id}")
async def listar_marcos(crianca_id: str):
    """Retorna todos os marcos da criança em ordem cronológica inversa."""
    rows = _query_many("""
        SELECT m.id, m.descricao, m.data_marco, m.criado_em,
               u.nome AS registrado_por
        FROM marcos m
        LEFT JOIN usuarios u ON u.id = m.usuario_id
        WHERE m.crianca_id = %s
        ORDER BY m.data_marco DESC
    """, (crianca_id,))
    return [dict(r) for r in rows]


class MarcoCreate(BaseModel):
    descricao: str
    data_marco: str  # YYYY-MM-DD


@api_router.post("/marcos/{crianca_id}", status_code=201)
async def criar_marco(crianca_id: str, body: MarcoCreate):
    """Registra um novo marco/conquista da criança."""
    usuario_id = settings.USUARIO_ID_PILOTO  # fixo até ter auth

    novo = _execute_returning("""
        INSERT INTO marcos (crianca_id, usuario_id, descricao, data_marco)
        VALUES (%s, %s, %s, %s)
        RETURNING id, descricao, data_marco, criado_em
    """, (crianca_id, usuario_id, body.descricao, body.data_marco))

    if not novo:
        raise HTTPException(status_code=500, detail="Erro ao registrar marco.")
    return dict(novo)


# ============================================================
# ATIVIDADES
# ============================================================

@api_router.get("/atividades/{crianca_id}")
async def listar_atividades(crianca_id: str):
    """Retorna atividades vinculadas à criança com status e feedback."""
    rows = _query_many("""
        SELECT
            a.id,
            a.titulo,
            a.descricao,
            a.tipo,
            a.objetivo,
            a.materiais,
            a.duracao_minutos,
            a.criado_em,
            u.nome AS criada_por_nome,
            ac.status,
            ac.feedback,
            ac.data_recomendacao
        FROM atividades a
        JOIN atividades_criancas ac ON ac.atividade_id = a.id
        LEFT JOIN usuarios u ON u.id = a.criada_por
        WHERE ac.crianca_id = %s
        ORDER BY ac.data_recomendacao DESC
    """, (crianca_id,))
    return [dict(r) for r in rows]


class AtividadeCreate(BaseModel):
    titulo: str
    descricao: str
    tipo: str
    objetivo: Optional[str] = None
    materiais: Optional[list[str]] = None
    duracao_minutos: Optional[int] = None
    crianca_id: str  # vincula direto à criança


@api_router.post("/atividades", status_code=201)
async def criar_atividade(body: AtividadeCreate):
    """Cadastra nova atividade e vincula à criança."""
    usuario_id = settings.USUARIO_ID_PILOTO  # fixo até ter auth

    # Buscar account_id da criança
    crianca = _query_one("SELECT account_id FROM criancas WHERE id = %s", (body.crianca_id,))
    if not crianca:
        raise HTTPException(status_code=404, detail="Criança não encontrada.")

    account_id = crianca["account_id"]

    atividade = _execute_returning("""
        INSERT INTO atividades (account_id, criada_por, titulo, descricao, tipo, objetivo, materiais, duracao_minutos)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, titulo, tipo, criado_em
    """, (
        account_id, usuario_id,
        body.titulo, body.descricao, body.tipo,
        body.objetivo, body.materiais, body.duracao_minutos
    ))

    if not atividade:
        raise HTTPException(status_code=500, detail="Erro ao criar atividade.")

    atividade_id = atividade["id"]

    # Vincular à criança
    _execute("""
        INSERT INTO atividades_criancas (atividade_id, crianca_id, recomendada_por, status)
        VALUES (%s, %s, %s, 'pendente')
        ON CONFLICT (atividade_id, crianca_id) DO NOTHING
    """, (atividade_id, body.crianca_id, usuario_id))

    return dict(atividade)


class AtividadeStatusUpdate(BaseModel):
    status: str  # pendente | em_andamento | concluida
    feedback: Optional[str] = None
    crianca_id: str


@api_router.patch("/atividades/{atividade_id}/status")
async def atualizar_status_atividade(atividade_id: str, body: AtividadeStatusUpdate):
    """Atualiza status e feedback de uma atividade para uma criança."""
    valores_validos = ("pendente", "em_andamento", "concluida")
    if body.status not in valores_validos:
        raise HTTPException(status_code=400, detail=f"Status inválido. Use: {valores_validos}")

    _execute("""
        UPDATE atividades_criancas
        SET status = %s, feedback = %s
        WHERE atividade_id = %s AND crianca_id = %s
    """, (body.status, body.feedback, atividade_id, body.crianca_id))

    return {"ok": True, "status": body.status}


# ============================================================
# CHAT COM O AGENTE
# ============================================================

class ChatRequest(BaseModel):
    mensagem: str
    crianca_id: str
    session_id: Optional[str] = "web-session-default"  # thread_id do LangGraph


@api_router.post("/chat")
async def chat_com_agente(body: ChatRequest, current_user: dict = Depends(get_current_user)):
    """
    Envia mensagem ao agente LangGraph e retorna a resposta.
    O session_id funciona como thread_id do MemorySaver — mantém histórico da sessão.
    """
    from agent.agent import executar_grafo

    try:
        resposta = await asyncio.to_thread(
            executar_grafo,
            mensagem=body.mensagem,
            telefone=body.session_id,  # thread_id do LangGraph
            usuario_id=current_user["id"],
            nome_usuario=current_user["nome"],
            perfil_usuario=current_user["perfil"],
            crianca_id=body.crianca_id,
        )
        return {"resposta": resposta, "session_id": body.session_id}
    except Exception as e:
        logger.error(f"[API /chat] Erro: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao processar mensagem no agente.")


# ============================================================
# USUÁRIOS (gestão admin)
# ============================================================

@api_router.get("/usuarios")
async def listar_usuarios():
    """Lista todos os usuários. Sem filtro de auth no MVP."""
    rows = _query_many("""
        SELECT id, nome, telefone_whatsapp, email, perfil, ativo, criado_em
        FROM usuarios
        ORDER BY criado_em DESC
    """)
    return [dict(r) for r in rows]


class UsuarioCreate(BaseModel):
    nome: str
    telefone_whatsapp: str
    email: Optional[str] = None
    perfil: str  # admin | família | terapeuta
    especialidade: Optional[str] = None


@api_router.post("/usuarios", status_code=201)
async def criar_usuario(body: UsuarioCreate):
    """Cadastra novo usuário. account_id fixo no piloto."""
    # Buscar account_id do piloto (primeiro account)
    account = _query_one("SELECT id FROM accounts LIMIT 1")
    if not account:
        raise HTTPException(status_code=500, detail="Nenhuma conta encontrada no banco.")

    perfis_validos = ("admin", "família", "terapeuta")
    if body.perfil not in perfis_validos:
        raise HTTPException(status_code=400, detail=f"Perfil inválido. Use: {perfis_validos}")

    try:
        novo = _execute_returning("""
            INSERT INTO usuarios (account_id, nome, telefone_whatsapp, email, perfil)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, nome, telefone_whatsapp, email, perfil, ativo, criado_em
        """, (account["id"], body.nome, body.telefone_whatsapp, body.email, body.perfil))

        # Se for terapeuta, vincular à criança piloto
        if body.perfil == "terapeuta" and body.especialidade:
            _execute("""
                INSERT INTO criancas_terapeutas (crianca_id, usuario_id, especialidade)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (settings.CRIANCA_ID_PILOTO, novo["id"], body.especialidade))

        return dict(novo)
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Telefone já cadastrado.")
        logger.error(f"[API] Erro ao criar usuário: {e}")
        raise HTTPException(status_code=500, detail="Erro ao cadastrar usuário.")


@api_router.patch("/usuarios/{usuario_id}/ativo")
async def toggle_usuario_ativo(usuario_id: str):
    """Alterna o status ativo/inativo de um usuário."""
    _execute("""
        UPDATE usuarios
        SET ativo = NOT ativo
        WHERE id = %s
    """, (usuario_id,))

    row = _query_one("SELECT id, nome, ativo FROM usuarios WHERE id = %s", (usuario_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return dict(row)


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    telefone_whatsapp: Optional[str] = None
    email: Optional[str] = None
    perfil: Optional[str] = None
    senha: Optional[str] = None

@api_router.patch("/usuarios/{usuario_id}")
async def atualizar_usuario(usuario_id: str, body: UsuarioUpdate):
    """Atualiza dados do usuário (incluindo senha se fornecida)."""
    # Construir query dinamicamente baseada nos campos fornecidos
    updates = []
    values = []
    
    if body.nome is not None:
        updates.append("nome = %s")
        values.append(body.nome)
    
    if body.telefone_whatsapp is not None:
        updates.append("telefone_whatsapp = %s")
        values.append(body.telefone_whatsapp)
        
    if body.email is not None:
        updates.append("email_web = %s")
        values.append(body.email)
        
    if body.perfil is not None:
        perfis_validos = ("admin", "família", "terapeuta")
        if body.perfil not in perfis_validos:
            raise HTTPException(status_code=400, detail=f"Perfil inválido. Use: {perfis_validos}")
        updates.append("perfil = %s")
        values.append(body.perfil)
        
    if body.senha is not None and body.senha.strip() != "":
        hashed = get_password_hash(body.senha.strip())
        updates.append("senha_hash = %s")
        values.append(hashed)
        
    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum dado fornecido para atualização.")
        
    query = f"UPDATE usuarios SET {', '.join(updates)} WHERE id = %s RETURNING id, nome, telefone_whatsapp, email_web as email, perfil, ativo, criado_em"
    values.append(usuario_id)
    
    try:
        atualizado = _execute_returning(query, tuple(values))
        if not atualizado:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        return dict(atualizado)
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="E-mail ou telefone já cadastrado.")
        logger.error(f"[API] Erro ao atualizar usuário: {e}")
        raise HTTPException(status_code=500, detail="Erro ao atualizar usuário.")
