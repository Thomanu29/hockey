"""NHL API client using the new NHL Edge Stats API."""
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from config.config import NHL_API_BASE, NHL_SCHEDULE_ENDPOINT, NHL_GAMECENTER_ENDPOINT


class NHLAPIClient:
    """Client for NHL Edge Stats API."""

    def __init__(self):
        self.base_url = NHL_API_BASE
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'NHL-Automation/1.0'
        })

    def _get(self, url: str) -> Optional[Dict[str, Any]]:
        """Make GET request."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ API Error: {e}")
            return None

    def get_schedule(self, date: str) -> List[Dict[str, Any]]:
        """
        Get schedule for a specific date.

        Args:
            date: Date string in format YYYY-MM-DD

        Returns:
            List of game dictionaries
        """
        url = NHL_SCHEDULE_ENDPOINT.format(date=date)
        data = self._get(url)

        if not data or 'gameWeek' not in data:
            return []

        games = []
        for day in data.get('gameWeek', []):
            for game in day.get('games', []):
                games.append(game)

        return games

    def get_yesterday_games(self) -> List[Dict[str, Any]]:
        """Get yesterday's games."""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        return self.get_schedule(yesterday)

    def get_today_games(self) -> List[Dict[str, Any]]:
        """Get today's games."""
        today = datetime.now().strftime('%Y-%m-%d')
        return self.get_schedule(today)

    def get_game_details(self, game_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed game information including boxscore.

        Args:
            game_id: NHL game ID

        Returns:
            Game details dictionary
        """
        url = NHL_GAMECENTER_ENDPOINT.format(game_id=game_id)
        return self._get(url)

    def parse_game_result(self, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse game data into simplified result format.

        Args:
            game: Raw game data from API

        Returns:
            Simplified game result dictionary
        """
        try:
            if game.get('gameState') not in ['OFF', 'FINAL']:
                return None  # Game not finished

            home_team = game['homeTeam']['abbrev']
            away_team = game['awayTeam']['abbrev']
            home_score = game['homeTeam']['score']
            away_score = game['awayTeam']['score']
            game_pk = game['id']
            game_date = game['gameDate']

            # Parse game date to ISO format
            game_datetime = datetime.strptime(game_date, '%Y-%m-%dT%H:%M:%SZ')
            game_date_iso = game_datetime.strftime('%Y-%m-%d')

            return {
                'game_pk': game_pk,
                'game_date': game_date_iso,
                'home_team': home_team,
                'away_team': away_team,
                'home_score': home_score,
                'away_score': away_score,
                'status': 'Final',
                'meta': {
                    'gameType': game.get('gameType'),
                    'season': game.get('season'),
                    'venue': game.get('venue', {}).get('default'),
                }
            }
        except (KeyError, ValueError) as e:
            print(f"❌ Error parsing game: {e}")
            return None

    def get_finished_games(self, date: str) -> List[Dict[str, Any]]:
        """
        Get all finished games for a date.

        Args:
            date: Date string in format YYYY-MM-DD

        Returns:
            List of parsed game results
        """
        games = self.get_schedule(date)
        finished_games = []

        for game in games:
            result = self.parse_game_result(game)
            if result:
                finished_games.append(result)

        return finished_games

    def get_team_abbrev(self, team_name: str) -> str:
        """
        Convert team name to abbreviation.
        This is a basic mapping - extend as needed.
        """
        team_mapping = {
            'Boston Bruins': 'BOS',
            'Toronto Maple Leafs': 'TOR',
            'Tampa Bay Lightning': 'TBL',
            'Florida Panthers': 'FLA',
            'Montreal Canadiens': 'MTL',
            'Ottawa Senators': 'OTT',
            'Detroit Red Wings': 'DET',
            'Buffalo Sabres': 'BUF',
            'New York Rangers': 'NYR',
            'New York Islanders': 'NYI',
            'New Jersey Devils': 'NJD',
            'Philadelphia Flyers': 'PHI',
            'Pittsburgh Penguins': 'PIT',
            'Washington Capitals': 'WSH',
            'Carolina Hurricanes': 'CAR',
            'Columbus Blue Jackets': 'CBJ',
            'Nashville Predators': 'NSH',
            'Winnipeg Jets': 'WPG',
            'St. Louis Blues': 'STL',
            'Minnesota Wild': 'MIN',
            'Chicago Blackhawks': 'CHI',
            'Dallas Stars': 'DAL',
            'Colorado Avalanche': 'COL',
            'Arizona Coyotes': 'ARI',
            'Vegas Golden Knights': 'VGK',
            'Edmonton Oilers': 'EDM',
            'Calgary Flames': 'CGY',
            'Vancouver Canucks': 'VAN',
            'Seattle Kraken': 'SEA',
            'Los Angeles Kings': 'LAK',
            'Anaheim Ducks': 'ANA',
            'San Jose Sharks': 'SJS',
        }
        return team_mapping.get(team_name, team_name)


# Convenience functions
def get_yesterday_results() -> List[Dict[str, Any]]:
    """Get yesterday's game results."""
    client = NHLAPIClient()
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    return client.get_finished_games(yesterday)


def get_today_schedule() -> List[Dict[str, Any]]:
    """Get today's game schedule."""
    client = NHLAPIClient()
    return client.get_today_games()


if __name__ == "__main__":
    # Test the API
    print("Testing NHL API Client...")

    client = NHLAPIClient()

    # Test yesterday's games
    print("\n📅 Yesterday's results:")
    results = get_yesterday_results()
    for game in results:
        print(f"  {game['away_team']} @ {game['home_team']}: {game['away_score']}-{game['home_score']}")

    # Test today's schedule
    print("\n📅 Today's schedule:")
    schedule = get_today_schedule()
    for game in schedule:
        result = client.parse_game_result(game)
        if result:
            print(f"  {result['away_team']} @ {result['home_team']}")
