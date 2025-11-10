"""Configuration management for NHL Automation System."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = os.getenv('DATABASE_PATH', str(BASE_DIR / 'nhl_automation.db'))

# Discord
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')
DISCORD_ALERT_WEBHOOK_URL = os.getenv('DISCORD_ALERT_WEBHOOK_URL', '')

# NHL API
NHL_API_BASE = 'https://api-web.nhle.com/v1'
NHL_SCHEDULE_ENDPOINT = f'{NHL_API_BASE}/schedule/{{date}}'
NHL_GAMECENTER_ENDPOINT = f'{NHL_API_BASE}/gamecenter/{{game_id}}/boxscore'
NHL_STANDINGS_ENDPOINT = f'{NHL_API_BASE}/standings/now'

# Bankroll settings
INITIAL_BANKROLL = float(os.getenv('INITIAL_BANKROLL', '1000.0'))
DEFAULT_STAKE_PERCENTAGE = float(os.getenv('DEFAULT_STAKE_PERCENTAGE', '2.0'))

# Model settings
MIN_EDGE_PERCENTAGE = float(os.getenv('MIN_EDGE_PERCENTAGE', '5.0'))
MIN_CONFIDENCE = int(os.getenv('MIN_CONFIDENCE', '6'))
MAX_PICKS_PER_REPORT = int(os.getenv('MAX_PICKS_PER_REPORT', '5'))

# Poisson model parameters
LOOKBACK_DAYS = 30  # Use last 30 days for training
HOME_ADVANTAGE_FACTOR = 1.15  # 15% home advantage

# Timezone
TIMEZONE = os.getenv('TIMEZONE', 'Europe/Paris')

# Report types
REPORT_TYPES = {
    'morning': {'emoji': '🌅', 'title': 'Morning Report'},
    'midday': {'emoji': '☀️', 'title': 'Midday Report'},
    'evening': {'emoji': '🌙', 'title': 'Evening Report'}
}
