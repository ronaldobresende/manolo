# Fase 4 — Guia de Startup

## 1. Migration do banco (Neon)

Rode o SQL abaixo no painel SQL do Neon (ou via psql):

```
scripts/migrate_web.sql
```

Cria: tabela `marcos` + colunas `senha_hash` e `email_web` em `usuarios`.

---

## 2. Instalar dependências do backend

```bash
# Na raiz do monorepo (c:\projects\python\manolo)
pip install python-multipart python-jose[cryptography] bcrypt
# ou
pip install -r requirements.txt
```

---

## 3. Adicionar variável de CORS no Render (backend)

No painel do Render, nas variáveis de ambiente, adicionar:

```
WEB_CORS_ORIGINS=http://localhost:3000
```

(Depois do deploy da Vercel: adicionar `,https://seu-app.vercel.app` ao valor)

---

## 4. Instalar dependências do frontend

```bash
cd web
npm install
```

---

## 5. Rodar localmente

**Terminal 1 — Backend FastAPI:**
```bash
# Na raiz do projeto
uvicorn channels.main:app --reload --port 8000
```

**Terminal 2 — Frontend Next.js:**
```bash
cd web
npm run dev
```

Acesse: **http://localhost:3000**

---

## 6. Estrutura do que foi criado

### Backend
| Arquivo | O que faz |
|---|---|
| `scripts/migrate_web.sql` | Migration para rodar no Neon |
| `channels/api.py` | 16 rotas REST `/api/*` |
| `channels/main.py` | CORS + mount do api_router |
| `core/config.py` | `WEB_CORS_ORIGINS`, `JWT_SECRET_KEY` preparados |

### Frontend (`web/`)
| Arquivo | O que faz |
|---|---|
| `app/dashboard/page.tsx` | Perfil vivo com cards por domínio |
| `app/dashboard/evolucao/page.tsx` | 4 gráficos Recharts (sono, comunicação, humor, brincar) |
| `app/dashboard/checklists/page.tsx` | Tabela paginada + modal de detalhe |
| `app/dashboard/documentos/page.tsx` | Upload drag-and-drop + listagem |
| `app/dashboard/marcos/page.tsx` | Timeline com formulário inline |
| `app/dashboard/atividades/page.tsx` | Cards expansíveis com status |
| `app/dashboard/chat/page.tsx` | Chat estilo WhatsApp Web |
| `app/dashboard/usuarios/page.tsx` | Gestão de usuários |

---

## 7. Deploy na Vercel

```bash
# Instalar Vercel CLI
npm i -g vercel

# Na pasta web/
cd web
vercel deploy

# Definir variável de ambiente na Vercel:
# NEXT_PUBLIC_API_URL = https://seu-backend.onrender.com
```

Depois: atualizar `WEB_CORS_ORIGINS` no Render com o domínio da Vercel.

---

## 8. Próximo passo: Autenticação (Fase 4.1)

Ver `DEBITOS_TECNICOS.md` § 5 — tudo já preparado:
- `web/lib/auth.ts` — stub com TODO detalhado
- `core/config.py` — JWT settings declarados
- `requirements.txt` — bibliotecas já adicionadas
- `scripts/migrate_web.sql` — colunas `senha_hash` e `email_web` já criadas
