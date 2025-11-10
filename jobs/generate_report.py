#!/usr/bin/env python3
"""Job: Generate NHL reports (morning/midday/evening)."""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import Database
from database.migrations import run_migrations
from reports.generator import ReportGenerator
from discord_bot.webhook import send_report_to_discord, send_alert_to_discord
from config.config import DATABASE_PATH


def main():
    """Generate and send report."""
    parser = argparse.ArgumentParser(description='Generate NHL report')
    parser.add_argument(
        'type',
        choices=['morning', 'midday', 'evening'],
        help='Report type to generate'
    )
    args = parser.parse_args()

    report_type = args.type

    print(f"📝 Starting generate_report job ({report_type})...")

    try:
        # Ensure database exists
        run_migrations(DATABASE_PATH)

        # Initialize database and generator
        db = Database(DATABASE_PATH)
        generator = ReportGenerator(db)

        # Generate report
        print(f"📊 Generating {report_type} report...")
        report = generator.generate_report(report_type)

        print(f"\n✅ Report generated:")
        print(f"   ID: {report['report_id']}")
        print(f"   Type: {report['type']}")
        if 'picks_count' in report:
            print(f"   Picks: {report['picks_count']}")

        # Send to Discord
        print("\n📤 Sending report to Discord...")
        success = send_report_to_discord(report['content'], report_type)

        if success:
            print("✅ Report sent to Discord successfully")
        else:
            print("⚠️ Failed to send report to Discord")

    except Exception as e:
        print(f"❌ Job failed: {e}")
        import traceback
        traceback.print_exc()
        send_alert_to_discord(f"❌ generate_report ({report_type}) failed: {e}", "error")
        sys.exit(1)


if __name__ == "__main__":
    main()
