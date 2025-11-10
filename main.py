#!/usr/bin/env python3
"""Main entry point for NHL Automation System."""
import sys
import argparse
from database.migrations import run_migrations
from database.models import Database
from bankroll.tracker import BankrollTracker
from config.config import DATABASE_PATH, INITIAL_BANKROLL


def setup():
    """Setup the system (database, initial bankroll)."""
    print("🏒 Setting up NHL Automation System...\n")

    # Run migrations
    print("📊 Creating database schema...")
    run_migrations(DATABASE_PATH)
    print(f"✅ Database created: {DATABASE_PATH}\n")

    # Initialize bankroll
    print("💰 Initializing bankroll...")
    db = Database(DATABASE_PATH)
    tracker = BankrollTracker(db)
    tracker.initialize_bankroll(INITIAL_BANKROLL)
    print(f"✅ Bankroll initialized: {INITIAL_BANKROLL}€\n")

    print("✅ Setup complete! You can now:")
    print("  - Run jobs: python jobs/store_game_stats.py")
    print("  - Generate reports: python jobs/generate_report.py morning")
    print("  - Check status: python main.py status")


def status():
    """Display system status."""
    print("🏒 NHL Automation System Status\n")

    try:
        db = Database(DATABASE_PATH)

        # Check database
        print("📊 Database:")
        print(f"  Path: {DATABASE_PATH}")

        # Check bankroll
        from database.models import BankrollState, GameStats, Pick
        bankroll_state = BankrollState(db)
        game_stats = GameStats(db)
        pick_model = Pick(db)

        latest_bankroll = bankroll_state.get_latest()
        if latest_bankroll:
            print(f"  Current bankroll: {latest_bankroll['bankroll_end']:.2f}€")
            print(f"  Latest ROI: {latest_bankroll['roi']:+.2f}%")
        else:
            print("  No bankroll data yet")

        # Check game stats
        recent_games = game_stats.get_recent_games(7)
        print(f"\n🏒 Games (last 7 days): {len(recent_games)}")

        # Check picks
        pending_picks = pick_model.get_pending_picks()
        print(f"📌 Pending picks: {len(pending_picks)}")

        # Check model
        from database.models import ModelPrediction
        model_pred = ModelPrediction(db)
        latest_model = model_pred.get_latest_by_scope('noon')
        if latest_model:
            print(f"\n🧠 Latest Model:")
            print(f"  λ_home: {latest_model['lambda_home']:.3f}")
            print(f"  λ_away: {latest_model['lambda_away']:.3f}")
            print(f"  Updated: {latest_model['created_at']}")
        else:
            print("\n🧠 No model trained yet")

        print("\n✅ System operational")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nRun 'python main.py setup' to initialize the system")


def test_api():
    """Test NHL API connection."""
    print("🏒 Testing NHL API...\n")

    from nhl_api.client import NHLAPIClient, get_yesterday_results

    client = NHLAPIClient()

    # Test yesterday's games
    print("📅 Yesterday's results:")
    results = get_yesterday_results()

    if not results:
        print("  No games yesterday (or API error)")
    else:
        for game in results:
            print(f"  {game['away_team']} @ {game['home_team']}: {game['away_score']}-{game['home_score']}")

    # Test today's schedule
    print("\n📅 Today's schedule:")
    today_games = client.get_today_games()

    if not today_games:
        print("  No games today")
    else:
        for game in today_games:
            result = client.parse_game_result(game)
            if result:
                status = result.get('status', 'Scheduled')
                print(f"  {result['away_team']} @ {result['home_team']} ({status})")

    print("\n✅ API test complete")


def test_discord():
    """Test Discord webhook."""
    print("🏒 Testing Discord webhook...\n")

    from discord_bot.webhook import DiscordNotifier

    notifier = DiscordNotifier()

    print("Sending test message...")
    success = notifier.send_message("🏒 NHL Automation System - Test Message")

    if success:
        print("✅ Discord webhook working!")
    else:
        print("❌ Discord webhook failed. Check your DISCORD_WEBHOOK_URL in .env")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='NHL Automation System')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Setup command
    subparsers.add_parser('setup', help='Setup the system (database, bankroll)')

    # Status command
    subparsers.add_parser('status', help='Display system status')

    # Test commands
    subparsers.add_parser('test-api', help='Test NHL API connection')
    subparsers.add_parser('test-discord', help='Test Discord webhook')

    args = parser.parse_args()

    if args.command == 'setup':
        setup()
    elif args.command == 'status':
        status()
    elif args.command == 'test-api':
        test_api()
    elif args.command == 'test-discord':
        test_discord()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
