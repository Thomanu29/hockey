"""Moneypuck API client for advanced NHL stats."""
import pandas as pd
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from io import StringIO


class MoneypuckClient:
    """Client for Moneypuck advanced hockey stats."""

    BASE_URL = "https://moneypuck.com/moneypuck"

    def __init__(self, season: str = "2024"):
        self.season = season
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'NHL-Automation/1.0'
        })

    def _get_csv(self, url: str) -> Optional[pd.DataFrame]:
        """Fetch CSV data from Moneypuck."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return pd.read_csv(StringIO(response.text))
        except requests.RequestException as e:
            print(f"❌ Moneypuck API Error: {e}")
            return None
        except Exception as e:
            print(f"❌ Error parsing Moneypuck CSV: {e}")
            return None

    def get_games_data(self) -> Optional[pd.DataFrame]:
        """
        Get game-by-game data including xG, scores, teams.

        Returns:
            DataFrame with columns:
            - game_id
            - gameDate
            - team
            - opposingTeam
            - home_or_away
            - goalsFor
            - goalsAgainst
            - xGoalsFor
            - xGoalsAgainst
            - corsiFor
            - corsiAgainst
            - etc.
        """
        url = f"{self.BASE_URL}/games/{self.season}/games.csv"
        return self._get_csv(url)

    def get_team_stats(self) -> Optional[pd.DataFrame]:
        """Get team-level aggregated stats."""
        url = f"{self.BASE_URL}/teams/{self.season}/regular/teams.csv"
        return self._get_csv(url)

    def get_goalie_stats(self) -> Optional[pd.DataFrame]:
        """Get goalie stats including GSAx (Goals Saved Above Expected)."""
        url = f"{self.BASE_URL}/goalies/{self.season}/regular/goalies.csv"
        return self._get_csv(url)

    def get_games_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        Get all games for a specific date from Moneypuck.

        Args:
            date: Date string in format YYYY-MM-DD

        Returns:
            List of game dictionaries with Moneypuck data
        """
        df = self.get_games_data()

        if df is None:
            return []

        # Filter by date
        df['gameDate'] = pd.to_datetime(df['gameDate']).dt.strftime('%Y-%m-%d')
        games_on_date = df[df['gameDate'] == date]

        if games_on_date.empty:
            return []

        # Group by game_id to get both teams' data
        games = []
        for game_id in games_on_date['game_id'].unique():
            game_data = games_on_date[games_on_date['game_id'] == game_id]

            # Get home and away rows
            home_row = game_data[game_data['home_or_away'] == 'HOME']
            away_row = game_data[game_data['home_or_away'] == 'AWAY']

            if home_row.empty or away_row.empty:
                continue

            home_row = home_row.iloc[0]
            away_row = away_row.iloc[0]

            games.append({
                'game_pk': int(game_id),
                'game_date': date,
                'home_team': str(home_row['team']),
                'away_team': str(away_row['team']),
                'home_score': int(home_row['goalsFor']),
                'away_score': int(away_row['goalsFor']),
                'status': 'Final',
                'source': 'moneypuck',
                'advanced_stats': {
                    'home_xG': float(home_row['xGoalsFor']),
                    'away_xG': float(away_row['xGoalsFor']),
                    'home_corsi': float(home_row.get('corsiFor', 0)),
                    'away_corsi': float(away_row.get('corsiFor', 0)),
                    'home_fenwick': float(home_row.get('fenwickFor', 0)),
                    'away_fenwick': float(away_row.get('fenwickFor', 0)),
                }
            })

        return games

    def get_finished_games(self, date: str) -> List[Dict[str, Any]]:
        """
        Get finished games for a date (same format as NHL API).

        Args:
            date: Date string in format YYYY-MM-DD

        Returns:
            List of parsed game results
        """
        return self.get_games_by_date(date)

    def get_team_recent_xg(self, team: str, days: int = 10) -> Dict[str, float]:
        """
        Get team's recent xG performance.

        Args:
            team: Team abbreviation
            days: Number of days to look back

        Returns:
            Dictionary with xGF, xGA averages
        """
        df = self.get_games_data()

        if df is None:
            return {'xGF': 0, 'xGA': 0, 'games': 0}

        # Filter team games in last N days
        df['gameDate'] = pd.to_datetime(df['gameDate'])
        cutoff = datetime.now() - timedelta(days=days)

        team_games = df[
            (df['team'] == team) &
            (df['gameDate'] >= cutoff)
        ]

        if team_games.empty:
            return {'xGF': 0, 'xGA': 0, 'games': 0}

        return {
            'xGF': float(team_games['xGoalsFor'].mean()),
            'xGA': float(team_games['xGoalsAgainst'].mean()),
            'games': len(team_games)
        }

    def get_goalie_gsax(self, goalie_name: str) -> Optional[float]:
        """
        Get goalie's Goals Saved Above Expected.

        Args:
            goalie_name: Goalie name

        Returns:
            GSAx value or None
        """
        df = self.get_goalie_stats()

        if df is None:
            return None

        goalie_data = df[df['name'] == goalie_name]

        if goalie_data.empty:
            return None

        return float(goalie_data.iloc[0].get('gsax', 0))


# Convenience functions
def get_yesterday_results() -> List[Dict[str, Any]]:
    """Get yesterday's game results from Moneypuck."""
    client = MoneypuckClient()
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    return client.get_finished_games(yesterday)


if __name__ == "__main__":
    # Test the Moneypuck client
    print("Testing Moneypuck API Client...")

    client = MoneypuckClient(season="2024")

    # Test yesterday's games
    print("\n📅 Yesterday's results from Moneypuck:")
    results = get_yesterday_results()

    if results:
        for game in results[:5]:  # Limit to 5 for readability
            print(f"\n  {game['away_team']} @ {game['home_team']}: {game['away_score']}-{game['home_score']}")
            if 'advanced_stats' in game:
                stats = game['advanced_stats']
                print(f"    xG: {stats['home_xG']:.2f} - {stats['away_xG']:.2f}")
    else:
        print("  No games found (might be off-season or API issue)")

    # Test team xG
    print("\n📊 Testing team xG (last 10 games):")
    xg_data = client.get_team_recent_xg('TOR', days=10)
    print(f"  Toronto: xGF={xg_data['xGF']:.2f}, xGA={xg_data['xGA']:.2f} ({xg_data['games']} games)")
