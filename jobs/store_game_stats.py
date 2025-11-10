#!/usr/bin/env python3
"""Job: Store yesterday's NHL game statistics from both NHL API and Moneypuck."""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import Database, GameStats
from database.migrations import run_migrations
from data.aggregator import DataAggregator
from discord_bot.webhook import send_alert_to_discord
from config.config import DATABASE_PATH


def main():
    """Store yesterday's game stats from both sources with validation."""
    print("🏒 Starting store_game_stats job (dual-source)...")

    try:
        # Ensure database exists
        run_migrations(DATABASE_PATH)

        # Initialize database
        db = Database(DATABASE_PATH)
        game_stats = GameStats(db)

        # Initialize aggregator (fetches from both sources)
        aggregator = DataAggregator()

        # Get yesterday's date
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        # Get validated and merged results
        print(f"📡 Fetching data from NHL API + Moneypuck for {yesterday}...")
        result = aggregator.get_games_with_validation(
            yesterday,
            prefer_source='nhl'  # Prefer NHL API for basic data
        )

        games = result['games']
        validation_report = result['validation_report']

        # Print validation report
        aggregator.validator.print_validation_report(validation_report)

        if not games:
            print("ℹ️ No games found yesterday")
            return

        # Store each game
        stored = 0
        for game in games:
            try:
                # Prepare meta data with advanced stats
                meta = game.get('meta', {})

                # Add data source info
                meta['data_source'] = game.get('data_source', 'unknown')
                meta['validated'] = game.get('validated', False)
                meta['available_in'] = game.get('available_in', {})

                # Add advanced stats if available
                if game.get('has_advanced_stats') and 'advanced_stats' in game:
                    meta['advanced_stats'] = game['advanced_stats']

                game_stats.create(
                    game_pk=game['game_pk'],
                    game_date=game['game_date'],
                    home_team=game['home_team'],
                    away_team=game['away_team'],
                    home_score=game['home_score'],
                    away_score=game['away_score'],
                    status=game['status'],
                    meta=meta
                )

                # Show storage confirmation
                xg_info = ""
                if game.get('has_advanced_stats'):
                    stats = game['advanced_stats']
                    xg_info = f" [xG: {stats['home_xG']:.2f}-{stats['away_xG']:.2f}]"

                print(f"  ✅ Stored: {game['away_team']} @ {game['home_team']} "
                      f"({game['away_score']}-{game['home_score']}){xg_info}")
                stored += 1

            except Exception as e:
                print(f"  ❌ Error storing game {game['game_pk']}: {e}")

        print(f"\n✅ Stored {stored}/{len(games)} games")

        # Build notification message
        message = f"✅ Stored {stored} games from {yesterday}\n"
        message += f"NHL API: {validation_report['nhl_count']} games\n"
        message += f"Moneypuck: {validation_report['mp_count']} games\n"
        message += f"Validated: {len(validation_report['validated_games'])}\n"

        if validation_report['status'] != 'OK':
            message += f"\n⚠️ Status: {validation_report['status']}"
            if validation_report['discrepancies']:
                message += f"\n❌ Discrepancies: {len(validation_report['discrepancies'])}"

        # Send notification
        if stored > 0:
            alert_level = "warning" if validation_report['status'] != 'OK' else "info"
            send_alert_to_discord(message, alert_level)

    except Exception as e:
        print(f"❌ Job failed: {e}")
        import traceback
        traceback.print_exc()
        send_alert_to_discord(f"❌ store_game_stats failed: {e}", "error")
        sys.exit(1)


if __name__ == "__main__":
    main()
