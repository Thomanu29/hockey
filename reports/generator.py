"""Report generator for NHL automation system."""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from database.models import Database, Report, Pick, BankrollState
from nhl_api.client import NHLAPIClient
from models.poisson import PoissonModel
from config.config import (
    REPORT_TYPES, MIN_EDGE_PERCENTAGE, MIN_CONFIDENCE,
    MAX_PICKS_PER_REPORT, DEFAULT_STAKE_PERCENTAGE
)


class ReportGenerator:
    """Generate NHL betting reports."""

    def __init__(self, db: Database):
        self.db = db
        self.report = Report(db)
        self.pick_model = Pick(db)
        self.bankroll_state = BankrollState(db)
        self.nhl_api = NHLAPIClient()
        self.poisson_model = PoissonModel(db)

    def generate_morning_report(self) -> Dict:
        """Generate morning report with yesterday's results and ROI."""
        report_type = 'morning'
        emoji = REPORT_TYPES[report_type]['emoji']

        # Get yesterday's ROI
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        bankroll = self.bankroll_state.get_by_date(yesterday)

        # Get current bankroll
        current_bankroll = self.bankroll_state.get_latest()
        bankroll_amount = current_bankroll['bankroll_end'] if current_bankroll else 0

        # Build report content
        content = f"# {emoji} NHL — Morning Report\n\n"

        if bankroll:
            roi = bankroll['roi']
            pnl = bankroll['pnl']
            content += f"## 📊 Yesterday's Performance\n"
            content += f"- **ROI**: {roi:+.2f}%\n"
            content += f"- **P&L**: {pnl:+.2f}€\n"
            content += f"- **Current Bankroll**: {bankroll_amount:.2f}€\n\n"
        else:
            content += f"## 📊 Current Status\n"
            content += f"- **Bankroll**: {bankroll_amount:.2f}€\n\n"

        # Get yesterday's results
        yesterday_games = self.nhl_api.get_finished_games(yesterday)

        if yesterday_games:
            content += "## 🏒 Yesterday's Results\n"
            for game in yesterday_games[:10]:  # Limit to 10 games
                away = game['away_team']
                home = game['home_team']
                away_score = game['away_score']
                home_score = game['home_score']
                content += f"- **{away}** {away_score} @ **{home}** {home_score}\n"
        else:
            content += "## 🏒 No games yesterday\n"

        content += f"\n---\n*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M')}*"

        # Save report
        report_id = self.report.create(report_type, content)

        return {
            'report_id': report_id,
            'type': report_type,
            'content': content
        }

    def generate_midday_report(self) -> Dict:
        """Generate midday report with predictions and value picks."""
        report_type = 'midday'
        emoji = REPORT_TYPES[report_type]['emoji']

        # Load model
        if not self.poisson_model.load_latest_model(scope='noon'):
            # Train if no model exists
            self.poisson_model.train(scope='noon')

        # Get today's games
        today = datetime.now().strftime('%Y-%m-%d')
        today_games = self.nhl_api.get_schedule(today)

        # Generate predictions
        predictions = []
        for game in today_games:
            result = self.nhl_api.parse_game_result(game)
            if result and result['status'] != 'Final':
                # Game hasn't started
                pred = self.poisson_model.predict_game(
                    result['home_team'],
                    result['away_team']
                )
                pred['game_pk'] = result['game_pk']
                predictions.append(pred)

        # Mock odds (in production, get from Winamax/Betclic API)
        mock_odds = self._generate_mock_odds(predictions)

        # Find value bets
        value_bets = self.poisson_model.find_value_bets(
            predictions,
            mock_odds,
            min_edge=MIN_EDGE_PERCENTAGE
        )

        # Filter by confidence
        value_bets = [bet for bet in value_bets if bet['confidence'] >= MIN_CONFIDENCE]

        # Limit picks
        value_bets = value_bets[:MAX_PICKS_PER_REPORT]

        # Calculate stakes
        current_bankroll = self.bankroll_state.get_latest()
        bankroll_amount = current_bankroll['bankroll_end'] if current_bankroll else 1000

        for bet in value_bets:
            bet['stake'] = bankroll_amount * (DEFAULT_STAKE_PERCENTAGE / 100)

        # Build report content
        content = f"# {emoji} NHL — Midday Report\n\n"

        if value_bets:
            content += f"## 🎯 Value Picks ({len(value_bets)})\n\n"

            for i, bet in enumerate(value_bets, 1):
                content += f"### {i}. {bet['label']}\n"
                content += f"- **Market**: {bet['market'].title()}\n"
                content += f"- **Odds**: {bet['odds']:.2f}\n"
                content += f"- **Fair Odds**: {bet['fair_odds']:.2f}\n"
                content += f"- **Edge**: +{bet['edge_pct']:.1f}%\n"
                content += f"- **Confidence**: {bet['confidence']}/10\n"
                content += f"- **Stake**: {bet['stake']:.2f}€\n\n"

            avg_confidence = sum(b['confidence'] for b in value_bets) / len(value_bets)
            content += f"## ⭐ Model Grade: {avg_confidence:.1f}/10\n\n"
        else:
            content += "## 🚫 No value picks today\n\n"
            content += "No bets meet our minimum edge and confidence criteria.\n\n"

        content += f"---\n*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M')}*"

        # Save report and picks
        report_id = self.report.create(report_type, content)

        # Save picks
        for bet in value_bets:
            # Find game_pk for this bet
            game_pk = None
            for pred in predictions:
                if bet['team'] in [pred['home_team'], pred['away_team']]:
                    game_pk = pred.get('game_pk')
                    break

            self.pick_model.create(
                report_id=report_id,
                label=bet['label'],
                market=bet['market'],
                odds=bet['odds'],
                fair_odds=bet['fair_odds'],
                edge_pct=bet['edge_pct'],
                confidence=bet['confidence'],
                stake=bet['stake'],
                implied_prob=bet['implied_prob'],
                game_pk=game_pk,
                meta={'report_type': report_type}
            )

        return {
            'report_id': report_id,
            'type': report_type,
            'content': content,
            'picks_count': len(value_bets)
        }

    def generate_evening_report(self) -> Dict:
        """Generate evening report with last-minute analysis."""
        report_type = 'evening'
        emoji = REPORT_TYPES[report_type]['emoji']

        # Similar to midday but with updated odds/analysis
        # For now, reuse midday logic
        result = self.generate_midday_report()
        result['type'] = report_type

        # Update content header
        content = result['content'].replace('Midday Report', 'Evening Report')
        content = content.replace('☀️', emoji)

        # Update report
        report_id = self.report.create(report_type, content)
        result['report_id'] = report_id
        result['content'] = content

        return result

    def _generate_mock_odds(self, predictions: List[Dict]) -> Dict[str, float]:
        """
        Generate mock market odds for testing.
        In production, replace with real odds from Winamax/Betclic API.
        """
        mock_odds = {}

        for pred in predictions:
            home = pred['home_team']
            away = pred['away_team']

            # Add some variance to fair odds to simulate market
            variance = 0.15  # 15% variance

            import random
            mock_odds[f"{home}_ML"] = pred['fair_home_ml'] * random.uniform(1 - variance, 1 + variance)
            mock_odds[f"{away}_ML"] = pred['fair_away_ml'] * random.uniform(1 - variance, 1 + variance)
            mock_odds[f"{home}_O5.5"] = pred['fair_over_5_5'] * random.uniform(1 - variance, 1 + variance)
            mock_odds[f"{home}_U5.5"] = pred['fair_under_5_5'] * random.uniform(1 - variance, 1 + variance)

        return mock_odds

    def generate_report(self, report_type: str) -> Dict:
        """
        Generate report by type.

        Args:
            report_type: 'morning', 'midday', or 'evening'

        Returns:
            Report dictionary
        """
        if report_type == 'morning':
            return self.generate_morning_report()
        elif report_type == 'midday':
            return self.generate_midday_report()
        elif report_type == 'evening':
            return self.generate_evening_report()
        else:
            raise ValueError(f"Invalid report type: {report_type}")


if __name__ == "__main__":
    # Test report generation
    from config.config import DATABASE_PATH

    db = Database(DATABASE_PATH)
    generator = ReportGenerator(db)

    print("Generating morning report...")
    report = generator.generate_morning_report()
    print(report['content'])
