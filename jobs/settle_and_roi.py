#!/usr/bin/env python3
"""Job: Settle picks and update bankroll/ROI."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import Database
from database.migrations import run_migrations
from bankroll.tracker import BankrollTracker
from discord_bot.webhook import send_settlement_to_discord, send_alert_to_discord
from config.config import DATABASE_PATH


def main():
    """Settle picks and update ROI."""
    print("💰 Starting settle_and_roi job...")

    try:
        # Ensure database exists
        run_migrations(DATABASE_PATH)

        # Initialize database and tracker
        db = Database(DATABASE_PATH)
        tracker = BankrollTracker(db)

        # Initialize today's bankroll if needed
        print("📊 Initializing bankroll...")
        tracker.initialize_bankroll()

        # Update bankroll (this settles picks automatically)
        print("\n💵 Settling picks and updating bankroll...")
        result = tracker.update_bankroll()

        print(f"\n✅ Settlement complete:")
        print(f"   Picks settled: {result['settled_picks']}")
        print(f"   Wins: {result['wins']}")
        print(f"   Losses: {result['losses']}")
        print(f"   P&L: {result['pnl']:+.2f}€")
        print(f"   ROI: {result['roi']:+.2f}%")
        print(f"   Bankroll: {result['bankroll_end']:.2f}€")

        # Send to Discord
        if result['settled_picks'] > 0:
            print("\n📤 Sending settlement summary to Discord...")
            send_settlement_to_discord(result)

    except Exception as e:
        print(f"❌ Job failed: {e}")
        import traceback
        traceback.print_exc()
        send_alert_to_discord(f"❌ settle_and_roi failed: {e}", "error")
        sys.exit(1)


if __name__ == "__main__":
    main()
