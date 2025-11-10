"""Discord webhook integration for NHL reports."""
import requests
from typing import Optional, Dict
from discord_webhook import DiscordWebhook, DiscordEmbed
from config.config import DISCORD_WEBHOOK_URL, DISCORD_ALERT_WEBHOOK_URL


class DiscordNotifier:
    """Send notifications to Discord via webhooks."""

    def __init__(self, webhook_url: str = DISCORD_WEBHOOK_URL):
        self.webhook_url = webhook_url
        self.alert_webhook_url = DISCORD_ALERT_WEBHOOK_URL

    def send_message(self, content: str, webhook_url: Optional[str] = None) -> bool:
        """
        Send a simple message to Discord.

        Args:
            content: Message content
            webhook_url: Optional custom webhook URL

        Returns:
            True if successful
        """
        url = webhook_url or self.webhook_url

        if not url:
            print("⚠️ No Discord webhook URL configured")
            return False

        try:
            webhook = DiscordWebhook(url=url, content=content)
            response = webhook.execute()

            if response.status_code == 200:
                print("✅ Message sent to Discord")
                return True
            else:
                print(f"❌ Discord error: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Failed to send Discord message: {e}")
            return False

    def send_report(self, report_content: str, report_type: str) -> bool:
        """
        Send NHL report to Discord with formatting.

        Args:
            report_content: Markdown report content
            report_type: Report type (morning/midday/evening)

        Returns:
            True if successful
        """
        if not self.webhook_url:
            print("⚠️ No Discord webhook URL configured")
            return False

        try:
            # Split content into chunks (Discord has 2000 char limit)
            chunks = self._split_content(report_content, 1900)

            for i, chunk in enumerate(chunks):
                webhook = DiscordWebhook(url=self.webhook_url)

                # Create embed for better formatting
                embed = DiscordEmbed(
                    title=f"NHL {report_type.title()} Report" + (f" (Part {i+1}/{len(chunks)})" if len(chunks) > 1 else ""),
                    description=chunk,
                    color=self._get_color_for_type(report_type)
                )

                embed.set_footer(text="HockeyChat NHL Automation")
                embed.set_timestamp()

                webhook.add_embed(embed)
                response = webhook.execute()

                if response.status_code != 200:
                    print(f"❌ Discord error: {response.status_code}")
                    return False

            print(f"✅ {report_type.title()} report sent to Discord")
            return True

        except Exception as e:
            print(f"❌ Failed to send report: {e}")
            return False

    def send_settlement_summary(self, summary: Dict) -> bool:
        """
        Send settlement summary to Discord.

        Args:
            summary: Settlement summary dictionary

        Returns:
            True if successful
        """
        settled = summary.get('settled_picks', 0)
        wins = summary.get('wins', 0)
        losses = summary.get('losses', 0)
        pnl = summary.get('pnl', 0)
        roi = summary.get('roi', 0)
        bankroll = summary.get('bankroll_end', 0)

        if settled == 0:
            return True  # No picks to report

        # Build message
        result_emoji = "📈" if pnl > 0 else "📉"
        win_rate = (wins / settled * 100) if settled > 0 else 0

        content = f"{result_emoji} **NHL Settlement Summary**\n\n"
        content += f"**Picks Settled**: {settled} ({wins}W-{losses}L)\n"
        content += f"**Win Rate**: {win_rate:.1f}%\n"
        content += f"**P&L**: {pnl:+.2f}€\n"
        content += f"**ROI**: {roi:+.2f}%\n"
        content += f"**Current Bankroll**: {bankroll:.2f}€\n"

        try:
            webhook = DiscordWebhook(url=self.webhook_url)

            embed = DiscordEmbed(
                title="💰 Daily Settlement",
                description=content,
                color='00ff00' if pnl > 0 else 'ff0000'
            )

            embed.set_footer(text="HockeyChat NHL Automation")
            embed.set_timestamp()

            webhook.add_embed(embed)
            response = webhook.execute()

            if response.status_code == 200:
                print("✅ Settlement summary sent to Discord")
                return True
            else:
                print(f"❌ Discord error: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Failed to send settlement: {e}")
            return False

    def send_alert(self, message: str, level: str = "info") -> bool:
        """
        Send alert message to alert webhook.

        Args:
            message: Alert message
            level: Alert level (info/warning/error)

        Returns:
            True if successful
        """
        url = self.alert_webhook_url or self.webhook_url

        if not url:
            print("⚠️ No Discord alert webhook configured")
            return False

        emoji_map = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '🚨'
        }

        color_map = {
            'info': '0099ff',
            'warning': 'ffaa00',
            'error': 'ff0000'
        }

        try:
            webhook = DiscordWebhook(url=url)

            embed = DiscordEmbed(
                title=f"{emoji_map.get(level, 'ℹ️')} {level.upper()}",
                description=message,
                color=color_map.get(level, '0099ff')
            )

            embed.set_footer(text="HockeyChat NHL Automation")
            embed.set_timestamp()

            webhook.add_embed(embed)
            response = webhook.execute()

            return response.status_code == 200

        except Exception as e:
            print(f"❌ Failed to send alert: {e}")
            return False

    def _split_content(self, content: str, max_length: int = 1900) -> list:
        """Split content into chunks that fit Discord's limits."""
        if len(content) <= max_length:
            return [content]

        chunks = []
        lines = content.split('\n')
        current_chunk = ""

        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _get_color_for_type(self, report_type: str) -> str:
        """Get embed color for report type."""
        colors = {
            'morning': 'ffa500',  # Orange
            'midday': 'ffff00',   # Yellow
            'evening': '4b0082'   # Indigo
        }
        return colors.get(report_type, '0099ff')


# Convenience functions
def send_report_to_discord(report_content: str, report_type: str) -> bool:
    """Send report to Discord."""
    notifier = DiscordNotifier()
    return notifier.send_report(report_content, report_type)


def send_settlement_to_discord(summary: Dict) -> bool:
    """Send settlement summary to Discord."""
    notifier = DiscordNotifier()
    return notifier.send_settlement_summary(summary)


def send_alert_to_discord(message: str, level: str = "info") -> bool:
    """Send alert to Discord."""
    notifier = DiscordNotifier()
    return notifier.send_alert(message, level)


if __name__ == "__main__":
    # Test Discord integration
    notifier = DiscordNotifier()

    print("Testing Discord webhook...")
    test_message = "🏒 NHL Automation System - Test Message"
    notifier.send_message(test_message)

    print("\nTesting alert...")
    notifier.send_alert("System initialized successfully", "info")
