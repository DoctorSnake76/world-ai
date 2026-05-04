# CLAUDE.md — World AI · Document Maître AGI
> **CE FICHIER EST LA SOURCE DE VÉRITÉ ABSOLUE DU PROJET.**
> Claude Code : lis ce fichier intégralement avant chaque session. Ne suppose rien qui ne soit pas ici.
> Maintenu à jour après chaque phase complétée.

---

## 🧭 Vision du Projet

**World AI** est un méta-orchestrateur d'IA personnel et professionnel, open-source, souverain et auto-évolutif. Il s'affranchit du paradigme "Prompt → Réponse" pour implémenter un **organisme cognitif bio-inspiré** : mémoire causale vivante, conscience temporelle, auto-réparation, preuve formelle des actions, et évolution nocturne autonome.

Il rend n'importe quel LLM 10x plus puissant en ajoutant :
- **Un Réflexe neuronal** : Cache sémantique (Qdrant > 98%) — zéro latence pour le connu
- **Une Âme causale** : Spreading Activation + Intent Tracking — mémoire qui pense et comprend le POURQUOI
- **Un Cerveau fractal** : Agent Cascade SAS→MAS + Consensus Multi-Modèle + Analogie Cross-Domaine
- **Un Bouclier formel** : Chain-of-Code + Red-Teaming + SMT Solvers (Phase 7) — zéro erreur non prouvée
- **Un Temps liquide** : Conscience asynchrone — l'agent ne bloque jamais
- **Un Système nerveux auto-plastique** : Self-Healing + Tool Synthesis — zéro maintenance humaine
- **Un Métabolisme nocturne** : Ebbinghaus Decay + Dynamic Prompt Library + DSPy — évolution continue
- **Une Empathie cognitive** : Theory of Mind + Persona Cloner + Autonomie proactive selon charge user

**Cible** : particuliers et professionnels qui veulent une IA qui les connaît, agit à leur place en toute sécurité, s'auto-répare, et s'améliore avec le temps.
**Budget** : ≤ 25 €/mois Phase 1 (Hetzner CX33 ~7€ + API LLM ~15€ + divers ~3€).
**Licence** : Apache 2.0 — totalement open source.
**Repo GitHub** : `https://github.com/[USERNAME]/world-ai`

---

## 🏗️ Architecture AGI — Les 9 Couches

```
┌─────────────────────────────────────────────────────────────┐
│  COUCHE 0 — PERCEPTION MULTI-CANAL (Liquid Time Gateway)    │
│  Entrée unifiée tous canaux. Horloge interne. Pings async.  │
│  Stack : FastAPI gateway + UnifiedMessage + liquid_time.py  │
├─────────────────────────────────────────────────────────────┤
│  COUCHE 1 — LE RÉFLEXE (Semantic Cache)                     │
│  Requête → FastEmbed → Qdrant sim > 0.98 → Réponse directe  │
│  Stack : FastEmbed + Qdrant + cache_manager.py              │
├─────────────────────────────────────────────────────────────┤
│  COUCHE 2 — L'ÂME (Spreading Activation Graph)             │
│  Graphe causal Memgraph. Onde d'activation. Dérive détectée │
│  Stack : Memgraph Cypher + spreading_activation.py          │
├─────────────────────────────────────────────────────────────┤
│  COUCHE 3 — CERVEAU EXÉCUTIF (Agent Cascade + Bidding)      │
│  SAS → MAS conditionnel. Compute Bidding ROI (Phase 5)      │
│  Stack : xLAM-2 + OpenRouter + compute_bidding.py           │
├─────────────────────────────────────────────────────────────┤
│  COUCHE 4 — BOUCLIER FORMEL (Chain-of-Code + Red-Team)      │
│  Génère assertion Python. Exécute sandbox. Red-team local.  │
│  Stack : chain_of_code.py + DinD sandbox + Qwen 1.5B local  │
├─────────────────────────────────────────────────────────────┤
│  COUCHE 5 — TEST-TIME COMPUTE (Thinking Budget)             │
│  Budget tokens réflexion caché. Backtracking. MCTS.         │
│  Stack : thinking_budget.py + self_correction.py + mcts.py  │
├─────────────────────────────────────────────────────────────┤
│  COUCHE 6 — SYSTÈME NERVEUX AUTO-PLASTIQUE (MCP + Healing)  │
│  Exécution MCP. Auto-réparation si erreur. Patch à chaud.   │
│  Stack : MCP servers + debugger.py + patch_generator.py     │
├─────────────────────────────────────────────────────────────┤
│  COUCHE 7 — INFÉRENCE ACTIVE (Curiosité Intrinsèque)        │
│  Démon background. Minimise surprise. Teste hypothèses web. │
│  Stack : active_inference.py + hypothesis_tester.py         │
├─────────────────────────────────────────────────────────────┤
│  COUCHE 8 — SOMMEIL CONSTITUTIONNEL (Métabolisme Nocturne)  │
│  Ebbinghaus Decay. Synthetic DPO. DSPy prompt optimization. │
│  Stack : ebbinghaus_decay.py + synthetic_dpo.py + dspy      │
└─────────────────────────────────────────────────────────────┘
         ⟳ Boucle asynchrone : Couche 8 (nuit) + Couche 7 (background)
         ⟳ Boucle continue : succès → Couche 2 (mémoire) → Couche 1 (cache)
```

### Principes fondamentaux — Ne JAMAIS violer

1. **Preuve avant action** : Toute action irréversible (écrire, supprimer, envoyer) est prouvée par un test Python généré et exécuté en sandbox (Couche 4) avant validation.
2. **Asynchronisme absolu** : L'agent ne bloque jamais l'utilisateur. Si une tâche dure > 10s, Liquid Time envoie un update automatique toutes les 15s.
3. **Self-Healing > Exception** : Une erreur MCP ne s'expose jamais à l'utilisateur. Elle déclenche la boucle de réparation automatique (Couche 6).
4. **Cache avant LLM** : Toute requête passe d'abord par le Semantic Cache (Couche 1). Appel LLM uniquement si similarité < 0.98.
5. **SAS avant MAS** : Agent unique en premier. MAS uniquement si `confidence_score < 0.75`. Compute Bidding uniquement si `roi_score > 0.8` ET validation humaine (Phase 5).
6. **Secrets jamais en plaintext** : Infisical vault ou Docker Secrets. Zéro credential dans le repo Git.
7. **Modulaire < 600 lignes** : Aucun fichier Python ne dépasse 600 lignes. Découpe en modules si nécessaire.
8. **Consensus avant action critique** : Pour toute action irréversible à haut impact, 3 modèles différents (DeepSeek + Llama + Claude) doivent converger. Si désaccord → blocage automatique + notification user.
9. **Intent Tracking obligatoire** : Le graphe ne stocke jamais un fait isolé. Tout nœud de connaissance inclut un arc causal `MOTIVATES` vers un objectif utilisateur. Stocker le POURQUOI, pas juste le QUOI.

---

## 📁 Structure Exhaustive du Repo

```
world-ai/
├── CLAUDE.md                          # SOURCE DE VÉRITÉ — ce fichier
├── ARCHITECTURE.md                    # Détail technique de chaque couche
├── ROADMAP.md                         # Phases et milestones
├── CHANGELOG.md                       # Historique sessions
├── LICENSE                            # Apache 2.0
├── README.md                          # Documentation publique
├── .gitignore                         # Python, Node, .env, secrets
├── .env.example                       # Template sans valeurs
├── docker-compose.yml                 # Stack complète 1 commande
├── docker-compose.dev.yml             # Override dev local
│
├── core/                              # Moteur Central (Couches 1, 3, 5)
│   ├── cache/                         # Couche 1 — Réflexe Sémantique
│   │   ├── semantic_cache.py          # FastEmbed + Qdrant similarity check
│   │   └── cache_manager.py          # Invalidation TTL, stats
│   ├── router/                        # Couche 3 — Routage & Économie
│   │   ├── router.py                  # Logique routing (score → modèle)
│   │   ├── confidence.py              # Calcul entropie/complexité/domaine
│   │   ├── models.py                  # Slugs OpenRouter par tier
│   │   └── compute_bidding.py        # API RunPod — location GPU (Phase 5)
│   ├── analogie/                      # Couche 3 — Raisonnement Cross-Domaine
│   │   ├── blender.py                 # Recherche Qdrant forcée dans domaines NON-LIÉS
│   │   └── domain_mapper.py          # Mapping domaines : biologie, physique, urbanisme…
│   └── reasoning/                     # Couche 5 — Test-Time Compute
│       ├── thinking_budget.py         # Allocation tokens réflexion cachés
│       ├── self_correction.py         # Boucle backtracking interne
│       └── mcts.py                    # Monte Carlo Tree Search
│
├── soul/                              # Couche 2 — Âme & Graphe Causal
│   ├── graph/                         # Memgraph
│   │   ├── spreading_activation.py   # Onde activation (spanningTree Cypher)
│   │   ├── queries.py                 # CRUD Knowledge Graph causal
│   │   ├── schema.cypher              # Schéma ontologique utilisateur
│   │   └── concept_drift.py          # Détection contradictions/mise à jour
│   ├── vectors/                       # Qdrant
│   │   └── collections.py            # Collections : cache, mémoire, skills
│   └── profile/                       # Profil utilisateur
│       ├── extractor.py               # Extraction patterns conversations
│       ├── updater.py                 # Mise à jour graphe post-interaction
│       ├── cognitive_load.py         # Charge cognitive → seuil autonomie proactive
│       └── intent_tracker.py         # Modélise objectifs cachés derrière chaque demande
│
│   ── theory_of_mind/                 # Couche 2 — Simulateur Cognitif (Empathie)
│       ├── persona_cloner.py         # Clone modèle mental d'un interlocuteur externe
│       └── autonomy_gate.py          # Si cognitive_load > seuil → décision autonome minor
│
├── shield/                            # Couche 4 — Bouclier Formel
│   ├── verifier/                      # Chain-of-Code + Consensus Multi-Modèle
│   │   ├── chain_of_code.py          # Génère test Python pré-action critique
│   │   ├── formal_eval.py            # Exécute le test en sandbox DinD
│   │   └── multi_model_consensus.py  # 3 LLMs votent sur action critique (unanimité requise)
│   ├── adversary/                     # Red-Teaming local
│   │   ├── evaluator.py              # LLM 1B inspecte plan d'action (actions critical)
│   │   └── rules_engine.py           # Synalinks + Pydantic v2
│   └── schemas/                       # Schémas Pydantic par domaine
│       ├── email_action.py
│       ├── file_action.py
│       └── calendar_action.py
│
├── simulation/                        # Simulateur de Décision (Couche entre 4 et 6)
│   ├── rehearsal.py                   # Boucle répétition décision pré-exécution
│   ├── risk_classifier.py             # Classification: safe / risky / critical
│   └── summary_generator.py          # Résumé conséquences → confirmation user
│
├── nervous/                           # Couche 6 — Système Nerveux Auto-Plastique
│   ├── registry/                      # Registre MCP (catalogue connecteurs)
│   │   ├── registry.py               # Liste tous MCP + métadonnées + auth
│   │   ├── loader.py                  # Chargement dynamique MCP depuis registre
│   │   └── schemas/                   # Schémas JSON capacités par connecteur
│   ├── servers/                       # MCP Servers natifs (built-in)
│   │   ├── filesystem_mcp.py         # Fichiers (sandbox /data/user/)
│   │   ├── web_mcp.py                 # Brave search + fetch URL
│   │   ├── email_mcp.py              # IMAP/SMTP
│   │   ├── calendar_mcp.py           # Google Cal / Outlook / iCal
│   │   ├── browser_mcp.py            # Playwright automation
│   │   ├── notion_mcp.py             # Notion API
│   │   ├── github_mcp.py             # GitHub (issues, PRs)
│   │   ├── slack_mcp.py              # Slack (messages)
│   │   ├── gdrive_mcp.py             # Google Drive
│   │   ├── linear_mcp.py             # Linear PM
│   │   ├── airtable_mcp.py           # Airtable
│   │   ├── stripe_mcp.py             # Stripe (READ-ONLY toujours)
│   │   ├── postgres_mcp.py           # PostgreSQL (sandboxé)
│   │   └── custom_mcp.py             # Template connecteur custom
│   ├── connectors/                    # Connecteurs tiers standard
│   │   ├── connector_base.py         # BaseConnector : interface à implémenter
│   │   └── README.md                 # Guide ajout connecteur en 10 lignes
│   ├── healing/                       # Self-Healing Auto-Réparation
│   │   ├── debugger.py               # Try/Catch global → déclenche healing
│   │   ├── patch_generator.py        # LLM écrit patch Python depuis doc web
│   │   └── dind_sandbox.py           # Docker-in-Docker testing du patch
│   ├── synthesis/                     # Synthèse de NOUVEAUX outils MCP
│   │   ├── tool_synthesizer.py       # LLM génère un connecteur MCP entier de zéro
│   │   └── tool_validator.py         # Valide et teste le nouvel outil avant injection
│   └── gateway.py                    # Passerelle MCP centrale (routage + audit)
│
├── curiosity/                         # Couche 7 — Inférence Active
│   ├── active_inference.py           # Démon background : cherche surprises
│   └── hypothesis_tester.py          # Tests web autonomes des hypothèses
│
├── evolution/                         # Couche 8 — Sommeil & Évolution
│   ├── sleep/
│   │   ├── ebbinghaus_decay.py       # Décadence mémoires non-consultées
│   │   ├── synthetic_dpo.py          # Self-play : génère cas difficiles et se corrige
│   │   ├── dspy_optimizer.py         # Auto-rewrite prompts optimaux
│   │   └── prompt_library.py         # Dynamic Prompt Library — archive prompts gagnants
│   └── compiler/                      # Skill Compiler
│       ├── skill_compiler.py          # Tâche réussie → skill persistant
│       └── lora_trainer.py           # Interface RunPod LoRA fine-tuning
│
├── interfaces/                        # Couche 0 — Gateway Multi-Canal
│   ├── gateway/
│   │   ├── gateway.py                # FastAPI port 8100 — point d'entrée unifié
│   │   ├── message.py                # Type UnifiedMessage (format commun)
│   │   ├── liquid_time.py            # Pings async toutes les 15s si tâche longue
│   │   └── response_formatter.py    # Formate réponse selon canal d'origine
│   ├── adapters/                      # Un adapter par canal
│   │   ├── base_adapter.py           # BaseAdapter abstrait : receive/send/confirm
│   │   ├── telegram_adapter.py       # Telegram (python-telegram-bot v21)
│   │   ├── discord_adapter.py        # Discord (discord.py v2)
│   │   ├── slack_adapter.py          # Slack (slack-bolt)
│   │   ├── email_adapter.py          # Email IMAP/SMTP
│   │   ├── whatsapp_adapter.py       # WhatsApp (Twilio)
│   │   ├── webchat_adapter.py        # WebSocket port 8101
│   │   ├── voice_adapter.py          # Whisper STT + TTS local
│   │   ├── api_adapter.py            # REST public port 8102
│   │   └── imessage_adapter.py       # iMessage (AppleScript, macOS only)
│   ├── handlers/                      # Handlers partagés tous canaux
│   │   ├── text_handler.py
│   │   ├── voice_handler.py
│   │   ├── file_handler.py
│   │   └── confirmation_handler.py
│   └── web/                           # Interface Web Dify
│       └── README.md
│
├── n8n/                               # Workflows No-Code
│   ├── exports/
│   │   ├── main_orchestrator.json
│   │   ├── proactive_suggestions.json
│   │   ├── human_approval_gate.json
│   │   ├── cron_sleep_cycle.json      # Déclencheur Couche 8 (03:00 AM)
│   │   └── scheduled_tasks.json
│   └── README.md
│
├── config/
│   ├── settings.py                    # Pydantic-settings centralisées
│   └── logging.py                     # Structlog JSON → Langfuse
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── docs/
    ├── setup.md
    ├── api.md
    └── contributing.md
```

---

## 🔧 Stack Technique Complète

### Infrastructure
| Composant | Technologie | Notes |
|---|---|---|
| VPS permanent | Hetzner CX33 | 4 vCPU, 8GB RAM — stack 24/7 |
| Compute dynamique | RunPod API | Location GPU à la demande (Phase 5, ROI validé) |
| Container mgmt | Coolify | Web UI Docker management |
| Reverse proxy | Traefik v3 | SSL Let's Encrypt automatique |
| Secrets | Infisical self-hosted | Zéro plaintext, vault chiffré |
| Auto-Healing sandbox | Docker-in-Docker | Test des patches MCP avant déploiement |

### IA et Modèles
| Composant | Technologie | Couche | Notes |
|---|---|---|---|
| Agent principal | xLAM-2-7b-fc-r GGUF Q4 | 3 | Function-calling dédié |
| Inférence locale | llama.cpp / vLLM | 3 | Selon RAM disponible |
| Routeur LLM | OpenRouter API | 3 | 250+ modèles |
| LLM budget (70%) | DeepSeek V3.2 / Qwen3.5 | 3 | ~0.10-0.28$/M |
| LLM mid (20%) | Llama 4 Scout / Gemini Flash | 3 | ~0.25$/M |
| LLM frontier (10%) | Claude Opus 4.6 / GPT-5 | 3 | Cas critiques |
| LLM adversarial | Qwen 1.5B / 3B local | 4 | Red-Team local — actions critical |
| Embeddings cache | FastEmbed (BAAI/bge-small) | 1 | < 50ms, CPU-only |
| STT | Whisper medium local | 0 | Voix → texte |
| TTS | Coqui TTS / pyttsx3 | 0 | Texte → voix |

### Mémoire et Données
| Composant | Technologie | Port | Couche | Notes |
|---|---|---|---|---|
| Knowledge Graph | Memgraph | 7687 | 2 | Spreading Activation, Cypher |
| Vector store | Qdrant | 6333 | 1, 2 | Cache sémantique + RAG |
| Cache rapide | Redis | 6379 | 0 | Sessions, queues, état |
| Graph embedded | Kuzu | embedded | 2 | Fallback local léger |

### Orchestration et Interfaces
| Composant | Technologie | Port | Notes |
|---|---|---|---|
| Workflows | n8n | 5678 | Crons, webhooks, sleep cycle |
| Web UI | Dify | 3000 | Dashboard paramétrage |
| Observabilité | Langfuse self-hosted | 3001 | Tracing pensée complète |
| Gateway multi-canal | FastAPI | 8100 | Entrée unifiée tous canaux |
| Web Chat | WebSocket FastAPI | 8101 | Widget embeddable |
| REST public | FastAPI | 8102 | Intégrations tierces |

### Neuro-Symbolique
| Composant | Technologie | Notes |
|---|---|---|
| Couche symbolique | Synalinks | Keras-style, JSON-schema contraints |
| Validation | Pydantic v2 strict | Toute action validée avant exécution |
| Règles métier | Memgraph SPARQL | Depuis Knowledge Graph utilisateur |

---

## 🧪 Implémentations AGI Clés

### Couche 0 — Liquid Time (Conscience Temporelle)
```python
# interfaces/gateway/liquid_time.py
async def execute_with_pulse(
    task_coro: Coroutine,
    adapter: BaseAdapter,
    chat_id: str,
    pulse_interval: int = 15
) -> Any:
    """Envoie un update toutes les 15s si la tâche est longue."""
    task = asyncio.create_task(task_coro)
    elapsed = 0
    while not task.done():
        await asyncio.sleep(pulse_interval)
        elapsed += pulse_interval
        state = get_agent_thought_state()  # "Analyse du contexte...", "Vérification formelle..."
        await adapter.send(chat_id, f"⏳ [{elapsed}s] {state}")
    return await task
```

### Couche 1 — Semantic Cache (Réflexe Neuronal)
```python
# core/cache/semantic_cache.py
async def check_cache(query: str) -> CacheResult | None:
    """Bypass LLM total si requête similaire connue à > 98%."""
    embedding = await fast_embed(query)  # FastEmbed, < 50ms CPU
    results = await qdrant.search(
        collection="semantic_cache",
        query_vector=embedding,
        limit=1,
        score_threshold=0.98
    )
    if results:
        return CacheResult(response=results[0].payload["response"], hit=True)
    return None

async def store_in_cache(query: str, response: str) -> None:
    embedding = await fast_embed(query)
    await qdrant.upsert("semantic_cache", points=[
        PointStruct(id=uuid4(), vector=embedding, payload={"response": response})
    ])
```

### Couche 2 — Intent Tracking (Graphe Causal du POURQUOI)
```python
# soul/graph/schema.cypher — Ajout nœud Intent
# Format : (fact:Knowledge)-[:MOTIVATES]->(intent:Intent)-[:SERVES]->(goal:Goal)
# Exemple : (fait "Alexis aime Python")-[:MOTIVATES]->(intent "Productivité")-[:SERVES]->(goal "Lancer SaaS 2026")

# soul/profile/intent_tracker.py
async def extract_intent_from_request(message: str, user_history: list) -> IntentNode:
    """Déduit l'objectif DERRIÈRE la demande, pas juste la demande."""
    prompt = f"""
    Message: {message}
    Historique récent: {user_history[-5:]}
    Quelle est l'intention profonde derrière cette demande ?
    Quel objectif à long terme sert-elle ?
    Réponds au format JSON: {{"intent": str, "goal": str, "confidence": float}}
    """
    result = await llm.generate_json(prompt)
    return IntentNode(
        surface_request=message,
        intent=result["intent"],      # "Gagner du temps"
        goal=result["goal"],           # "Lancer son produit avant mars"
        confidence=result["confidence"]
    )
    # → Inséré dans Memgraph avec arc MOTIVATES entre le fait et l'intent
```

### Couche 2 — Persona Cloner (Simulateur d'Interlocuteur)
```python
# soul/theory_of_mind/persona_cloner.py
async def clone_persona(contact_id: str) -> PersonaModel:
    """Construit un modèle mental d'un interlocuteur externe pour le Self-Play MCTS."""
    # 1. Récupère l'historique des échanges avec ce contact
    history = await email_mcp.get_thread_history(contact_id)
    messages_from_contact = [m for m in history if m.sender == contact_id]
    # 2. Profile son style, ses objections habituelles, ses priorités
    analysis = await llm.generate(f"""
    Analyse ces {len(messages_from_contact)} messages de {contact_id}.
    Extrais: style de communication, objections fréquentes, valeurs,
    points de résistance, ce qui le convainc.
    Format JSON: {{style, objections[], values[], persuasion_triggers[]}}
    """)
    return PersonaModel(
        contact_id=contact_id,
        communication_style=analysis["style"],
        typical_objections=analysis["objections"],
        persuasion_triggers=analysis["persuasion_triggers"]
    )
    # → Utilisé par simulation/self_play/mcts.py pour simuler ses réactions
```

### Couche 3 — Analogie Cross-Domaine (Créativité par Association)
```python
# core/analogie/blender.py
UNRELATED_DOMAINS = ["biologie", "urbanisme", "thermodynamique", "jazz", "écologie", "marine"]

async def find_cross_domain_analogy(problem: str) -> list[AnalogyResult]:
    """Force la recherche de solutions dans des domaines intentionnellement non-liés."""
    results = []
    for domain in UNRELATED_DOMAINS[:3]:  # 3 domaines aléatoires
        # Recherche dans Qdrant restreinte au tag de ce domaine
        domain_docs = await qdrant.search(
            collection="knowledge_base",
            query_vector=embed(problem),
            filter={"domain": domain},
            limit=2
        )
        if domain_docs:
            # LLM forge l'analogie entre le domaine et le problème
            analogy = await llm.generate(f"""
            Problème à résoudre: {problem}
            Concept du domaine {domain}: {domain_docs[0].payload["summary"]}
            Comment ce concept du domaine {domain} pourrait-il inspirer une solution ?
            Sois créatif et concret.
            """)
            results.append(AnalogyResult(domain=domain, analogy=analogy, source=domain_docs[0]))
    return results
    # Exemple de sortie : "Et si on structurait ce réseau distribué comme le mycélium des champignons ?"
```

### Couche 4 — Consensus Multi-Modèle (Vote Unanime Critique)
```python
# shield/verifier/multi_model_consensus.py
CONSENSUS_MODELS = [
    "deepseek/deepseek-chat",       # Raisonnement
    "meta-llama/llama-4-scout",     # Équilibre vitesse/qualité
    "anthropic/claude-opus-4-6",    # Jugement final
]

async def require_consensus(action: MCPAction) -> ConsensusResult:
    """3 modèles différents doivent approuver. Désaccord = blocage automatique."""
    votes = []
    for model in CONSENSUS_MODELS:
        verdict = await openrouter.generate(
            model=model,
            prompt=f"""
            Évalue cette action irréversible:
            {action.model_dump_json()}
            Réponds UNIQUEMENT par: APPROVE ou REJECT + raison en 1 phrase.
            """,
            max_tokens=100
        )
        votes.append({"model": model, "vote": verdict})
    approvals = sum(1 for v in votes if "APPROVE" in v["vote"])
    if approvals < 3:  # Unanimité requise
        rejected_by = [v for v in votes if "REJECT" in v["vote"]]
        raise ConsensusRejected(
            action=action,
            votes=votes,
            reason=f"Blocage : {len(rejected_by)}/3 modèles ont refusé"
        )
    return ConsensusResult(approved=True, votes=votes)
```

### Couche 2 — Autonomie Proactive (Décision selon Charge Cognitive)
```python
# soul/theory_of_mind/autonomy_gate.py
AUTONOMY_THRESHOLDS = {
    "low_load": 0.3,      # User disponible → demande confirmation pour tout
    "medium_load": 0.6,   # User occupé → confirme uniquement risky et critical
    "high_load": 0.85,    # User en deep work → agit seul sur les actions "safe"
}

async def decide_autonomy_level(action: MCPAction, user_id: str) -> AutonomyDecision:
    """Adapte le niveau de sollicitation selon la charge cognitive détectée."""
    load = await cognitive_load.get_current(user_id)  # 0.0 → 1.0
    risk = action.risk_level  # safe / risky / critical
    
    if load > AUTONOMY_THRESHOLDS["high_load"] and risk == "safe":
        # User en deep work → exécuter silencieusement, log pour rapport
        return AutonomyDecision(ask_user=False, reason="User en deep work, action sûre")
    elif load > AUTONOMY_THRESHOLDS["medium_load"] and risk == "risky":
        # User occupé → envoyer résumé compact, pas de détail
        return AutonomyDecision(ask_user=True, format="compact")
    else:
        # User disponible → demande complète avec détails
        return AutonomyDecision(ask_user=True, format="full")
```

### Couche 2 — Paradigm Shift Notification (Concept Drift → Alerte)
```python
# soul/graph/concept_drift.py
async def detect_and_notify_paradigm_shift(user_id: str) -> list[ShiftAlert]:
    """Détecte les contradictions évolutives et alerte l'user pour validation."""
    # Cherche les tensions dans le graphe : ancien nœud vs comportement récent
    conflicts = memgraph.execute("""
        MATCH (old:Belief {user_id: $uid})-[:HELD_BY]->(u:User)
        MATCH (new:Observation {user_id: $uid, timestamp: > date() - duration("P14D")})
        WHERE old.value <> new.value AND old.topic = new.topic
        AND old.confidence > 0.7
        RETURN old, new, old.topic as topic
        LIMIT 5
    """, {"uid": user_id})
    
    alerts = []
    for conflict in conflicts:
        alert = ShiftAlert(
            topic=conflict["topic"],
            old_belief=conflict["old"]["value"],
            new_pattern=conflict["new"]["value"],
            message=f"💡 PARADIGM SHIFT DÉTECTÉ\n"
                    f"Ton rapport à '{conflict['topic']}' semble avoir évolué.\n"
                    f"Ancienne conviction : {conflict['old']['value']}\n"
                    f"Nouveau pattern observé : {conflict['new']['value']}\n"
                    f"Dois-je restructurer notre ontologie sur ce sujet ?\n"
                    f"[Oui, restructure ✅] [Non, garde l'ancien ❌] [Explique-moi 🔍]"
        )
        alerts.append(alert)
    return alerts
```

### Couche 8 — Dynamic Prompt Library (Contextual Forking)
```python
# evolution/sleep/prompt_library.py
async def update_winning_prompts():
    """Archive les prompts qui ont eu les meilleurs scores — alternative légère au LoRA."""
    # 1. Récupère les interactions du jour avec score de qualité > 0.85
    top_interactions = await langfuse.get_high_score_interactions(
        date=date.today(), min_score=0.85
    )
    # 2. Extrait les patterns de prompt gagnants
    for interaction in top_interactions:
        pattern = await llm.extract_prompt_pattern(
            system_prompt=interaction.system_prompt,
            user_message=interaction.input,
            response=interaction.output,
            score=interaction.quality_score
        )
        # 3. Archive dans la bibliothèque DSPy avec son contexte d'usage
        await prompt_library.store({
            "pattern": pattern,
            "context_tags": interaction.tags,  # ["code", "urgent", "technical"]
            "avg_score": interaction.quality_score,
            "usage_count": 1
        })
    # 4. Optimise via DSPy Teleprompter sur les patterns accumulés
    await dspy_optimizer.compile_from_library(prompt_library.get_top(n=20))
    # → Résultat : les system prompts s'améliorent chaque nuit sans LoRA
```
```python
# soul/graph/spreading_activation.py
def get_graph_context(entities: list[str]) -> SubgraphContext:
    """Réveille la zone mémoire liée — supérieur au RAG vectoriel pur."""
    query = """
    MATCH (start:Entity) WHERE start.name IN $entities
    CALL algo.bfs(start, {
        maxDepth: 3,
        weightProperty: 'synaptic_weight',
        filterExpression: 'n.synaptic_weight > 0.1'
    })
    YIELD path
    RETURN path
    ORDER BY path.totalWeight DESC
    LIMIT 50
    """
    results = memgraph.execute(query, {"entities": entities})
    return format_subgraph(results)
    # Retourne un contexte riche multi-nœuds, pas juste 1 document
```

### Couche 4 — Chain-of-Code (Preuve Formelle)
```python
# shield/verifier/chain_of_code.py
async def verify_before_execution(action: MCPAction) -> VerificationResult:
    """Génère et exécute un test Python avant toute action critique."""
    test_code = await llm.generate(f"""
    Write a safe pytest script to mock and verify this action:
    {action.model_dump_json()}
    The test must verify: preconditions, expected state change, rollback path.
    """)
    sandbox = DinDSandbox(timeout=30, network=False)
    result = await sandbox.run(test_code)
    if not result.success:
        raise FormalVerificationFailed(
            action=action,
            errors=result.errors,
            test_code=test_code
        )
    return VerificationResult(proven=True, test_code=test_code)
```

### Couche 4 — Red-Teaming Local (Actions Critical Seulement)
```python
# shield/adversary/evaluator.py
async def red_team_action_plan(plan: ActionPlan) -> RedTeamResult:
    """LLM 1B local inspecte le plan pour détecter jailbreaks/dérives."""
    # Activé UNIQUEMENT pour action.risk_level == "critical"
    adversarial_prompt = f"""
    You are a security auditor. Find vulnerabilities in this action plan:
    {plan.model_dump_json()}
    Look for: prompt injections, data exfiltration, unintended side effects.
    Respond with: SAFE or UNSAFE + reason.
    """
    result = await local_llm.generate(adversarial_prompt, model="qwen-1.5b")
    return RedTeamResult(safe=result.startswith("SAFE"), reason=result)
```

### Couche 6 — Self-Healing MCP (Auto-Réparation)
```python
# nervous/healing/debugger.py
async def execute_mcp_with_healing(tool: MCPTool, params: dict) -> ToolResult:
    """Erreur MCP → Recherche doc → Patch → Test DinD → Apply → Retry."""
    try:
        return await execute_tool(tool, params)
    except Exception as e:
        logger.warning(f"MCP error on {tool.name}: {e} — Starting self-healing")
        # 1. Cherche la doc à jour
        docs = await web_search(f"{tool.name} API documentation 2026 {type(e).__name__}")
        # 2. Génère le patch
        patch = await llm.generate(f"""
        Fix this tool code:
        Error: {e}
        Current code: {tool.source_code}
        Updated docs: {docs}
        Return ONLY the fixed Python function.
        """)
        # 3. Teste le patch en sandbox
        if await test_patch_in_dind(tool, patch, params):
            apply_hotfix(tool.name, patch)
            logger.info(f"Self-healing successful for {tool.name}")
            return await execute_tool(tool, params)  # Retry avec patch
        raise MCPHealingFailed(tool=tool.name, original_error=str(e))
```

### Couche 8 — Ebbinghaus Decay (Métabolisme Nocturne)
```python
# evolution/sleep/ebbinghaus_decay.py
def run_nightly_decay(decay_rate: float = 0.7):
    """Cron 03:00 AM — Refroidit les mémoires non-consultées (Ebbinghaus)."""
    # 1. Décadence des nœuds anciens
    memgraph.execute("""
        MATCH (n:Memory)
        WHERE n.last_accessed < date() - duration("P7D")
        SET n.synaptic_weight = n.synaptic_weight * $decay_rate
    """, {"decay_rate": decay_rate})
    # 2. Archive vers Qdrant cold storage si poids < seuil
    memgraph.execute("""
        MATCH (n:Memory) WHERE n.synaptic_weight < 0.1
        SET n.status = 'cold'
    """)
    cold_nodes = fetch_cold_nodes()
    for node in cold_nodes:
        qdrant.upsert("cold_memory", node.to_vector_point())
        memgraph.delete_node(node.id)

def run_synthetic_dpo():
    """Génère des cas difficiles depuis les logs du jour et auto-corrige."""
    todays_failures = fetch_low_confidence_interactions(date.today())
    for interaction in todays_failures:
        improved = llm.generate(f"Improve this response: {interaction}")
        store_dpo_pair(chosen=improved, rejected=interaction.response)
```

---

## 🌊 Roadmap AGI

### ✅ PHASE 00 — Initialisation (FAIT)
- [x] CLAUDE.md rédigé, architecture définie, stack choisie

### ✅ PHASE 01 partielle — Fondation Opérationnelle (EN COURS)
**Étape 1.1 — Infrastructure Docker** ✅
- [x] docker-compose.yml complet
- [x] docker-compose.dev.yml
- [x] .env.example
- [x] .gitignore
- [ ] Test : `docker-compose up -d` → tous services healthy

**Étape 1.2 — Routeur LLM Tiéré** ✅
- [x] core/router/models.py
- [x] core/router/confidence.py
- [x] core/router/router.py
- [x] config/settings.py
- [x] 29 tests unitaires — 100%

**Étape 1.3 — Agent Cascade (SAS)** ✅
- [x] core/cascade/agent.py
- [x] core/cascade/evaluator.py
- [x] core/cascade/types.py
- [x] core/cascade/openrouter.py
- [x] core/cascade/dispatcher.py
- [x] 41 tests unitaires — 100%

**Étape 1.4 — MCP Servers de base** ✅
- [x] nervous/servers/filesystem_mcp.py
- [x] nervous/servers/web_mcp.py
- [x] nervous/gateway.py
- [x] 80 tests unitaires — 100%

**Étape 1.5 — Gateway Multi-Canal (EN COURS)**

> Philosophie : UnifiedMessage normalisé → l'agent ignore le canal d'origine.
> Ajouter un canal = un seul adapter qui hérite de BaseAdapter.

- [ ] `interfaces/gateway/message.py` : UnifiedMessage (channel, user_id, content, attachments)
- [ ] `interfaces/adapters/base_adapter.py` : BaseAdapter abstrait
- [ ] `interfaces/gateway/liquid_time.py` : pings async toutes 15s si tâche > 10s
- [ ] `interfaces/gateway/gateway.py` : FastAPI port 8100
- [ ] `interfaces/gateway/response_formatter.py` : format selon canal
- [ ] `interfaces/adapters/telegram_adapter.py` : Telegram complet
- [ ] `interfaces/adapters/discord_adapter.py` : Discord
- [ ] `interfaces/adapters/slack_adapter.py` : Slack bolt
- [ ] `interfaces/adapters/email_adapter.py` : IMAP/SMTP async
- [ ] `interfaces/adapters/whatsapp_adapter.py` : Twilio stub
- [ ] `interfaces/adapters/webchat_adapter.py` : WebSocket port 8101
- [ ] `interfaces/adapters/voice_adapter.py` : Whisper STT + TTS
- [ ] `interfaces/adapters/api_adapter.py` : REST port 8102
- [ ] `interfaces/adapters/imessage_adapter.py` : AppleScript stub macOS
- [ ] `interfaces/handlers/text_handler.py`
- [ ] `interfaces/handlers/voice_handler.py`
- [ ] `interfaces/handlers/file_handler.py`
- [ ] `interfaces/handlers/confirmation_handler.py`
- [ ] Tests + git commit + push

**Étape 1.6 — Interface Web (Dify)**
- [ ] Dify dans docker-compose, app chat + paramétrage
- [ ] Connexion OpenRouter, page paramétrage modèle/seuil

**Étape 1.7 — Observabilité (Langfuse)**
- [ ] Instrumentation : modèle, latence, coût, score par appel
- [ ] Dashboard Langfuse accessible

**Étape 1.8 — Workflow n8n Principal**
- [ ] Workflow principal + export JSON
- [ ] Workflow cron sleep cycle (Couche 8, 03:00 AM)

---

### ⏳ PHASE 02 — RÉFLEXE & TEMPS LIQUIDE
**Objectif** : Zéro latence pour le connu. Conscience temporelle.

- [ ] `core/cache/semantic_cache.py` : FastEmbed + Qdrant sim > 0.98 → bypass LLM
- [ ] `core/cache/cache_manager.py` : TTL, invalidation, stats d'économie
- [ ] Injecter `current_time` et `last_interaction_delta` dans system prompt
- [ ] Liquid Time intégré dans toutes les tâches > 10s
- [ ] Test : requête répétée → hit cache, coût LLM = 0€

---

### ⏳ PHASE 03 — ÂME CAUSALE (Spreading Activation + Profil + Empathie)
**Objectif** : L'IA connaît l'utilisateur, pense par graphe causal, et s'adapte à son état cognitif.

- [ ] Memgraph + schéma ontologique avec nœuds `Intent` et `Goal` (schema.cypher)
- [ ] `soul/graph/spreading_activation.py` : onde activation Cypher avec poids synaptiques
- [ ] `soul/graph/concept_drift.py` : détection contradictions + notification Paradigm Shift
- [ ] `soul/profile/extractor.py` : extraction patterns auto depuis conversations
- [ ] `soul/profile/updater.py` : mise à jour graphe post-interaction
- [ ] `soul/profile/intent_tracker.py` : déduit le POURQUOI derrière chaque demande → arc MOTIVATES
- [ ] `soul/profile/cognitive_load.py` : charge cognitive (heure + fréquence + vitesse + contenu)
- [ ] `soul/theory_of_mind/autonomy_gate.py` : seuil autonomie proactive selon cognitive_load
- [ ] `soul/theory_of_mind/persona_cloner.py` : clone modèle mental interlocuteur externe
- [ ] `core/analogie/blender.py` : recherche Qdrant forcée dans domaines non-liés (biologie, physique…)
- [ ] `core/analogie/domain_mapper.py` : catalogue de domaines avec tags et embeddings
- [ ] Suggestions proactives via n8n Cron (pattern → proposition Telegram)
- [ ] Dashboard profil + Intent Map dans Dify

---

### ⏳ PHASE 04 — BOUCLIER FORMEL + TEST-TIME COMPUTE + CONSENSUS
**Objectif** : Fiabilité o1-style, sécurité formelle prouvée, vote multi-modèle.

- [ ] `core/reasoning/thinking_budget.py` : boucle réflexion cachée (Thought steps internes)
- [ ] `core/reasoning/self_correction.py` : backtracking si incohérence détectée
- [ ] `shield/verifier/chain_of_code.py` : assertion Python pré-action critique
- [ ] `shield/verifier/formal_eval.py` : exécution sandbox DinD
- [ ] `shield/verifier/multi_model_consensus.py` : vote unanime 3 LLMs pour actions critical
- [ ] `shield/adversary/evaluator.py` : Red-team Qwen 1.5B local (critical seulement)
- [ ] `simulation/rehearsal.py` : simulation + résumé conséquences avant exécution
- [ ] Gate confirmation multi-canal (Confirmer / Modifier / Annuler)
- [ ] Audit log complet dans Dify
- [ ] Note Phase 7+ : intégration solveurs SMT (Z3/Lean) pour preuve mathématique du code critique

---

### ⏳ PHASE 05 — SYSTÈME NERVEUX AUTO-PLASTIQUE (Self-Healing + Tool Synthesis)
**Objectif** : Zéro maintenance humaine sur les outils. L'IA crée ses propres connecteurs.

- [ ] `nervous/healing/debugger.py` : try/catch global → healing pipeline
- [ ] `nervous/healing/patch_generator.py` : LLM écrit patch depuis doc web
- [ ] `nervous/healing/dind_sandbox.py` : Docker-in-Docker test du patch
- [ ] `nervous/synthesis/tool_synthesizer.py` : LLM génère un MCP entier de zéro (ex: API météo non couverte)
- [ ] `nervous/synthesis/tool_validator.py` : valide + teste le nouvel outil avant injection dans registry
- [ ] MCP Connecteurs étendus : Notion, GitHub, Drive, Linear, Airtable
- [ ] `nervous/registry/registry.py` : catalogue dynamique connecteurs
- [ ] Test : provoquer une erreur MCP → observer auto-repair complet
- [ ] Test : demander un outil inexistant → observer tool_synthesizer créer le connecteur

---

### ⏳ PHASE 06 — INFÉRENCE ACTIVE + SOMMEIL CONSTITUTIONNEL
**Objectif** : Curiosité autonome + métabolisme nocturne + bibliothèque de prompts gagnants.

- [ ] `curiosity/active_inference.py` : démon background, minimise surprise (Free Energy)
- [ ] `curiosity/hypothesis_tester.py` : tests web autonomes des hypothèses
- [ ] `evolution/sleep/ebbinghaus_decay.py` : cron 03:00 AM decay + cold storage Qdrant
- [ ] `evolution/sleep/synthetic_dpo.py` : auto-génération cas difficiles + self-correction
- [ ] `evolution/sleep/dspy_optimizer.py` : recompilation prompts optimaux
- [ ] `evolution/sleep/prompt_library.py` : Dynamic Prompt Library — archive prompts gagnants du jour
- [ ] n8n workflow cron_sleep_cycle.json déclenche Couche 8

---

### ⏳ PHASE 07 — AUTO-ÉVOLUTION & COMPUTE BIDDING
**Objectif** : Fine-tuning personnel + location GPU conditionnelle.

- [ ] `evolution/compiler/skill_compiler.py` : succès → skill persistant
- [ ] `evolution/compiler/lora_trainer.py` : interface RunPod LoRA
- [ ] `core/router/compute_bidding.py` : calcul ROI → location H100 conditionnelle
- [ ] ⚠️ Compute Bidding : validation humaine OBLIGATOIRE avant tout achat GPU
- [ ] MCTS : `core/reasoning/mcts.py` pour exploration décisionnelle

---

## 🔒 Conventions de Code

### Python
- **Python 3.12** strictement. **Type hints partout**, sans exception.
- **Pydantic v2** pour toute validation. **async/await** pour tout I/O.
- **Structlog JSON** → Langfuse. `ruff` lint, `black` format.
- **Pytest** : couverture > 80% sur `core/` et `shield/`.
- **< 600 lignes par fichier** — découper en sous-modules si dépassement.

### Nommage
- Fichiers : `snake_case.py` | Classes : `PascalCase` | Constantes : `UPPER_SNAKE_CASE`
- Variables d'environnement : préfixe `WORLDAI_`

---

## ⚙️ Variables d'Environnement

```bash
# Infrastructure
WORLDAI_ENV=production
WORLDAI_MEMGRAPH_URI=bolt://memgraph:7687
WORLDAI_QDRANT_URL=http://qdrant:6333
WORLDAI_REDIS_URL=redis://redis:6379
WORLDAI_LANGFUSE_SECRET_KEY=
WORLDAI_LANGFUSE_PUBLIC_KEY=

# LLM & Modèles
WORLDAI_OPENROUTER_API_KEY=
WORLDAI_ANTHROPIC_API_KEY=
WORLDAI_LLM_BUDGET_MODEL=deepseek/deepseek-chat
WORLDAI_LLM_MID_MODEL=meta-llama/llama-4-scout
WORLDAI_LLM_FRONTIER_MODEL=anthropic/claude-opus-4-6
WORLDAI_XLAM_LOCAL_URL=http://localhost:8080
WORLDAI_ADVERSARIAL_LLM_URL=http://vllm-nano:8000   # Qwen 1.5B local Phase 4
WORLDAI_CONFIDENCE_THRESHOLD=0.75
WORLDAI_SIMULATION_THRESHOLD=0.40
WORLDAI_MAX_THINKING_TOKENS=15000                    # Phase 4 Test-Time Compute

# Semantic Cache (Phase 2)
WORLDAI_CACHE_SIMILARITY_THRESHOLD=0.98
WORLDAI_CACHE_TTL_HOURS=24

# Consensus Multi-Modèle (Phase 4)
WORLDAI_CONSENSUS_MODELS=deepseek/deepseek-chat,meta-llama/llama-4-scout,anthropic/claude-opus-4-6
WORLDAI_CONSENSUS_REQUIRED=3                    # Nombre de votes unanimes requis

# Autonomie Proactive (Phase 3)
WORLDAI_AUTONOMY_LOW_LOAD_THRESHOLD=0.3
WORLDAI_AUTONOMY_HIGH_LOAD_THRESHOLD=0.85
WORLDAI_AUTONOMY_ENABLED=true

# Analogie Cross-Domaine (Phase 3)
WORLDAI_ANALOGY_ENABLED=true
WORLDAI_ANALOGY_DOMAINS=biologie,urbanisme,thermodynamique,jazz,écologie,marine

# Dynamic Prompt Library (Phase 6)
WORLDAI_PROMPT_LIBRARY_MIN_SCORE=0.85
WORLDAI_PROMPT_LIBRARY_MAX_SIZE=500

# Tool Synthesis (Phase 5)
WORLDAI_TOOL_SYNTHESIS_ENABLED=true             # Création de nouveaux MCP from scratch

# Compute Bidding (Phase 7 — VALIDATION HUMAINE REQUISE)
WORLDAI_RUNPOD_API_KEY=
WORLDAI_MAX_BID_BUDGET_USD=5.00
WORLDAI_COMPUTE_BIDDING_ENABLED=false               # false jusqu'en Phase 7

# Ebbinghaus Decay (Phase 6)
WORLDAI_DECAY_RATE=0.7
WORLDAI_DECAY_THRESHOLD=0.1
WORLDAI_ENTROPY_THRESHOLD=0.6

# Canaux de communication
WORLDAI_TELEGRAM_BOT_TOKEN=
WORLDAI_DISCORD_BOT_TOKEN=
WORLDAI_DISCORD_GUILD_ID=
WORLDAI_SLACK_BOT_TOKEN=
WORLDAI_SLACK_SIGNING_SECRET=
WORLDAI_SLACK_APP_TOKEN=
WORLDAI_WHATSAPP_MODE=twilio
WORLDAI_TWILIO_ACCOUNT_SID=
WORLDAI_TWILIO_AUTH_TOKEN=
WORLDAI_TWILIO_WHATSAPP_NUMBER=
WORLDAI_EMAIL_IMAP_HOST=
WORLDAI_EMAIL_IMAP_PORT=993
WORLDAI_EMAIL_SMTP_HOST=
WORLDAI_EMAIL_SMTP_PORT=587
WORLDAI_EMAIL_ADDRESS=
WORLDAI_EMAIL_PASSWORD=
WORLDAI_IMESSAGE_ENABLED=false
WORLDAI_WEBCHAT_SECRET=
WORLDAI_API_PUBLIC_KEY=

# MCP Connecteurs
WORLDAI_MCP_ENABLED_SERVERS=filesystem,web,email,calendar,browser
WORLDAI_MCP_BRAVE_API_KEY=
WORLDAI_MCP_NOTION_TOKEN=
WORLDAI_MCP_GITHUB_TOKEN=
WORLDAI_MCP_GDRIVE_CREDENTIALS=
WORLDAI_MCP_LINEAR_API_KEY=
WORLDAI_MCP_AIRTABLE_API_KEY=
WORLDAI_MCP_STRIPE_SECRET_KEY=                      # READ-ONLY toujours
WORLDAI_MCP_POSTGRES_URL=
```

---

## 📡 Architecture Gateway Multi-Canal

```
Canal entrant (Telegram / Discord / Slack / Email / WhatsApp / Voice / Web / API)
        │
        ▼
┌─────────────────────────────────────────────┐
│  interfaces/gateway/gateway.py — port 8100  │
│  Reçoit webhook brut de chaque canal        │
└──────────────────┬──────────────────────────┘
                   │  via adapter.receive()
                   ▼
         UnifiedMessage {
           channel, user_id, content,
           attachments, reply_to,
           timestamp, session_id
         }
                   │
         ┌─────────▼─────────┐
         │  Liquid Time wrap │  → pulse async 15s si tâche longue
         └─────────┬─────────┘
                   │
         ┌─────────▼─────────┐
         │  Semantic Cache   │  → hit > 0.98 : réponse directe (Phase 2)
         └─────────┬─────────┘
                   │ miss
                   ▼
         core/cascade/agent.py → Spreading Activation → Shield → MCP
                   │
                   ▼
         response_formatter.py → format selon canal
                   │
         adapter.send() → Canal d'origine
```

---

## 🔌 Architecture MCP Universelle

```
nervous/registry/registry.py — Catalogue connecteurs
        │
        │  discover_tools() → liste outils actifs
        ▼
core/cascade/agent.py — "Quels outils ai-je ?"
        │
        │  execute_tool(name, params)
        ▼
nervous/gateway.py — Routage + audit + sandbox
        │
        ├── filesystem_mcp (stdio, sandbox)
        ├── web_mcp (HTTP, Brave API)
        ├── email_mcp (IMAP/SMTP)
        ├── notion_mcp (HTTP/OAuth)
        ├── github_mcp (HTTP/token)
        └── custom_mcp (template à étendre)
        │
        ↓ Si erreur → nervous/healing/ → Self-Healing pipeline
```

---

## 💬 Format Messages Multi-Canal

```
# Réponse standard
🤖 [Résumé action]
─────────────────────
📊 Modèle : DeepSeek V3 | Coût : ~0.001€ | Cache : ❌
⏱️ Temps : 1.2s | Confiance : 87% | Canal : Telegram

# Réponse depuis cache (Phase 2)
⚡ [Réponse instantanée]
─────────────────────
📊 Cache sémantique | Coût : 0€ | Similarité : 99.2%

# Liquid Time update
⏳ [45s] Vérification formelle de l'action en cours...

# Confirmation action risquée
⚠️ ACTION REQUISE
─────────────────────
Je vais envoyer l'email suivant :
À : jean@example.com | Objet : Rapport Q3
[Test formel : ✅ Prouvé]

[Confirmer ✅] [Modifier ✏️] [Annuler ❌]

# Suggestion proactive (Phase 3)
💡 SUGGESTION
─────────────────────
J'ai détecté un pattern : tu envoies ce rapport
chaque lundi depuis 3 semaines.
[Automatiser 🚀] [Non merci ✋]
```

---

## 📊 Métriques Langfuse (par interaction)

```python
{
    "model_used": str,               # Modèle sélectionné
    "cache_hit": bool,               # Semantic cache utilisé
    "cache_similarity": float,       # Score similarité cache
    "confidence_score": float,       # Score routing
    "thinking_tokens": int,          # Tokens réflexion cachés (Phase 4)
    "response_time_ms": int,
    "tokens_in": int,
    "tokens_out": int,
    "estimated_cost_eur": float,
    "action_risk_level": str,        # safe / risky / critical
    "formal_verified": bool,         # Chain-of-Code exécuté
    "red_team_passed": bool,         # Red-team local (si critical)
    "simulation_triggered": bool,
    "user_confirmed": bool,
    "healing_triggered": bool,       # Self-healing MCP activé
    "activation_nodes": int,         # Nœuds activés Spreading Activation
    "skill_compiled": bool,          # Nouveau skill créé
    "channel": str                   # Canal d'entrée
}
```

---

## 🚦 Instructions pour Claude Code

### Avant chaque session
1. Lire ce fichier intégralement
2. Identifier `🔄 EN COURS` et la première `[ ]` non cochée
3. Vérifier qu'aucune étape précédente n'est incomplète
4. Ne jamais sauter d'étape

### Pendant le développement
- **Un livrable à la fois** — commit après chaque fichier fonctionnel
- **< 600 lignes par fichier** — découper si nécessaire
- **Tests obligatoires** avant de cocher `[x]`
- **Type hints partout**, async pour tout I/O
- Ne jamais inventer de bibliothèques non listées ici
- Si doute architectural → arrêter et demander

### Après chaque étape
- Cocher `[ ]` → `[x]` dans ce fichier
- Ajouter entrée dans CHANGELOG.md
- `git commit -m "feat(couche): description"` + `git push`
- Si phase complète : `⏳` → `✅`

### Interdictions absolues
- ❌ Credentials dans le code ou le repo
- ❌ `WORLDAI_COMPUTE_BIDDING_ENABLED=true` sans validation humaine explicite
- ❌ Exposer stack traces à l'utilisateur final
- ❌ Fichier > 600 lignes
- ❌ Modifier l'architecture sans mettre à jour ce fichier

---

## 🔗 Ressources

| Ressource | URL |
|---|---|
| OpenRouter | https://openrouter.ai/docs |
| xLAM-2 | https://github.com/SalesforceAIResearch/xLAM |
| Memgraph Docs | https://memgraph.com/docs |
| Qdrant Docs | https://qdrant.tech/documentation |
| FastEmbed | https://github.com/qdrant/fastembed |
| Synalinks | https://github.com/SynaLinks/synalinks |
| LingBot-World | https://github.com/leofan90/awesome-world-models |
| n8n Docs | https://docs.n8n.io |
| Dify Docs | https://docs.dify.ai |
| Coolify | https://coolify.io/docs |
| Hetzner | https://www.hetzner.com/cloud |
| RunPod API | https://docs.runpod.io/api |
| python-telegram-bot | https://docs.python-telegram-bot.org |
| discord.py | https://discordpy.readthedocs.io |
| slack-bolt | https://slack.dev/bolt-python |
| Twilio WhatsApp | https://www.twilio.com/docs/whatsapp |
| aiosmtplib | https://aiosmtplib.readthedocs.io |
| Playwright Python | https://playwright.dev/python |
| Langfuse | https://langfuse.com/docs |
| OMI Open Source | https://github.com/BasedHardware/omi |
| MCP Protocol | https://modelcontextprotocol.io |
| MCP Servers | https://github.com/modelcontextprotocol/servers |
| DSPy | https://github.com/stanfordnlp/dspy |
| Coqui TTS | https://github.com/coqui-ai/TTS |

---

*Dernière mise à jour : Phase 01 partielle (1.1→1.4) · Architecture AGI 9 couches · Concepts Gemini intégrés (Intent Tracking, Persona Cloner, Analogie Cross-Domaine, Consensus Multi-Modèle, Autonomie Proactive, Paradigm Shift, Tool Synthesis, Dynamic Prompt Library, SMT Solvers Phase 7+)*
*Maintenu par : Alexis Druaux + Claude Code (Opus 4.6)*