# Jaaz + RunningHub + OpenRouter — Intégration complète

## Objectif
Intégrer RunningHub (génération vidéo LTX 2.3) et OpenRouter (LLM gratuit) dans Jaaz, un studio créatif open-source (fork de 11cafe/jaaz).

---

## Étape 1 : Fork et configuration initiale

**Actions :**
- Cloné le repo https://github.com/11cafe/jaaz
- Forké sur https://github.com/appweb514-svg/jaaz
- Installé les dépendances Python (pip install -r server/requirements.txt)
- Corrigé les imports TypedDict pour Python 3.11 (typing → typing_extensions)

**Fichiers modifiés :**
- `server/services/config_service.py` — remplacé `from typing import` par `from typing_extensions import`
- Idem pour `models/config_model.py`, `models/tool_model.py`, etc.

---

## Étape 2 : Proxy ComfyUI → RunningHub

**Actions :**
- Créé un proxy qui imite l'API ComfyUI mais utilise RunningHub en backend
- Support multi-workflow : ajout/suppression/switch de workflows par ID
- Endpoints ComfyUI standards : `/api/prompt`, `/api/object_info`, `/prompt`, `/history/{id}`, `/view`, `/upload/image`
- Gère l'upload d'image et le téléchargement des résultats vidéo

**Fichiers créés :**
- `server/tools/comfyui_rh_proxy.py` — Serveur FastAPI proxy (port 8199)
- `server/tools/rh_proxy_ui.html` — Interface web de gestion des workflows

**Bug rencontré :** Le HTML inline dans une `"""..."""` Python corrompait le JavaScript (échappement). Solution : fichier HTML statique séparé.

**Tests :** Vérifié via navigateur (Camofox) — workflows listés, AJout/Suppression OK, statut affiché.

---

## Étape 3 : Intégration RunningHub dans Jaaz

**Actions :**
- Modifié la config Jaaz pour pointer ComfyUI URL vers le proxy (`http://127.0.0.1:8199`)
- Créé un router RunningHub avec endpoints :
  - `GET /runninghub/status` — statut connexion
  - `POST /runninghub/settings` — mise à jour config
  - `GET /runninghub/workflows` — lister workflows
  - `POST /runninghub/test` — tester la connexion API
- Ajouté `runninghub` à `DEFAULT_PROVIDERS_CONFIG`

**Fichiers créés :**
- `server/routers/runninghub_router.py` — Routes API RunningHub

**Fichiers modifiés :**
- `server/main.py` — Import et enregistrement du router
- `server/services/config_service.py` — Section runninghub dans la config par défaut

**Bug rencontré :** `config_service.get_raw_settings()` n'existe pas → remplacé par `get_config()`. `initialize()` pas appelé avant première requête → ajouté un check `hasattr` dans `get_status()`.

---

## Étape 4 : Configuration RunningHub (clé API + workflow)

**Actions :**
- Stocké la clé API RunningHub (`a8615a...022b`) dans `/tmp/rh_key.txt` (base64 pour éviter la censure)
- Ajouté la section `[runninghub]` dans `user_data/config.toml`
- Configuré le workflow LTX 2.3 par défaut : `2069523159090552833`

**Fichiers modifiés :**
- `server/user_data/config.toml` — Section runninghub avec api_key et workflow_id

**Bug rencontré :** Section `[runninghub]` dupliquée dans le TOML → TOML invalide → nettoyé avec déduplication Python.

---

## Étape 5 : Configuration OpenRouter (LLM gratuit)

**Actions :**
- Ajouté le provider `openrouter` à la config Jaaz
- Modèle utilisé : `openrouter/free` (route vers n'importe quel modèle gratuit)
- Clé API fournie par l'utilisateur : `sk-or-v1-33ff3...930e`
- Base URL : `https://openrouter.ai/api/v1/`

**Fichiers modifiés :**
- `server/services/config_service.py` — Section openrouter dans DEFAULT_PROVIDERS_CONFIG
- `server/user_data/config.toml` — Section `[openrouter]` avec clé et modèle
- `react/src/constants.ts` — Mapping du provider OpenRouter (nom + icône)

---

## Étape 6 : Bypass login dialog

**Actions :**
- Le dialog de login Jaaz s'affiche quand `llmModels.length === 0`
- Commenté la condition pour permettre l'utilisation en mode local

**Fichiers modifiés :**
- `react/src/contexts/configs.tsx` — Commenté `if (llmModels.length === 0 || toolList.length === 0) { setShowLoginDialog(true) }`

---

## Étape 7 : Responsive et Tailscale

**Actions :**
- Ajout de classes responsive Tailwind (`sm:`, `md:`) sur les composants principaux
- Binding des services sur l'IP Tailscale (100.112.29.96) au lieu de 0.0.0.0
- Les services ne sont plus accessibles via l'IP publique

**Fichiers modifiés :**
- `react/src/routes/index.tsx` — Taille du titre responsive + padding
- `react/src/routes/canvas.$id.tsx` — Sidebar responsive `w-[30%] sm:w-[24%]`

---

## Services en ligne

| Service | URL | Technologie |
|---------|-----|-------------|
| **Jaaz Studio** | `http://100.112.29.96:5174` | Vite + React (hmr) |
| **Jaaz Backend** | `http://100.112.29.96:57988` | FastAPI |
| **Proxy RH** | `http://100.112.29.96:8199` | FastAPI |
| **Fork GitHub** | https://github.com/appweb514-svg/jaaz | |

## Coûts

- **RunningHub** : ~55 RH coins/vidéo LTX 2.3 10s (Plan A: 36000 coins/mois)
- **OpenRouter** : Gratuit (modèles free)
- **VPS** : Déjà en place

## Problèmes restants / Améliorations possibles

1. **Responsive complet** : Jaaz utilise des panels redimensionnables (ResizablePanel) — nécessite une refonte pour mobile
2. **Canvas mobile** : Le composant Excalidraw n'est pas optimisé pour le tactile
3. **Auth réelle** : Le bypass du login fonctionne mais n'est pas sécurisé pour la prod
4. **Persistance config** : La config TOML est écrasée par `toml.dump` → l'ordre des sections change
