-- ══════════════════════════════════════════════════════════════
-- PostgreSQL — Initialisation des bases de données World AI
-- Exécuté automatiquement au premier démarrage du container
-- ══════════════════════════════════════════════════════════════

-- Base pour n8n (workflow orchestrator)
CREATE DATABASE n8n;

-- Base pour Langfuse (LLM observability)
CREATE DATABASE langfuse;

-- Base pour Dify (Web UI / AI platform)
CREATE DATABASE dify;

-- Accorder tous les droits à l'utilisateur principal
GRANT ALL PRIVILEGES ON DATABASE n8n TO worldai;
GRANT ALL PRIVILEGES ON DATABASE langfuse TO worldai;
GRANT ALL PRIVILEGES ON DATABASE dify TO worldai;
