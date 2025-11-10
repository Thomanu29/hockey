#!/usr/bin/env python3
"""Job: Store yesterday's NHL game statistics."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import Database, GameStats
from database.migrations import run_migrations
from nhl_api.client import get_yesterday_results
from discord_bot.webhook import send_alert_to_discord
from config.config import DATABASE_PATH


def main():
    """Store yesterday's game stats."""
    print("🏒 Starting store_game_stats job...")

    try:
        # Ensure database exists
        run_migrations(DATABASE_PATH)

        # Initialize database
        db = Database(DATABASE_PATH)
        game_stats = GameStats(db)

        # Get yesterday's results
        print("📡 Fetching yesterday's results from NHL API...")
        results = get_yesterday_results()

        if not results:
            print("ℹ️ No games found yesterday")
            return

        # Store each game
        stored = 0
        for game in results:
            try:
                game_stats.create(
                    game_pk=game['game_pk'],
                    game_date=game['game_date'],
                    home_team=game['home_team'],
                    away_team=game['away_team'],
                    home_score=game['home_score'],
                    away_score=game['away_score'],
                    status=game['status'],
                    meta=game.get('meta', {})
                )
                print(f"  ✅ Stored: {game['away_team']} @ {game['home_team']} ({game['away_score']}-{game['home_score']})")
                stored += 1
            except Exception as e:
                print(f"  ❌ Error storing game {game['game_pk']}: {e}")

        print(f"\n✅ Stored {stored}/{len(results)} games")

        # Send success notification
        if stored > 0:
            send_alert_to_discord(
                f"✅ Stored {stored} game results from yesterday",
                "info"
            )

    except Exception as e:
        print(f"❌ Job failed: {e}")
        send_alert_to_discord(f"❌ store_game_stats failed: {e}", "error")
        sys.exit(1)


if __name__ == "__main__":
    main()
