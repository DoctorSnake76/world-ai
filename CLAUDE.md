# CLAUDE.md — World AI · Document Maître
> **CE FICHIER EST LA SOURCE DE VÉRITÉ ABSOLUE DU PROJET.**
> Claude Code : lis ce fichier intégralement avant chaque session. Ne suppose rien qui ne soit pas ici.
> Maintenu à jour après chaque phase complétée.

---

## 🧭 Vision du Projet

**World AI** est un méta-orchestrateur d'IA personnel et professionnel, open-source, souverain et auto-évolutif.

Il ne remplace pas un LLM — il rend **n'importe quel LLM 10x plus capable, fiable et personnalisé** en ajoutant :
- Une mémoire causale vivante de l'utilisateur (graphe d'ontologie)
- Une logique déterministe anti-hallucination
- Une simulation des conséquences avant chaque action critique
- Une captation continue de la vie de l'utilisateur (voix, lectures, décisions)
- Une auto-évolution réelle via fine-tuning LoRA et compilation de skills

**Cible** : particuliers et professionnels qui veulent une IA qui les connaît, agit à leur place en toute sécurité, et s'améliore avec le temps.

**Budget** : ≤ 25 €/mois en Phase 1 (VPS Hetzner CX33 ~7€ + API LLM ~15€ + divers ~3€).

**Licence** : Apache 2.0 — totalement open source.

**Repo GitHub** : `https://github.com/[USERNAME]/world-ai`

---

## 🏗️ Architecture — Les 7 Couches

```
┌─────────────────────────────────────────────────────────────┐
│  COUCHE 0 — OMI LAYER (Soul Collector)                      │
│  Captation continue : voix, lectures, actions, contexte     │
│  Stack : OMI app + Whisper STT + NLP extraction             │
├─────────────────────────────────────────────────────────────┤
│  COUCHE 1 — ÂME NUMÉRIQUE (Jumeau Cognitif)                 │
│  Knowledge Graph causal de l'utilisateur                    │
│  Stack : Memgraph + Qdrant + ontologie personnelle          │
├─────────────────────────────────────────────────────────────┤
│  COUCHE 2 — CERVEAU EXÉCUTIF (Agent Cascade)                │
│  SAS en premier → MAS si confiance < seuil                  │
│  Stack : xLAM-2 7B + Routeur LLM tiéré + OpenRouter        │
├─────────────────────────────────────────────────────────────┤
│  COUCHE 3 — BOUCLIER LOGIQUE (Gardien Déterministe)         │
│  Vérification règles avant chaque action                    │
│  Stack : Synalinks + Pydantic v2 + Memgraph SPARQL          │
├─────────────────────────────────────────────────────────────┤
│  COUCHE 4 — SIMULATEUR DE DÉCISION (World Model)            │
│  Simulation conséquences → résumé → confirmation user       │
│  Stack : LingBot-World-Fast + Decision Rehearsal Loop       │
├─────────────────────────────────────────────────────────────┤
│  COUCHE 5 — SYSTÈME NERVEUX (MCP Servers)                   │
│  Exécution réelle après validation                          │
│  Stack : MCP Servers locaux (stdio + HTTP/TLS)              │
├─────────────────────────────────────────────────────────────┤
│  COUCHE 6 — AUTO-ÉVOLUTION (Le Phénix)                      │
│  Fine-tuning LoRA + Skill Compiler + HOPE memory           │
│  Stack : LoRA/QLoRA + DSPy + HOPE (PyTorch)                 │
└─────────────────────────────────────────────────────────────┘
         ⟳ Boucle continue : Couche 6 → alimente → Couches 1,2,3
```

### Principes fondamentaux à ne JAMAIS violer

1. **Sécurité d'abord** : container hardening, read-only root FS, namespace isolation, secrets en vault, pre-execution scanner sur toute commande shell.
2. **SAS avant MAS** : traiter toute requête par agent unique d'abord. MAS uniquement si `confidence_score < 0.75`.
3. **Simulation avant action critique** : toute action irréversible (suppression, envoi email, transaction, écriture fichier hors sandbox) déclenche obligatoirement la boucle de simulation + confirmation utilisateur.
4. **MCP partout** : tous les outils exposés via MCP servers — portabilité garantie, audit complet.
5. **Secrets jamais en plaintext** : utiliser Infisical (self-hosted) ou variables d'environnement Docker Secrets.
6. **Aucun credential dans le repo Git** : `.gitignore` strict, `.env.example` uniquement.

---

## 📁 Structure du Repo

```
world-ai/
├── CLAUDE.md                    # CE FICHIER — source de vérité
├── ARCHITECTURE.md              # Détail technique de chaque couche
├── ROADMAP.md                   # Phases, milestones, statuts
├── CHANGELOG.md                 # Historique des changements
├── LICENSE                      # Apache 2.0
├── README.md                    # Documentation publique projet
├── .gitignore                   # Node, Python, .env, secrets
├── .env.example                 # Template variables d'env (sans valeurs)
│
├── docker-compose.yml           # Stack complète — démarrage en 1 commande
├── docker-compose.dev.yml       # Override pour développement local
│
├── core/                        # Moteur central
│   ├── router/                  # Routage LLM tiéré
│   │   ├── router.py            # Logique de routing (budget → frontier)
│   │   ├── confidence.py        # Calcul score de confiance
│   │   └── models.py            # Définitions des modèles disponibles
│   └── cascade/                 # Agent Cascade (SAS → MAS)
│       ├── agent.py             # Agent principal SAS
│       ├── evaluator.py         # Évaluateur de difficulté
│       └── dispatcher.py        # Dispatch vers MAS si nécessaire
│
├── soul/                        # Âme Numérique
│   ├── graph/                   # Memgraph queries et schemas
│   │   ├── schema.cypher        # Schéma ontologique utilisateur
│   │   └── queries.py           # CRUD Knowledge Graph
│   ├── vectors/                 # Qdrant collections
│   │   └── collections.py       # Définition et gestion collections
│   └── profile/                 # Profil utilisateur
│       ├── extractor.py         # Extraction patterns depuis conversations
│       └── updater.py           # Mise à jour automatique du profil
│
├── shield/                      # Bouclier Logique
│   ├── synalinks_config.py      # Configuration Synalinks
│   ├── rules_engine.py          # Moteur de règles déterministes
│   └── schemas/                 # Schémas Pydantic par domaine
│       ├── email_action.py
│       ├── file_action.py
│       └── calendar_action.py
│
├── simulation/                  # Simulateur de Décision
│   ├── rehearsal.py             # Boucle de répétition de décision
│   ├── risk_classifier.py       # Classification risque d'une action
│   └── summary_generator.py    # Génération résumé conséquences
│
├── nervous/                     # Système Nerveux (MCP)
│   ├── servers/                 # MCP Servers
│   │   ├── filesystem_mcp.py    # Accès fichiers (sandbox strict)
│   │   ├── web_mcp.py           # Recherche web + fetch
│   │   ├── email_mcp.py         # Lecture/envoi email
│   │   ├── calendar_mcp.py      # Calendrier
│   │   └── browser_mcp.py       # Playwright browser automation
│   └── gateway.py               # Passerelle MCP centrale
│
├── evolution/                   # Auto-Évolution
│   ├── skill_compiler.py        # Tâche réussie → skill persistant
│   ├── lora_trainer.py          # Interface RunPod pour fine-tuning
│   └── hope/                    # Architecture HOPE (Nested Learning)
│       └── memory.py            # Continuum Memory System
│
├── interfaces/                  # Interfaces Utilisateur
│   ├── telegram/
│   │   ├── bot.py               # Handler principal bot Telegram
│   │   ├── handlers/            # Handlers par type de message
│   │   │   ├── text_handler.py
│   │   │   ├── voice_handler.py
│   │   │   └── confirmation_handler.py
│   │   └── keyboards.py         # Claviers inline Telegram
│   └── web/                     # Interface Web (Next.js via Dify)
│       └── README.md            # Configuration Dify pour l'UI
│
├── n8n/                         # Workflows No-Code
│   ├── exports/                 # Workflows n8n exportés en JSON
│   │   ├── main_orchestrator.json
│   │   ├── proactive_suggestions.json
│   │   ├── human_approval_gate.json
│   │   └── scheduled_tasks.json
│   └── README.md                # Guide d'import des workflows
│
├── config/                      # Configuration globale
│   ├── settings.py              # Settings centralisées (pydantic-settings)
│   └── logging.py               # Configuration logging structuré
│
├── tests/                       # Tests
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── docs/                        # Documentation
    ├── setup.md                 # Guide d'installation complet
    ├── api.md                   # Documentation API interne
    └── contributing.md          # Guide de contribution
```

---

## 🔧 Stack Technique Complète

### Infrastructure
| Composant | Technologie | Version cible | Notes |
|---|---|---|---|
| VPS | Hetzner CX33 | — | 4 vCPU, 8GB RAM, 80GB SSD, EU |
| Container mgmt | Coolify | latest | Web UI Docker management |
| Orchestration | Docker Compose | v2+ | Stack complète en 1 commande |
| Reverse proxy | Traefik | v3 | SSL automatique Let's Encrypt |
| Secrets | Infisical | self-hosted | Vault secrets, zéro plaintext |

### IA et Modèles
| Composant | Technologie | Notes |
|---|---|---|
| Agent principal (local) | xLAM-2-7b-fc-r (GGUF Q4) | Function-calling dédié |
| Inférence locale | vLLM ou llama.cpp | Selon RAM disponible |
| Routeur LLM | OpenRouter API | 250+ modèles, single endpoint |
| LLM budget (70%) | DeepSeek V3.2 / Qwen3.5-9B | ~0.10-0.28$/M tokens |
| LLM mid (20%) | Llama 4 Scout / Gemini Flash | ~0.25$/M tokens |
| LLM frontier (10%) | Claude Opus 4.6 / GPT-5 | Cas critiques uniquement |
| STT | Whisper (openai/whisper) | Local, modèle medium |

### Mémoire et Données
| Composant | Technologie | Port | Notes |
|---|---|---|---|
| Knowledge Graph | Memgraph | 7687 | Ontologie causale utilisateur |
| Base vectorielle | Qdrant | 6333 | Mémoire sémantique |
| Graph léger | Kuzu | embedded | Embedded, zéro serveur |
| Cache | Redis | 6379 | Sessions, queues |

### Orchestration et Interfaces
| Composant | Technologie | Port | Notes |
|---|---|---|---|
| Workflows no-code | n8n | 5678 | Crons, webhooks, intégrations |
| Interface Web UI | Dify | 3000 | Paramétrage, dashboard |
| Logs structurés | Langfuse (self-hosted) | 3001 | Tracing chaque step agent |
| Bot Telegram | python-telegram-bot v21 | — | Handler principal |

### Neuro-Symbolique et Bouclier
| Composant | Technologie | Notes |
|---|---|---|
| Couche symbolique | Synalinks | Keras-style, JSON-schema |
| Validation schémas | Pydantic v2 | Strict mode |
| Règles métier | Memgraph SPARQL | Depuis le Knowledge Graph |

### Languages et Frameworks
- **Python 3.12** — langage principal (backend, agents, MCP servers)
- **FastAPI** — API REST interne entre composants
- **Pydantic v2** — validation données stricte
- **Next.js 15** — interface Web (via Dify ou custom)
- **Docker Compose** — orchestration services

---

## 🌊 Phases de Développement

### ✅ PHASE 00 — Initialisation (FAIT)
- [x] Document CLAUDE.md rédigé
- [x] Architecture définie
- [x] Stack technique choisie

---

### 🔄 PHASE 01 — FONDATION OPÉRATIONNELLE (EN COURS)
**Durée cible** : Semaines 1–2
**Objectif** : Agent fonctionnel sur Telegram + Interface Web de base

#### Ordre d'implémentation (suivre dans l'ordre strict)

**Étape 1.1 — Infrastructure Docker**
- [x] `docker-compose.yml` complet avec tous les services
- [x] `docker-compose.dev.yml` override pour dev local
- [x] `.env.example` avec toutes les variables nécessaires
- [x] `.gitignore` strict (Python, Node, secrets, .env)
- [ ] Test : `docker-compose up -d` → tous services healthy

**Étape 1.2 — Routeur LLM Tiéré**
- [ ] `core/router/models.py` : définition des modèles (budget/mid/frontier)
- [ ] `core/router/confidence.py` : calcul score confiance (longueur, complexité, domaine)
- [ ] `core/router/router.py` : logique routing (score → sélection modèle)
- [ ] `config/settings.py` : settings centralisées avec pydantic-settings
- [ ] Test unitaire : requête simple → DeepSeek, requête complexe → Claude

**Étape 1.3 — Agent Cascade (SAS)**
- [ ] `core/cascade/agent.py` : agent unique principal avec tool-calling
- [ ] `core/cascade/evaluator.py` : évaluation difficulté post-réponse
- [ ] Intégration OpenRouter API
- [ ] Intégration xLAM-2 local (llama.cpp)
- [ ] Test : conversation basique + appel d'outil simple

**Étape 1.4 — MCP Servers de base**
- [ ] `nervous/servers/filesystem_mcp.py` : lecture/écriture fichiers (sandbox /data/user/)
- [ ] `nervous/servers/web_mcp.py` : recherche Brave + fetch URL
- [ ] `nervous/gateway.py` : passerelle centrale MCP
- [ ] Test : agent lit un fichier via MCP, agent fait une recherche web

**Étape 1.5 — Bot Telegram**
- [ ] `interfaces/telegram/bot.py` : setup bot, handlers de base
- [ ] `interfaces/telegram/handlers/text_handler.py` : messages texte → agent
- [ ] `interfaces/telegram/handlers/voice_handler.py` : voice note → Whisper → agent
- [ ] `interfaces/telegram/handlers/confirmation_handler.py` : boutons Oui/Non/Modifier
- [ ] `interfaces/telegram/keyboards.py` : claviers inline pour confirmations
- [ ] Test : envoie un message Telegram → l'agent répond

**Étape 1.6 — Interface Web (Dify)**
- [ ] Configuration Dify dans docker-compose
- [ ] Création app Dify : chat + paramétrage de base
- [ ] Connexion Dify → OpenRouter (modèles disponibles)
- [ ] Page paramétrage : choix du modèle par défaut, seuil de confiance
- [ ] Test : accès web → chat fonctionne

**Étape 1.7 — Logs et Observabilité**
- [ ] Langfuse self-hosted dans docker-compose
- [ ] Instrumentation : chaque appel LLM tracé (modèle, latence, coût, score)
- [ ] Dashboard Langfuse accessible
- [ ] Test : après une conversation, voir le trace complet dans Langfuse

**Étape 1.8 — Workflow n8n Principal**
- [ ] n8n installé et accessible
- [ ] Workflow : Telegram webhook → pre-processing → Agent → post-processing → réponse
- [ ] Export JSON du workflow → `n8n/exports/main_orchestrator.json`
- [ ] Documentation d'import dans `n8n/README.md`

---

### ⏳ PHASE 02 — ÂME NUMÉRIQUE V1 (À VENIR)
**Durée cible** : Semaines 3–5
**Objectif** : L'IA connaît l'utilisateur et propose des suggestions proactives

- [ ] Memgraph déployé + schéma ontologique utilisateur
- [ ] Qdrant déployé + collections : conversations, faits, préférences
- [ ] `soul/profile/extractor.py` : extraction automatique profil depuis conversations
- [ ] `soul/profile/updater.py` : mise à jour graphe après chaque interaction
- [ ] Moteur de suggestions proactives (n8n Cron toutes les heures)
- [ ] Template suggestion Telegram : "J'ai remarqué X → veux-tu que j'automatise ?"
- [ ] Dashboard profil dans interface Web
- [ ] Règles personnelles auto-détectées depuis le graphe

---

### ⏳ PHASE 03 — BOUCLIER LOGIQUE + SIMULATION (À VENIR)
**Durée cible** : Semaines 6–9

- [ ] Synalinks intégré : validation avant chaque action
- [ ] Classification actions : sûre / risquée / irréversible
- [ ] Boucle simulation légère pour actions irréversibles
- [ ] Gate confirmation Telegram (boutons inline : Confirmer / Modifier / Annuler)
- [ ] Audit log complet dans l'interface Web

---

### ⏳ PHASE 04 — OMI LAYER (À VENIR)
**Durée cible** : Mois 3

- [ ] Intégration OMI app (webhook vers n8n)
- [ ] Pipeline Whisper STT → NLP → Memgraph
- [ ] Timeline de vie dans l'interface Web

---

### ⏳ PHASE 05 — AUTO-ÉVOLUTION (À VENIR)
**Durée cible** : Mois 4–6

- [ ] Skill Compiler : tâche réussie → skill persistant
- [ ] LoRA fine-tuning via RunPod Spot API
- [ ] Architecture HOPE partielle : mémoire multi-échelle
- [ ] Self-improvement loop sur les prompts (DSPy)

---

## 🔒 Conventions de Code

### Python
- **Python 3.12** strictement
- **Type hints** partout, sans exception
- **Pydantic v2** pour toute validation de données
- **async/await** pour tous les appels I/O (LLM, DB, MCP)
- **Logging** : `structlog` en JSON, niveau INFO en prod, DEBUG en dev
- **Tests** : pytest, couverture minimale 80% sur `core/`
- Format : `ruff` pour lint, `black` pour format

### Conventions de nommage
- Fichiers : `snake_case.py`
- Classes : `PascalCase`
- Fonctions et variables : `snake_case`
- Constantes : `UPPER_SNAKE_CASE`
- Variables d'environnement : `WORLDAI_PREFIXE_NOM`

### Variables d'environnement (préfixe WORLDAI_)
```
WORLDAI_OPENROUTER_API_KEY=
WORLDAI_TELEGRAM_BOT_TOKEN=
WORLDAI_ANTHROPIC_API_KEY=
WORLDAI_MEMGRAPH_URI=bolt://memgraph:7687
WORLDAI_QDRANT_URL=http://qdrant:6333
WORLDAI_REDIS_URL=redis://redis:6379
WORLDAI_LANGFUSE_SECRET_KEY=
WORLDAI_LANGFUSE_PUBLIC_KEY=
WORLDAI_LLM_BUDGET_MODEL=deepseek/deepseek-chat
WORLDAI_LLM_MID_MODEL=meta-llama/llama-4-scout
WORLDAI_LLM_FRONTIER_MODEL=anthropic/claude-opus-4-6
WORLDAI_CONFIDENCE_THRESHOLD=0.75
WORLDAI_SIMULATION_THRESHOLD=0.40
WORLDAI_ENV=production
```

### Gestion des erreurs
- Toujours logger l'erreur avant de la propager
- Ne jamais exposer les stack traces à l'utilisateur final
- Actions critiques échouées → notification Telegram à l'admin
- Retry automatique (max 3) avec backoff exponentiel pour les appels LLM

### Docker
- Chaque service a son propre Dockerfile dans son dossier
- Healthchecks définis pour tous les services
- Ressources limitées (CPU, mémoire) par service
- Networks isolés : `internal` (services) et `public` (Traefik uniquement)
- Volumes nommés pour toutes les données persistantes

---

## 🧪 Logique de Routing LLM Tiéré

```python
# Règles de routing (dans core/router/router.py)

def compute_confidence_score(request: AgentRequest) -> float:
    """
    Score 0.0 à 1.0 — plus c'est bas, plus c'est complexe/risqué
    Score > 0.80 → modèle budget
    Score 0.60-0.80 → modèle mid
    Score < 0.60 → modèle frontier
    """
    factors = {
        "length": normalize(len(request.content), 0, 2000),
        "complexity": detect_complexity(request.content),  # keywords, nested logic
        "domain": domain_risk_score(request.content),      # finance, medical, legal
        "tools_required": len(request.required_tools) / 10,
        "history_depth": request.conversation_depth / 20,
    }
    return weighted_average(factors, weights={...})

# Modèles disponibles (OpenRouter slugs)
BUDGET_MODELS = [
    "deepseek/deepseek-chat",           # 0.14$/M — défaut
    "qwen/qwen3.5-9b-instruct",         # 0.10$/M
]
MID_MODELS = [
    "meta-llama/llama-4-scout",         # 0.11$/0.34$/M
    "google/gemini-flash-1.5",          # 0.25$/M
]
FRONTIER_MODELS = [
    "anthropic/claude-opus-4-6",        # Cas critiques
    "openai/gpt-5",                     # Backup
]
```

---

## 🤖 Logique Agent Cascade

```python
# core/cascade/agent.py — Flux principal

async def process_request(request: UserRequest) -> AgentResponse:
    # 1. Routing : quel modèle ?
    confidence = compute_confidence_score(request)
    model = select_model(confidence)

    # 2. SAS : traitement agent unique d'abord
    response = await single_agent_process(request, model)

    # 3. Évaluation post-traitement
    quality_score = await evaluate_response(response, request)

    if quality_score >= CONFIDENCE_THRESHOLD:
        # 4a. Assez bon → on livre directement
        return response
    else:
        # 4b. Insuffisant → escalade MAS ciblé
        return await multi_agent_process(request, frontier_model)

# Classification actions (pour simulation)
ACTION_RISK_LEVELS = {
    "read_file": "safe",
    "web_search": "safe",
    "write_file": "risky",       # → confirmation
    "send_email": "risky",       # → confirmation
    "delete_file": "critical",   # → simulation + confirmation
    "api_transaction": "critical" # → simulation + confirmation
}
```

---

## 💬 Format des Messages Telegram

```
# Message standard
🤖 [Résumé de ce que l'IA a fait]
─────────────────────
📊 Modèle : DeepSeek V3 | Coût : ~0.001€
⏱️ Temps : 1.2s | Confiance : 87%

# Message avec confirmation requise
⚠️ ACTION REQUISE
─────────────────────
Je vais envoyer l'email suivant :
À : jean@example.com
Objet : Rapport Q3

[Confirmer ✅] [Modifier ✏️] [Annuler ❌]

# Suggestion proactive (Phase 02)
💡 SUGGESTION
─────────────────────
J'ai remarqué que tu envoies ce rapport
chaque lundi manuellement depuis 3 semaines.
Veux-tu que j'automatise ça ?

[Oui, automatise 🚀] [Non merci ✋]
```

---

## 📊 Métriques à Tracker (Langfuse)

Pour chaque interaction, logger :
- `model_used` : modèle sélectionné
- `confidence_score` : score qui a déterminé le routing
- `response_time_ms` : latence totale
- `tokens_in` / `tokens_out` : consommation
- `estimated_cost_eur` : coût estimé
- `action_risk_level` : si une action MCP a été déclenchée
- `simulation_triggered` : si la boucle simulation s'est activée
- `user_confirmed` : si l'utilisateur a confirmé/refusé
- `skill_compiled` : si un skill a été créé (Phase 05)

---

## 🚦 Instructions pour Claude Code

### Avant de commencer une session
1. Lis ce fichier `CLAUDE.md` intégralement
2. Identifie la phase en cours (cherche `🔄 EN COURS`)
3. Identifie la prochaine étape non cochée `[ ]`
4. Vérifie qu'aucun step précédent n'est incomplet

### Pendant le développement
- Implémente **un step à la fois** — ne saute pas d'étapes
- Après chaque fichier créé : ajoute les tests correspondants
- Respecte strictement les conventions de nommage
- N'invente JAMAIS de bibliothèques ou d'APIs — utilise uniquement ce qui est listé dans ce fichier
- Si tu as un doute sur un choix architectural : arrête et demande

### Après avoir implémenté une étape
- Coche la case `[ ]` → `[x]` dans ce fichier
- Mets à jour `CHANGELOG.md` avec ce qui a été fait
- Génère ou mets à jour les tests si nécessaire
- Si la phase est complète : mets à jour le statut `⏳` → `✅`

### Ce que tu NE dois pas faire
- ❌ Jamais utiliser des bibliothèques non listées sans validation
- ❌ Jamais créer de fichiers .env avec de vraies valeurs
- ❌ Jamais exposer des credentials dans le code
- ❌ Jamais sauter l'étape tests pour "aller plus vite"
- ❌ Jamais modifier l'architecture sans mise à jour de ce fichier

---

## 🔗 Ressources Clés

| Ressource | URL |
|---|---|
| OpenRouter API | https://openrouter.ai/docs |
| xLAM-2 Models | https://github.com/SalesforceAIResearch/xLAM |
| Memgraph Docs | https://memgraph.com/docs |
| Qdrant Docs | https://qdrant.tech/documentation |
| Synalinks | https://github.com/SynaLinks/synalinks |
| LingBot-World | https://github.com/leofan90/awesome-world-models |
| n8n Docs | https://docs.n8n.io |
| Dify Docs | https://docs.dify.ai |
| Coolify Docs | https://coolify.io/docs |
| Hetzner Cloud | https://www.hetzner.com/cloud |
| python-telegram-bot | https://docs.python-telegram-bot.org |
| Langfuse | https://langfuse.com/docs |
| OMI Open Source | https://github.com/BasedHardware/omi |

---

*Dernière mise à jour : Phase 01 — Étape 1.1 complétée (Infrastructure Docker)*
*Maintenu par : Alexis Druaux + Claude Code (Sonnet 4.6)*
