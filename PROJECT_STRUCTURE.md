# 📁 Project Structure

## Overview

```
hockey/
├── 📄 Configuration & Documentation
│   ├── .env.example              # Environment variables template
│   ├── .env                      # Your local config (not in git)
│   ├── .gitignore               # Git ignore rules
│   ├── requirements.txt         # Python dependencies
│   ├── LICENSE                  # MIT License
│   ├── README.md                # Main documentation
│   ├── QUICKSTART.md            # Quick start guide
│   ├── STACK_COMPARISON.md      # Why this stack vs Supabase
│   └── PROJECT_STRUCTURE.md     # This file
│
├── 🔧 Core Application
│   ├── main.py                  # Main entry point (setup, status, tests)
│   └── config/
│       ├── __init__.py
│       └── config.py            # Configuration loader
│
├── 🗄️ Database Layer
│   └── database/
│       ├── __init__.py
│       ├── migrations.py        # Database schema creation
│       └── models.py            # ORM models (GameStats, Report, Pick, etc.)
│
├── 🏒 NHL API Client
│   └── nhl_api/
│       ├── __init__.py
│       └── client.py            # NHL Edge Stats API wrapper
│
├── 🧠 Machine Learning
│   └── models/
│       ├── __init__.py
│       └── poisson.py           # Poisson model for predictions
│
├── 📝 Reports System
│   └── reports/
│       ├── __init__.py
│       └── generator.py         # Report generator (morning/midday/evening)
│
├── 💰 Bankroll Management
│   └── bankroll/
│       ├── __init__.py
│       └── tracker.py           # Bankroll & ROI tracker
│
├── 💬 Discord Integration
│   └── discord_bot/
│       ├── __init__.py
│       └── webhook.py           # Discord webhook sender
│
├── ⚙️ Automation Jobs
│   └── jobs/
│       ├── __init__.py
│       ├── store_game_stats.py  # Fetch & store NHL results
│       ├── train_poisson.py     # Train Poisson model
│       ├── generate_report.py   # Generate reports
│       └── settle_and_roi.py    # Settle picks & update bankroll
│
└── 🤖 GitHub Actions
    └── .github/
        └── workflows/
            └── nhl_automation.yml  # Cron automation workflow
```

## File Descriptions

### Configuration Files

| File | Purpose |
|------|---------|
| `.env.example` | Template for environment variables |
| `.env` | Your local configuration (Discord URLs, etc.) |
| `requirements.txt` | Python dependencies (requests, scipy, etc.) |
| `.gitignore` | Files to ignore in git (*.db, .env, etc.) |

### Documentation

| File | Purpose |
|------|---------|
| `README.md` | Complete project documentation |
| `QUICKSTART.md` | 5-minute setup guide |
| `STACK_COMPARISON.md` | Why Python over Supabase |
| `PROJECT_STRUCTURE.md` | This file |
| `LICENSE` | MIT License |

### Core Application

| File | Lines | Purpose |
|------|-------|---------|
| `main.py` | ~150 | CLI entry point (setup, status, tests) |
| `config/config.py` | ~50 | Load environment variables & settings |

### Database Layer

| File | Lines | Purpose |
|------|-------|---------|
| `database/migrations.py` | ~100 | Create SQLite schema (5 tables, 1 view) |
| `database/models.py` | ~300 | ORM models for all tables |

**Tables created:**
- `game_stats` - NHL game results
- `reports_nhl` - Generated reports
- `reports_nhl_picks` - Picks with odds, edge, stake
- `model_predictions` - Poisson model parameters
- `bankroll_state` - Daily bankroll tracking

### NHL API Client

| File | Lines | Purpose |
|------|-------|---------|
| `nhl_api/client.py` | ~200 | Fetch games, scores, schedules from NHL API |

**Key functions:**
- `get_yesterday_results()` - Get finished games
- `get_today_schedule()` - Get upcoming games
- `parse_game_result()` - Parse API response

### Machine Learning

| File | Lines | Purpose |
|------|-------|---------|
| `models/poisson.py` | ~300 | Poisson distribution predictions |

**Key methods:**
- `train()` - Train on historical data
- `predict_game()` - Calculate probabilities & fair odds
- `find_value_bets()` - Detect edges > threshold

### Reports System

| File | Lines | Purpose |
|------|-------|---------|
| `reports/generator.py` | ~200 | Generate markdown reports |

**Report types:**
- Morning: Yesterday's ROI + results
- Midday: Today's value picks
- Evening: Updated picks

### Bankroll Management

| File | Lines | Purpose |
|------|-------|---------|
| `bankroll/tracker.py` | ~200 | Track bankroll, settle picks, calculate ROI |

**Key methods:**
- `settle_picks()` - Match picks with results
- `update_bankroll()` - Calculate daily P&L & ROI
- `get_performance_summary()` - Stats over N days

### Discord Integration

| File | Lines | Purpose |
|------|-------|---------|
| `discord_bot/webhook.py` | ~200 | Send messages to Discord |

**Message types:**
- Reports (with embeds)
- Settlement summaries
- Alerts (info/warning/error)

### Automation Jobs

| File | Lines | Purpose | Schedule |
|------|-------|---------|----------|
| `store_game_stats.py` | ~60 | Store yesterday's results | 06:50 Paris |
| `train_poisson.py` | ~50 | Train model | 12:00 Paris |
| `generate_report.py` | ~60 | Generate reports | 06:20, 12:05, 19:00 |
| `settle_and_roi.py` | ~50 | Settle picks & ROI | 07:00 Paris |

### GitHub Actions

| File | Lines | Purpose |
|------|-------|---------|
| `.github/workflows/nhl_automation.yml` | ~250 | Cron automation workflow |

**Jobs:**
- `store-game-stats` - Fetch & store NHL results
- `settle-and-roi` - Calculate daily ROI
- `morning-report` - Morning report
- `train-poisson` - Train model at noon
- `midday-report` - Midday picks
- `evening-report` - Evening update

## Data Flow

```
1. NHL API → store_game_stats.py → game_stats table
                                    ↓
2. game_stats → train_poisson.py → model_predictions
                                    ↓
3. model_predictions + today's schedule → generate_report.py → reports_nhl + picks
                                                                ↓
4. Discord Webhook ← reports/generator.py ← report content
                                                                ↓
5. game_stats + picks → settle_and_roi.py → bankroll_state
                                             ↓
6. Discord Webhook ← settlement summary
```

## Key Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Core language |
| SQLite | 3.x | Database |
| Scipy | 1.11+ | Poisson distributions |
| Numpy | 1.26+ | Numerical calculations |
| Requests | 2.31+ | HTTP API calls |
| Discord-Webhook | 1.3+ | Discord integration |
| GitHub Actions | - | Automation |

## Database Schema

### game_stats
```sql
id, game_pk (unique), game_date, home_team, away_team,
home_score, away_score, status, meta, created_at
```

### reports_nhl
```sql
id (uuid), type (morning/midday/evening), content, created_at
```

### reports_nhl_picks
```sql
id, report_id, label, market, odds, fair_odds, edge_pct,
confidence, result, stake, implied_prob, game_pk, meta,
created_at, settled_at
```

### model_predictions
```sql
id, model, scope, lambda_home, lambda_away, meta, created_at
```

### bankroll_state
```sql
date (pk), bankroll_start, bankroll_end, pnl, roi
```

## Lines of Code

```
Total Python: ~2,000 lines
Total Config: ~300 lines
Total Docs: ~1,500 lines
Total: ~3,800 lines
```

## Dependencies Size

```
Core dependencies: ~100MB
Total install: ~150MB
```

## Performance

- **Database queries**: <1ms (local SQLite)
- **API calls**: 200-500ms (NHL API)
- **Model training**: 50-100ms (30 games)
- **Report generation**: 100-200ms
- **Total job time**: 2-5 seconds

---

**Built with ❤️ for NHL betting automation**
