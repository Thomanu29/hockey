# 🚀 Quick Start Guide

## Installation en 5 minutes

### 1. Prérequis

```bash
# Python 3.11+
python3 --version

# Git
git --version
```

### 2. Installation

```bash
# Clone
git clone <your-repo>
cd hockey

# Install dependencies
pip install -r requirements.txt

# Copy config
cp .env.example .env
```

### 3. Configuration Discord

1. Aller sur Discord → Serveur → Paramètres du canal
2. Intégrations → Webhooks → Nouveau Webhook
3. Copier l'URL du webhook
4. Éditer `.env`:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN
```

### 4. Setup

```bash
python main.py setup
```

### 5. Test

```bash
# Test API NHL
python main.py test-api

# Test Discord
python main.py test-discord

# Test complet
python jobs/store_game_stats.py
python jobs/train_poisson.py
python jobs/generate_report.py midday
```

## 🎮 Utilisation Locale

### Workflow manuel quotidien

```bash
# Matin (après les matchs de la nuit)
python jobs/store_game_stats.py    # Sauvegarder résultats
python jobs/settle_and_roi.py       # Settlement + ROI
python jobs/generate_report.py morning

# Midi (avant les matchs)
python jobs/train_poisson.py        # Entraîner modèle
python jobs/generate_report.py midday

# Soir (dernières cotes)
python jobs/generate_report.py evening
```

### Vérifier le système

```bash
python main.py status
```

## ☁️ Déploiement GitHub Actions

### 1. Push sur GitHub

```bash
git add .
git commit -m "Initial commit NHL automation"
git push origin main
```

### 2. Configurer les secrets

Sur GitHub:
- Repo → Settings → Secrets and variables → Actions
- New repository secret:
  - Name: `DISCORD_WEBHOOK_URL`
  - Value: `https://discord.com/api/webhooks/...`

### 3. Activer Actions

- Actions → Enable workflows
- Le système tournera automatiquement selon le cron

### 4. Tester manuellement

- Actions → NHL Automation System
- Run workflow → Choisir `all` ou un job spécifique

## 📊 Horaire Automatique (Heure Paris)

| Heure | Job |
|-------|-----|
| 06:20 | Morning Report |
| 06:50 | Store Game Stats |
| 07:00 | Settle & ROI |
| 12:00 | Train Poisson Model |
| 12:05 | Midday Report |
| 19:00 | Evening Report |

## 🔧 Personnalisation

### Changer la bankroll initiale

Éditer `.env`:
```env
INITIAL_BANKROLL=2000.0
DEFAULT_STAKE_PERCENTAGE=1.5
```

### Changer les critères de value

Éditer `.env`:
```env
MIN_EDGE_PERCENTAGE=8.0    # Edge minimum 8%
MIN_CONFIDENCE=7           # Confidence minimum 7/10
MAX_PICKS_PER_REPORT=3     # Max 3 picks par rapport
```

### Changer les horaires

Éditer `.github/workflows/nhl_automation.yml`:

```yaml
on:
  schedule:
    - cron: '0 12 * * *'  # 13:00 Paris (UTC+1)
```

## 📱 Exemple de Rapport Discord

![Morning Report](https://via.placeholder.com/600x400?text=Morning+Report)

Contient:
- ROI yesterday
- Bankroll actuel
- Résultats d'hier

![Midday Report](https://via.placeholder.com/600x400?text=Midday+Report)

Contient:
- Value picks du jour
- Cotes + Edge %
- Confidence rating
- Stakes recommandés

## 🆘 Problèmes Courants

### Erreur: "No Discord webhook URL"

```bash
# Vérifier .env
cat .env | grep DISCORD_WEBHOOK_URL

# Ou exporter directement
export DISCORD_WEBHOOK_URL="https://..."
```

### Erreur: "No module named X"

```bash
pip install -r requirements.txt
```

### Base de données verrouillée

```bash
# Fermer tous les processus Python
pkill -9 python

# Réinitialiser
python main.py setup
```

### Pas de matchs

Normal si:
- NHL en pause (All-Star break, etc.)
- Pas de matchs hier/aujourd'hui
- API NHL temporairement down

### GitHub Actions ne démarre pas

1. Vérifier que Actions est activé (Settings → Actions)
2. Vérifier les secrets (Settings → Secrets)
3. Vérifier le fichier workflow (doit être dans `.github/workflows/`)

## 📚 Prochaines Étapes

1. **Monitorer pendant 1 semaine** pour vérifier que tout fonctionne
2. **Ajuster les paramètres** (edge, confidence, stake%)
3. **Intégrer vraies cotes** (Winamax/Betclic API) - v2.0
4. **Améliorer le modèle** (forme, goalies, HFA) - v2.0

## 🎓 Resources

- [NHL API Documentation](https://api-web.nhle.com/)
- [Discord Webhooks Guide](https://discord.com/developers/docs/resources/webhook)
- [GitHub Actions Cron Syntax](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)
- [Poisson Distribution](https://en.wikipedia.org/wiki/Poisson_distribution)

---

**Prêt à commencer!** 🚀

Pour toute question, ouvrir une issue sur GitHub.
