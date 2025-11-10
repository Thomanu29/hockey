"""Data validator to compare NHL API and Moneypuck data."""
from typing import List, Dict, Any, Tuple
from discord_bot.webhook import send_alert_to_discord


class DataValidator:
    """Validate and compare data from multiple sources."""

    def __init__(self):
        self.discrepancies = []

    def compare_games(
        self,
        nhl_games: List[Dict[str, Any]],
        mp_games: List[Dict[str, Any]],
        date: str
    ) -> Dict[str, Any]:
        """
        Compare game data from NHL API and Moneypuck.

        Args:
            nhl_games: Games from NHL API
            mp_games: Games from Moneypuck
            date: Date being compared

        Returns:
            Validation report dictionary
        """
        report = {
            'date': date,
            'nhl_count': len(nhl_games),
            'mp_count': len(mp_games),
            'validated_games': [],
            'discrepancies': [],
            'missing_in_nhl': [],
            'missing_in_mp': [],
            'status': 'OK'
        }

        # Create lookup dicts by game_pk
        nhl_dict = {g['game_pk']: g for g in nhl_games}
        mp_dict = {g['game_pk']: g for g in mp_games}

        # Find games in both sources
        common_games = set(nhl_dict.keys()) & set(mp_dict.keys())

        # Check for missing games
        report['missing_in_mp'] = list(set(nhl_dict.keys()) - set(mp_dict.keys()))
        report['missing_in_nhl'] = list(set(mp_dict.keys()) - set(nhl_dict.keys()))

        # Validate common games
        for game_pk in common_games:
            nhl_game = nhl_dict[game_pk]
            mp_game = mp_dict[game_pk]

            validation = self._validate_single_game(nhl_game, mp_game)

            if validation['has_discrepancy']:
                report['discrepancies'].append(validation)
                report['status'] = 'WARNING'
            else:
                report['validated_games'].append(game_pk)

        # Alert if major issues
        if report['missing_in_nhl'] or len(report['discrepancies']) > 2:
            report['status'] = 'ERROR'
            self._send_alert(report)

        return report

    def _validate_single_game(
        self,
        nhl_game: Dict[str, Any],
        mp_game: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a single game between sources.

        Returns:
            Validation result with discrepancies
        """
        result = {
            'game_pk': nhl_game['game_pk'],
            'has_discrepancy': False,
            'issues': []
        }

        # Check teams
        if nhl_game['home_team'] != mp_game['home_team']:
            result['has_discrepancy'] = True
            result['issues'].append({
                'field': 'home_team',
                'nhl': nhl_game['home_team'],
                'mp': mp_game['home_team']
            })

        if nhl_game['away_team'] != mp_game['away_team']:
            result['has_discrepancy'] = True
            result['issues'].append({
                'field': 'away_team',
                'nhl': nhl_game['away_team'],
                'mp': mp_game['away_team']
            })

        # Check scores
        if nhl_game['home_score'] != mp_game['home_score']:
            result['has_discrepancy'] = True
            result['issues'].append({
                'field': 'home_score',
                'nhl': nhl_game['home_score'],
                'mp': mp_game['home_score']
            })

        if nhl_game['away_score'] != mp_game['away_score']:
            result['has_discrepancy'] = True
            result['issues'].append({
                'field': 'away_score',
                'nhl': nhl_game['away_score'],
                'mp': mp_game['away_score']
            })

        # Check date
        if nhl_game['game_date'] != mp_game['game_date']:
            result['has_discrepancy'] = True
            result['issues'].append({
                'field': 'game_date',
                'nhl': nhl_game['game_date'],
                'mp': mp_game['game_date']
            })

        return result

    def _send_alert(self, report: Dict[str, Any]):
        """Send Discord alert for data discrepancies."""
        message = f"⚠️ Data Validation Alert - {report['date']}\n\n"

        if report['missing_in_nhl']:
            message += f"Missing in NHL API: {len(report['missing_in_nhl'])} games\n"
            message += f"Game IDs: {report['missing_in_nhl'][:5]}\n\n"

        if report['missing_in_mp']:
            message += f"Missing in Moneypuck: {len(report['missing_in_mp'])} games\n"
            message += f"Game IDs: {report['missing_in_mp'][:5]}\n\n"

        if report['discrepancies']:
            message += f"Data Discrepancies: {len(report['discrepancies'])} games\n"
            for disc in report['discrepancies'][:3]:  # Show first 3
                message += f"\nGame {disc['game_pk']}:\n"
                for issue in disc['issues']:
                    message += f"  - {issue['field']}: NHL={issue['nhl']}, MP={issue['mp']}\n"

        send_alert_to_discord(message, "warning")

    def print_validation_report(self, report: Dict[str, Any]):
        """Print validation report to console."""
        print(f"\n{'='*60}")
        print(f"DATA VALIDATION REPORT - {report['date']}")
        print(f"{'='*60}")

        print(f"\n📊 Summary:")
        print(f"  NHL API games: {report['nhl_count']}")
        print(f"  Moneypuck games: {report['mp_count']}")
        print(f"  Validated games: {len(report['validated_games'])}")
        print(f"  Status: {report['status']}")

        if report['missing_in_mp']:
            print(f"\n⚠️ Missing in Moneypuck ({len(report['missing_in_mp'])}):")
            for game_pk in report['missing_in_mp'][:5]:
                print(f"    - Game {game_pk}")

        if report['missing_in_nhl']:
            print(f"\n⚠️ Missing in NHL API ({len(report['missing_in_nhl'])}):")
            for game_pk in report['missing_in_nhl'][:5]:
                print(f"    - Game {game_pk}")

        if report['discrepancies']:
            print(f"\n❌ Data Discrepancies ({len(report['discrepancies'])}):")
            for disc in report['discrepancies']:
                print(f"\n  Game {disc['game_pk']}:")
                for issue in disc['issues']:
                    print(f"    {issue['field']}: NHL={issue['nhl']} vs MP={issue['mp']}")

        print(f"\n{'='*60}\n")


if __name__ == "__main__":
    # Test validator
    from nhl_api.client import NHLAPIClient
    from moneypuck_api.client import MoneypuckClient
    from datetime import datetime, timedelta

    validator = DataValidator()

    # Get yesterday's data from both sources
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    print("Fetching data from both sources...")
    nhl_client = NHLAPIClient()
    mp_client = MoneypuckClient()

    nhl_games = nhl_client.get_finished_games(yesterday)
    mp_games = mp_client.get_finished_games(yesterday)

    print(f"NHL API: {len(nhl_games)} games")
    print(f"Moneypuck: {len(mp_games)} games")

    # Validate
    report = validator.compare_games(nhl_games, mp_games, yesterday)
    validator.print_validation_report(report)
