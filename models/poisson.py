"""Poisson model for NHL game predictions."""
import numpy as np
from scipy.stats import poisson
from typing import Dict, List, Tuple, Optional
from database.models import Database, GameStats, ModelPrediction
from config.config import LOOKBACK_DAYS, HOME_ADVANTAGE_FACTOR


class PoissonModel:
    """Poisson distribution model for NHL predictions."""

    def __init__(self, db: Database):
        self.db = db
        self.game_stats = GameStats(db)
        self.model_pred = ModelPrediction(db)
        self.lambda_home = None
        self.lambda_away = None

    def train(self, lookback_days: int = LOOKBACK_DAYS, scope: str = "global", use_xg: bool = True) -> Dict[str, float]:
        """
        Train Poisson model on recent games.
        Can use either actual goals or Expected Goals (xG) from Moneypuck.

        Args:
            lookback_days: Number of days to look back for training data
            scope: Model scope identifier (e.g., 'global', 'noon')
            use_xg: Whether to use xG instead of actual goals (more accurate)

        Returns:
            Dictionary with lambda_home and lambda_away
        """
        # Get recent games
        recent_games = self.game_stats.get_recent_games(lookback_days)

        if not recent_games:
            print(f"⚠️ No games found in last {lookback_days} days")
            return {'lambda_home': 3.0, 'lambda_away': 2.7}

        # Parse meta JSON if stored as string
        import json
        for game in recent_games:
            if isinstance(game.get('meta'), str):
                try:
                    game['meta'] = json.loads(game['meta'])
                except:
                    game['meta'] = {}

        # Check if we have xG data available
        has_xg_data = any(
            g.get('meta', {}).get('advanced_stats', {}).get('home_xG') is not None
            for g in recent_games
        )

        if use_xg and has_xg_data:
            # Use Expected Goals (xG) - more accurate!
            print(f"🎯 Using xG data for training (more accurate)")

            home_values = []
            away_values = []

            for g in recent_games:
                meta = g.get('meta', {})
                adv_stats = meta.get('advanced_stats', {})

                home_xg = adv_stats.get('home_xG')
                away_xg = adv_stats.get('away_xG')

                if home_xg is not None and away_xg is not None:
                    home_values.append(float(home_xg))
                    away_values.append(float(away_xg))

            if home_values and away_values:
                avg_home = np.mean(home_values)
                avg_away = np.mean(away_values)
                model_type = 'poisson_xg_v2'
            else:
                # Fallback to actual goals
                print("⚠️ xG data incomplete, falling back to actual goals")
                home_values = [g['home_score'] for g in recent_games]
                away_values = [g['away_score'] for g in recent_games]
                avg_home = np.mean(home_values)
                avg_away = np.mean(away_values)
                model_type = 'poisson_v1'
        else:
            # Use actual goals
            print(f"📊 Using actual goals for training")
            home_values = [g['home_score'] for g in recent_games]
            away_values = [g['away_score'] for g in recent_games]
            avg_home = np.mean(home_values)
            avg_away = np.mean(away_values)
            model_type = 'poisson_v1'

        # Apply home advantage factor
        self.lambda_home = avg_home * HOME_ADVANTAGE_FACTOR
        self.lambda_away = avg_away

        # Store model
        self.model_pred.create(
            model=model_type,
            scope=scope,
            lambda_home=self.lambda_home,
            lambda_away=self.lambda_away,
            meta={
                'lookback_days': lookback_days,
                'n_games': len(recent_games),
                'avg_home_raw': float(avg_home),
                'avg_away_raw': float(avg_away),
                'home_advantage_factor': HOME_ADVANTAGE_FACTOR,
                'used_xg': use_xg and has_xg_data,
                'xg_games_available': len([g for g in recent_games
                                          if g.get('meta', {}).get('advanced_stats', {}).get('home_xG')])
            }
        )

        print(f"✅ Model trained: λ_home={self.lambda_home:.2f}, λ_away={self.lambda_away:.2f}")
        print(f"   Type: {model_type}")
        print(f"   Data: ({len(recent_games)} games, {lookback_days} days)")

        return {
            'lambda_home': self.lambda_home,
            'lambda_away': self.lambda_away,
            'model_type': model_type
        }

    def load_latest_model(self, scope: str = "global") -> bool:
        """Load latest trained model."""
        model = self.model_pred.get_latest_by_scope(scope)

        if not model:
            print(f"⚠️ No model found for scope '{scope}'")
            return False

        self.lambda_home = model['lambda_home']
        self.lambda_away = model['lambda_away']

        print(f"✅ Model loaded: λ_home={self.lambda_home:.2f}, λ_away={self.lambda_away:.2f}")
        return True

    def predict_game(self, home_team: str, away_team: str) -> Dict[str, float]:
        """
        Predict game outcome probabilities.

        Args:
            home_team: Home team abbreviation
            away_team: Away team abbreviation

        Returns:
            Dictionary with probabilities and fair odds
        """
        if self.lambda_home is None or self.lambda_away is None:
            raise ValueError("Model not trained or loaded")

        # Generate score probabilities (0-10 goals each)
        max_goals = 10
        prob_matrix = np.zeros((max_goals + 1, max_goals + 1))

        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                prob_matrix[i][j] = (
                    poisson.pmf(i, self.lambda_home) * poisson.pmf(j, self.lambda_away)
                )

        # Calculate outcome probabilities
        prob_home_win = np.sum(np.tril(prob_matrix, -1))  # Home scores more
        prob_away_win = np.sum(np.triu(prob_matrix, 1))   # Away scores more
        prob_draw = np.sum(np.diag(prob_matrix))          # Equal scores (rare in NHL due to OT)

        # In NHL, draws go to OT/SO - redistribute draw probability
        # Assume 50/50 in OT (simplified)
        prob_home_win += prob_draw * 0.5
        prob_away_win += prob_draw * 0.5

        # Calculate totals probabilities
        total_goals = self.lambda_home + self.lambda_away

        # Common totals
        prob_over_5_5 = 1 - poisson.cdf(5, total_goals)
        prob_under_5_5 = poisson.cdf(5, total_goals)
        prob_over_6_5 = 1 - poisson.cdf(6, total_goals)
        prob_under_6_5 = poisson.cdf(6, total_goals)

        # Fair odds (European decimal odds)
        fair_home_ml = 1 / prob_home_win if prob_home_win > 0 else 999
        fair_away_ml = 1 / prob_away_win if prob_away_win > 0 else 999
        fair_over_5_5 = 1 / prob_over_5_5 if prob_over_5_5 > 0 else 999
        fair_under_5_5 = 1 / prob_under_5_5 if prob_under_5_5 > 0 else 999
        fair_over_6_5 = 1 / prob_over_6_5 if prob_over_6_5 > 0 else 999
        fair_under_6_5 = 1 / prob_under_6_5 if prob_under_6_5 > 0 else 999

        return {
            'home_team': home_team,
            'away_team': away_team,
            'prob_home_win': float(prob_home_win),
            'prob_away_win': float(prob_away_win),
            'fair_home_ml': float(fair_home_ml),
            'fair_away_ml': float(fair_away_ml),
            'expected_total': float(total_goals),
            'prob_over_5_5': float(prob_over_5_5),
            'prob_under_5_5': float(prob_under_5_5),
            'fair_over_5_5': float(fair_over_5_5),
            'fair_under_5_5': float(fair_under_5_5),
            'prob_over_6_5': float(prob_over_6_5),
            'prob_under_6_5': float(prob_under_6_5),
            'fair_over_6_5': float(fair_over_6_5),
            'fair_under_6_5': float(fair_under_6_5),
        }

    def calculate_edge(self, fair_odds: float, market_odds: float) -> float:
        """
        Calculate edge percentage.

        Args:
            fair_odds: Fair odds from model
            market_odds: Market odds from bookmaker

        Returns:
            Edge percentage
        """
        if fair_odds <= 0:
            return 0.0

        edge = ((market_odds - fair_odds) / fair_odds) * 100
        return float(edge)

    def find_value_bets(
        self,
        predictions: List[Dict],
        mock_odds: Dict[str, float],
        min_edge: float = 5.0
    ) -> List[Dict]:
        """
        Find value bets based on edge threshold.

        Args:
            predictions: List of game predictions
            mock_odds: Dictionary of mock market odds (for testing)
            min_edge: Minimum edge percentage to consider

        Returns:
            List of value bet dictionaries
        """
        value_bets = []

        for pred in predictions:
            home_team = pred['home_team']
            away_team = pred['away_team']

            # Check moneyline bets
            home_ml_odds = mock_odds.get(f"{home_team}_ML", pred['fair_home_ml'])
            away_ml_odds = mock_odds.get(f"{away_team}_ML", pred['fair_away_ml'])

            home_edge = self.calculate_edge(pred['fair_home_ml'], home_ml_odds)
            away_edge = self.calculate_edge(pred['fair_away_ml'], away_ml_odds)

            if home_edge >= min_edge:
                value_bets.append({
                    'label': f"{home_team} ML",
                    'market': 'moneyline',
                    'team': home_team,
                    'odds': home_ml_odds,
                    'fair_odds': pred['fair_home_ml'],
                    'edge_pct': home_edge,
                    'implied_prob': pred['prob_home_win'],
                    'confidence': int(min(10, 5 + home_edge / 2))
                })

            if away_edge >= min_edge:
                value_bets.append({
                    'label': f"{away_team} ML",
                    'market': 'moneyline',
                    'team': away_team,
                    'odds': away_ml_odds,
                    'fair_odds': pred['fair_away_ml'],
                    'edge_pct': away_edge,
                    'implied_prob': pred['prob_away_win'],
                    'confidence': int(min(10, 5 + away_edge / 2))
                })

            # Check totals bets
            over_5_5_odds = mock_odds.get(f"{home_team}_O5.5", pred['fair_over_5_5'])
            under_5_5_odds = mock_odds.get(f"{home_team}_U5.5", pred['fair_under_5_5'])

            over_edge = self.calculate_edge(pred['fair_over_5_5'], over_5_5_odds)
            under_edge = self.calculate_edge(pred['fair_under_5_5'], under_5_5_odds)

            if over_edge >= min_edge:
                value_bets.append({
                    'label': f"{home_team} vs {away_team} Over 5.5",
                    'market': 'totals',
                    'team': f"{home_team}/{away_team}",
                    'odds': over_5_5_odds,
                    'fair_odds': pred['fair_over_5_5'],
                    'edge_pct': over_edge,
                    'implied_prob': pred['prob_over_5_5'],
                    'confidence': int(min(10, 5 + over_edge / 2))
                })

            if under_edge >= min_edge:
                value_bets.append({
                    'label': f"{home_team} vs {away_team} Under 5.5",
                    'market': 'totals',
                    'team': f"{home_team}/{away_team}",
                    'odds': under_5_5_odds,
                    'fair_odds': pred['fair_under_5_5'],
                    'edge_pct': under_edge,
                    'implied_prob': pred['prob_under_5_5'],
                    'confidence': int(min(10, 5 + under_edge / 2))
                })

        # Sort by edge descending
        value_bets.sort(key=lambda x: x['edge_pct'], reverse=True)

        return value_bets


if __name__ == "__main__":
    # Test the model
    from config.config import DATABASE_PATH

    db = Database(DATABASE_PATH)
    model = PoissonModel(db)

    print("Training Poisson model...")
    model.train()

    print("\nTesting predictions...")
    pred = model.predict_game("BOS", "TOR")

    print(f"\n🏒 BOS vs TOR")
    print(f"  Home win: {pred['prob_home_win']:.2%} (fair odds: {pred['fair_home_ml']:.2f})")
    print(f"  Away win: {pred['prob_away_win']:.2%} (fair odds: {pred['fair_away_ml']:.2f})")
    print(f"  Expected total: {pred['expected_total']:.2f}")
    print(f"  Over 5.5: {pred['prob_over_5_5']:.2%} (fair odds: {pred['fair_over_5_5']:.2f})")
