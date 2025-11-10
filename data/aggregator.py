"""Data aggregator to merge NHL API and Moneypuck data."""
from typing import List, Dict, Any, Optional
from nhl_api.client import NHLAPIClient
from moneypuck_api.client import MoneypuckClient
from data.validator import DataValidator


class DataAggregator:
    """Aggregate and merge data from multiple sources."""

    def __init__(self):
        self.nhl_client = NHLAPIClient()
        self.mp_client = MoneypuckClient()
        self.validator = DataValidator()

    def get_games_with_validation(
        self,
        date: str,
        prefer_source: str = 'nhl'
    ) -> Dict[str, Any]:
        """
        Get games from both sources, validate, and return merged data.

        Args:
            date: Date string in format YYYY-MM-DD
            prefer_source: Which source to prefer for conflicts ('nhl' or 'moneypuck')

        Returns:
            Dictionary with:
            - games: List of merged game data
            - validation_report: Validation results
            - source_priority: Which source was preferred
        """
        print(f"📡 Fetching data for {date}...")

        # Fetch from both sources
        nhl_games = self.nhl_client.get_finished_games(date)
        mp_games = self.mp_client.get_finished_games(date)

        print(f"  NHL API: {len(nhl_games)} games")
        print(f"  Moneypuck: {len(mp_games)} games")

        # Validate
        validation_report = self.validator.compare_games(nhl_games, mp_games, date)

        # Merge data
        merged_games = self._merge_game_data(nhl_games, mp_games, prefer_source)

        return {
            'games': merged_games,
            'validation_report': validation_report,
            'source_priority': prefer_source,
            'date': date
        }

    def _merge_game_data(
        self,
        nhl_games: List[Dict[str, Any]],
        mp_games: List[Dict[str, Any]],
        prefer_source: str
    ) -> List[Dict[str, Any]]:
        """
        Merge game data from both sources.

        Strategy:
        1. Use preferred source for basic data (scores, teams)
        2. Always add Moneypuck advanced stats when available
        3. Mark data source for transparency
        """
        merged = []

        # Create lookup dicts
        nhl_dict = {g['game_pk']: g for g in nhl_games}
        mp_dict = {g['game_pk']: g for g in mp_games}

        # Get all unique game IDs
        all_game_pks = set(nhl_dict.keys()) | set(mp_dict.keys())

        for game_pk in all_game_pks:
            nhl_game = nhl_dict.get(game_pk)
            mp_game = mp_dict.get(game_pk)

            # Determine base game data
            if prefer_source == 'nhl' and nhl_game:
                base_game = nhl_game.copy()
                base_game['data_source'] = 'nhl_api'
            elif prefer_source == 'moneypuck' and mp_game:
                base_game = mp_game.copy()
                base_game['data_source'] = 'moneypuck'
            elif nhl_game:
                base_game = nhl_game.copy()
                base_game['data_source'] = 'nhl_api'
            elif mp_game:
                base_game = mp_game.copy()
                base_game['data_source'] = 'moneypuck'
            else:
                continue

            # Add advanced stats from Moneypuck if available
            if mp_game and 'advanced_stats' in mp_game:
                base_game['advanced_stats'] = mp_game['advanced_stats']
                base_game['has_advanced_stats'] = True
            else:
                base_game['has_advanced_stats'] = False

            # Add data availability flags
            base_game['available_in'] = {
                'nhl': nhl_game is not None,
                'moneypuck': mp_game is not None
            }

            # Add validation status
            if nhl_game and mp_game:
                base_game['validated'] = self._check_data_match(nhl_game, mp_game)
            else:
                base_game['validated'] = False

            merged.append(base_game)

        return merged

    def _check_data_match(self, game1: Dict, game2: Dict) -> bool:
        """Check if two game records match on key fields."""
        return (
            game1['home_team'] == game2['home_team'] and
            game1['away_team'] == game2['away_team'] and
            game1['home_score'] == game2['home_score'] and
            game1['away_score'] == game2['away_score']
        )

    def get_enriched_game(self, game_pk: int) -> Optional[Dict[str, Any]]:
        """
        Get a single game with all available data from both sources.

        Args:
            game_pk: NHL game ID

        Returns:
            Enriched game dictionary
        """
        # Get from NHL API
        nhl_game = self.nhl_client.get_game_details(game_pk)

        # Try to find in Moneypuck
        # (would need date to query efficiently)

        # For now, return NHL data
        return nhl_game

    def get_team_analysis(self, team: str, days: int = 10) -> Dict[str, Any]:
        """
        Get comprehensive team analysis from both sources.

        Args:
            team: Team abbreviation
            days: Days to look back

        Returns:
            Team analysis dictionary
        """
        # Get xG from Moneypuck
        xg_data = self.mp_client.get_team_recent_xg(team, days)

        return {
            'team': team,
            'period_days': days,
            'xG_data': xg_data,
            'source': 'moneypuck'
        }


def get_validated_games(date: str, prefer_nhl: bool = True) -> List[Dict[str, Any]]:
    """
    Convenience function to get validated games.

    Args:
        date: Date string YYYY-MM-DD
        prefer_nhl: Whether to prefer NHL API for conflicts

    Returns:
        List of validated and merged games
    """
    aggregator = DataAggregator()
    source = 'nhl' if prefer_nhl else 'moneypuck'

    result = aggregator.get_games_with_validation(date, prefer_source=source)

    # Print validation report
    aggregator.validator.print_validation_report(result['validation_report'])

    return result['games']


if __name__ == "__main__":
    # Test aggregator
    from datetime import datetime, timedelta

    aggregator = DataAggregator()

    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    print(f"Testing DataAggregator for {yesterday}...\n")

    result = aggregator.get_games_with_validation(yesterday, prefer_source='nhl')

    print(f"\n✅ Merged {len(result['games'])} games")

    # Show first game as example
    if result['games']:
        game = result['games'][0]
        print(f"\n📊 Example game:")
        print(f"  {game['away_team']} @ {game['home_team']}: {game['away_score']}-{game['home_score']}")
        print(f"  Data source: {game['data_source']}")
        print(f"  Validated: {game['validated']}")
        print(f"  Has advanced stats: {game.get('has_advanced_stats', False)}")

        if game.get('has_advanced_stats'):
            stats = game['advanced_stats']
            print(f"  Advanced stats:")
            print(f"    xG: {stats['home_xG']:.2f} - {stats['away_xG']:.2f}")
            print(f"    Corsi: {stats['home_corsi']:.0f} - {stats['away_corsi']:.0f}")
