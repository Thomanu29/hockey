#!/usr/bin/env python3
"""Job: Train Poisson model on recent games."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import Database
from database.migrations import run_migrations
from models.poisson import PoissonModel
from discord_bot.webhook import send_alert_to_discord
from config.config import DATABASE_PATH, LOOKBACK_DAYS


def main():
    """Train Poisson model."""
    print("🧠 Starting train_poisson job...")

    try:
        # Ensure database exists
        run_migrations(DATABASE_PATH)

        # Initialize database and model
        db = Database(DATABASE_PATH)
        model = PoissonModel(db)

        # Train model
        print(f"📊 Training model on last {LOOKBACK_DAYS} days...")
        params = model.train(lookback_days=LOOKBACK_DAYS, scope='noon')

        lambda_home = params['lambda_home']
        lambda_away = params['lambda_away']

        print(f"\n✅ Model trained successfully")
        print(f"   λ_home: {lambda_home:.3f}")
        print(f"   λ_away: {lambda_away:.3f}")

        # Send notification
        send_alert_to_discord(
            f"🧠 Poisson model trained\n"
            f"λ_home: {lambda_home:.3f}\n"
            f"λ_away: {lambda_away:.3f}",
            "info"
        )

    except Exception as e:
        print(f"❌ Job failed: {e}")
        send_alert_to_discord(f"❌ train_poisson failed: {e}", "error")
        sys.exit(1)


if __name__ == "__main__":
    main()
