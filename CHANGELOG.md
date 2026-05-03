# CHANGELOG — World AI

## [Phase 01 — Étape 1.4] — 2026-05-03

### Added
- `nervous/servers/base.py` — `BaseMCPServer` abstract class (interface commune pour tous les MCP servers)
- `nervous/servers/filesystem_mcp.py` — `FilesystemMCP` : 5 outils sandboxés (`fs_read_file`, `fs_write_file`, `fs_list_directory`, `fs_file_exists`, `fs_delete_file`), sandbox enforcement strict via path resolution, init lazy du répertoire
- `nervous/servers/web_mcp.py` — `WebMCP` : `web_search` (Brave Search API) + `web_fetch` (HTTP GET avec mitigation SSRF sur loopback/private IPs), stripping HTML automatique
- `nervous/gateway.py` — `MCPGateway` : registre central des servers, routing O(1) par outil, `register/unregister`, app FastAPI (`GET /health`, `GET /tools`, `POST /execute`)
- `config/settings.py` — ajout `brave_api_key`, `mcp_sandbox_root`, `mcp_fetch_timeout_s`, `mcp_fetch_max_bytes`
- `.env.example` — ajout variables `WORLDAI_BRAVE_API_KEY`, `WORLDAI_MCP_SANDBOX_ROOT`, `WORLDAI_MCP_FETCH_TIMEOUT_S`, `WORLDAI_MCP_FETCH_MAX_BYTES`
- **80 nouveaux tests** : `test_mcp_filesystem.py` (32), `test_mcp_web.py` (27), `test_mcp_gateway.py` (21) — 100% passing

### Suite complète
**150 tests, 100% passing** (router 29 + cascade evaluator 29 + cascade agent 12 + filesystem 32 + web 27 + gateway 21)

---

## [Phase 01 — Étape 1.3] — 2026-05

### Added
- `core/cascade/agent.py` — `CascadeAgent` : pipeline SAS → évaluation → escalade MAS
- `core/cascade/evaluator.py` — `QualityEvaluator` : score heuristique post-réponse
- `core/cascade/types.py` — types partagés (`UserRequest`, `AgentResponse`, `ToolCall`, `ToolResult`, …)
- `core/cascade/openrouter.py` — client HTTP async OpenRouter (OpenAI-compatible)
- `core/cascade/dispatcher.py` — escalade MAS vers modèle frontier
- Intégration OpenRouter API + xLAM-2 local via `WORLDAI_XLAM_LOCAL_URL`
- 41 tests unitaires (évaluateur + pipeline CascadeAgent) — 100% passing

---

## [Phase 01 — Étapes 1.1 & 1.2] — 2026-05

### Added
- `docker-compose.yml` — stack complète (Traefik, Redis, PostgreSQL, Memgraph, Qdrant, n8n, Langfuse, Dify) avec healthchecks
- `docker-compose.dev.yml` — override développement local
- `.env.example` — toutes les variables `WORLDAI_*`
- `.gitignore` — Python, Node, secrets, .env
- `core/router/models.py` — définition des modèles (budget/mid/frontier)
- `core/router/confidence.py` — calcul score de confiance
- `core/router/router.py` — logique de routing tiéré
- `config/settings.py` — settings centralisées Pydantic v2
- 29 tests unitaires routeur — 100% passing

---

## [Phase 00] — 2026-05

### Added
- `CLAUDE.md` — document maître, source de vérité
- `ARCHITECTURE.md` — détail technique des 7 couches
- `ROADMAP.md` — phases et milestones
- `LICENSE` — Apache 2.0
- `README.md` — documentation publique
