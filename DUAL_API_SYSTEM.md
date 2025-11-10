# 🔄 Système Dual-API: NHL + Moneypuck

## ✅ Ce qui a été implémenté

Votre système utilise maintenant **deux sources de données** pour maximiser la précision et la fiabilité:

### 1. **NHL Edge Stats API** (Officielle)
- ✅ Calendrier des matchs
- ✅ Scores finaux officiels
- ✅ Équipes, dates, statuts
- ✅ Temps réel

### 2. **Moneypuck** (Stats avancées)
- ✅ Expected Goals (xG)
- ✅ Corsi / Fenwick
- ✅ Stats gardiens (GSAx)
- ✅ Qualité du jeu

---

## 🏗️ Architecture

```
Récupération des données:
    │
    ├─→ NHL API Client (nhl_api/)
    │   └─ Scores, équipes, calendrier
    │
    └─→ Moneypuck Client (moneypuck_api/)
        └─ xG, Corsi, stats avancées

           ↓

Validation (data/validator.py)
    ├─ Compare les deux sources
    ├─ Détecte incohérences
    └─ Alerte Discord si problème

           ↓

Agrégation (data/aggregator.py)
    ├─ Fusionne les données
    ├─ Préfère NHL API pour scores
    └─ Ajoute stats Moneypuck

           ↓

Base de données
    ├─ Scores validés
    ├─ xG + stats avancées
    └─ Flags de validation

           ↓

Modèle Poisson v2
    ├─ Utilise xG au lieu de buts réels
    ├─ Plus précis
    └─ Meilleure prédiction
```

---

## 📁 Nouveaux fichiers créés

### 1. `nhl_api/client.py` (modifié)
- ✅ **Correction**: Filtre correctement par date exacte (au lieu de toute la semaine)
- Fonction: `get_schedule(date)` retourne SEULEMENT les matchs du jour demandé

### 2. `moneypuck_api/client.py` (nouveau)
```python
class MoneypuckClient:
    def get_games_by_date(date)          # Matchs avec xG
    def get_team_stats()                  # Stats équipes
    def get_goalie_stats()                # Stats gardiens
    def get_team_recent_xg(team, days)    # Forme récente (xG)
```

### 3. `data/validator.py` (nouveau)
```python
class DataValidator:
    def compare_games(nhl_games, mp_games)  # Compare les sources
    def _validate_single_game()              # Valide un match
    def _send_alert()                        # Alerte Discord
```

**Ce que le validator vérifie:**
- ✅ Scores identiques entre les deux sources
- ✅ Équipes identiques
- ✅ Dates identiques
- ⚠️ Alerte si discordances > 2 matchs

### 4. `data/aggregator.py` (nouveau)
```python
class DataAggregator:
    def get_games_with_validation()  # Récupère + valide
    def _merge_game_data()           # Fusionne intelligemment
```

**Stratégie de fusion:**
- Scores: **NHL API** (officiel)
- Stats avancées: **Moneypuck** (xG, Corsi)
- Validation: **Les deux** doivent matcher

### 5. `jobs/store_game_stats.py` (modifié)
- ✅ Utilise maintenant `DataAggregator` au lieu de juste NHL API
- ✅ Récupère données des **deux sources**
- ✅ **Valide** les données
- ✅ Sauvegarde **xG + stats avancées** dans meta
- ✅ **Alerte Discord** si discordances

### 6. `models/poisson.py` (modifié)
- ✅ Nouveau paramètre: `use_xg=True`
- ✅ Utilise **Expected Goals** (xG) au lieu de buts réels
- ✅ **Plus précis** pour prédictions
- ✅ Fallback automatique vers buts si pas de xG

---

## 🎯 Utilisation

### Test rapide du système

```powershell
cd C:\Users\thoma\hockey

# 1. Tester la validation des données
python data/validator.py

# 2. Tester l'agrégateur
python data/aggregator.py

# 3. Tester le client Moneypuck
python moneypuck_api/client.py

# 4. Tester le système complet
python jobs/store_game_stats.py
```

### Workflow quotidien (automatique)

Le système tourne automatiquement via GitHub Actions:

**Chaque matin à 06:50:**
```
1. Récupère matchs d'hier (NHL API)
2. Récupère xG d'hier (Moneypuck)
3. Valide les données (compare les deux)
4. Fusionne et sauvegarde
5. Alerte Discord si problème
```

**À 12:00 (training):**
```
1. Charge les matchs des 30 derniers jours
2. Extrait les xG de la base de données
3. Entraîne modèle Poisson avec xG
4. Sauvegarde λ_home et λ_away
```

**À 12:05 (prédictions):**
```
1. Charge le modèle (avec xG)
2. Prédit les matchs du jour
3. Calcule fair odds basées sur xG
4. Détecte value bets
5. Envoie rapport Discord
```

---

## 📊 Format des données enrichies

### Avant (v1):
```json
{
  "game_pk": 2025020252,
  "home_team": "NJD",
  "away_team": "NYI",
  "home_score": 3,
  "away_score": 2,
  "status": "Final"
}
```

### Après (v2 - Dual API):
```json
{
  "game_pk": 2025020252,
  "home_team": "NJD",
  "away_team": "NYI",
  "home_score": 3,
  "away_score": 2,
  "status": "Final",

  "data_source": "nhl_api",
  "validated": true,
  "has_advanced_stats": true,

  "available_in": {
    "nhl": true,
    "moneypuck": true
  },

  "advanced_stats": {
    "home_xG": 2.8,
    "away_xG": 2.3,
    "home_corsi": 58.2,
    "away_corsi": 41.8,
    "home_fenwick": 52.1,
    "away_fenwick": 47.9
  }
}
```

---

## 🔍 Validation Report Example

```
==============================================================
DATA VALIDATION REPORT - 2024-11-09
==============================================================

📊 Summary:
  NHL API games: 8
  Moneypuck games: 8
  Validated games: 8
  Status: OK

✅ All data sources match!
No discrepancies found.

==============================================================
```

**Si problème détecté:**
```
==============================================================
DATA VALIDATION REPORT - 2024-11-09
==============================================================

📊 Summary:
  NHL API games: 8
  Moneypuck games: 7
  Validated games: 7
  Status: WARNING

⚠️ Missing in Moneypuck (1):
    - Game 2025020255

❌ Data Discrepancies (1):
  Game 2025020252:
    home_score: NHL=3 vs MP=4    ← Différence!

==============================================================

→ Alerte Discord envoyée automatiquement
```

---

## 🧠 Modèle Poisson v2 (avec xG)

### Avant (v1):
```python
λ_home = moyenne(buts_domicile) × 1.15
λ_away = moyenne(buts_extérieur)
```

**Problème:** Les buts réels ont beaucoup de variance (luck)

### Après (v2 - avec xG):
```python
λ_home = moyenne(xG_domicile) × 1.15
λ_away = moyenne(xG_extérieur)
```

**Avantage:** xG représente la **qualité du jeu**, pas la chance

### Exemple concret:

**Match: TOR 2 vs MTL 5**

Avec buts réels (v1):
- Model pense que MTL joue beaucoup mieux
- λ = 5 buts/match pour MTL
- ❌ Mais peut-être c'était juste de la chance!

Avec xG (v2):
- xG_TOR = 3.2, xG_MTL = 2.8
- TOR a eu de meilleures chances mais n'a pas converti
- λ basé sur xG (plus précis)
- ✅ Modèle comprend la vraie qualité du jeu

---

## ⚡ Avantages du système dual-API

| Avantage | Explication |
|----------|-------------|
| **Fiabilité** | Double vérification des scores |
| **Précision** | xG > buts réels pour prédictions |
| **Redondance** | Fallback si une API est down |
| **Stats avancées** | Corsi, Fenwick, GSAx disponibles |
| **Validation** | Détection automatique d'erreurs |
| **Alertes** | Discord notifie si problème |

---

## 🚀 Prochaines améliorations possibles

### v2.1 (Court terme)
- [ ] Ajouter stats gardiens (GSAx) dans prédictions
- [ ] Pondérer par forme récente (10 derniers matchs)
- [ ] Ajuster λ selon le gardien titulaire

### v2.2 (Moyen terme)
- [ ] Intégration API Winamax (vraies cotes)
- [ ] Dashboard web pour visualiser xG
- [ ] Alertes en temps réel pendant les matchs

### v2.3 (Long terme)
- [ ] Machine Learning (XGBoost) au lieu de Poisson
- [ ] Prédictions joueur par joueur
- [ ] Modèle de contexte (rivalries, back-to-back, etc.)

---

## 🧪 Tests à faire

```powershell
# 1. Tester NHL API (correction filtre date)
python nhl_api/client.py

# 2. Tester Moneypuck
python moneypuck_api/client.py

# 3. Tester validation
python data/validator.py

# 4. Tester agrégation
python data/aggregator.py

# 5. Test complet (store + train + report)
python jobs/store_game_stats.py
python jobs/train_poisson.py
python jobs/generate_report.py midday
```

---

## 📞 Support

Si problème:
1. Vérifier logs dans PowerShell
2. Vérifier alertes Discord
3. Exécuter validation manuelle: `python data/validator.py`

---

**Votre système est maintenant 2x plus puissant avec la double validation!** 🚀

Données NHL officielles + Stats avancées Moneypuck = **Prédictions optimales** ⚽🎯
