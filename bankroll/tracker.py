"""Bankroll and ROI tracking system."""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from database.models import Database, Pick, BankrollState, GameStats
from config.config import INITIAL_BANKROLL


class BankrollTracker:
    """Track bankroll and calculate ROI."""

    def __init__(self, db: Database):
        self.db = db
        self.pick_model = Pick(db)
        self.bankroll_state = BankrollState(db)
        self.game_stats = GameStats(db)

    def initialize_bankroll(self, amount: float = INITIAL_BANKROLL):
        """Initialize bankroll for today if not exists."""
        today = datetime.now().strftime('%Y-%m-%d')
        existing = self.bankroll_state.get_by_date(today)

        if not existing:
            # Get yesterday's end or use initial
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            yesterday_state = self.bankroll_state.get_by_date(yesterday)

            start_amount = yesterday_state['bankroll_end'] if yesterday_state else amount

            self.bankroll_state.create(
                date=today,
                bankroll_start=start_amount,
                bankroll_end=start_amount,
                pnl=0.0,
                roi=0.0
            )

            print(f"✅ Initialized bankroll for {today}: {start_amount:.2f}€")

    def settle_picks(self) -> Dict:
        """
        Settle pending picks based on game results.

        Returns:
            Settlement summary dictionary
        """
        pending_picks = self.pick_model.get_pending_picks()

        if not pending_picks:
            print("ℹ️ No pending picks to settle")
            return {
                'settled': 0,
                'wins': 0,
                'losses': 0,
                'pnl': 0.0
            }

        settled_count = 0
        wins = 0
        losses = 0
        total_pnl = 0.0

        for pick in pending_picks:
            # Get game result
            if not pick['game_pk']:
                continue

            game = self.game_stats.get_by_game_pk(pick['game_pk'])

            if not game or game['status'] != 'Final':
                continue  # Game not finished yet

            # Determine pick result
            result = self._evaluate_pick(pick, game)

            if result is None:
                continue  # Can't determine result

            # Calculate P&L
            if result == 'win':
                pnl = pick['stake'] * (pick['odds'] - 1)
                wins += 1
            else:  # lose
                pnl = -pick['stake']
                losses += 1

            total_pnl += pnl

            # Update pick
            self.pick_model.settle_pick(pick['id'], result)
            settled_count += 1

            print(f"  {'✅' if result == 'win' else '❌'} {pick['label']}: {result.upper()} ({pnl:+.2f}€)")

        if settled_count > 0:
            print(f"\n📊 Settled {settled_count} picks: {wins}W-{losses}L ({total_pnl:+.2f}€)")

        return {
            'settled': settled_count,
            'wins': wins,
            'losses': losses,
            'pnl': total_pnl
        }

    def _evaluate_pick(self, pick: Dict, game: Dict) -> Optional[str]:
        """
        Evaluate if a pick won or lost.

        Args:
            pick: Pick dictionary
            game: Game result dictionary

        Returns:
            'win', 'lose', or None if can't determine
        """
        market = pick['market']
        label = pick['label']

        home_score = game['home_score']
        away_score = game['away_score']
        total = home_score + away_score

        if market == 'moneyline':
            # Determine which team was picked
            home_team = game['home_team']
            away_team = game['away_team']

            if home_team in label:
                # Picked home team
                return 'win' if home_score > away_score else 'lose'
            elif away_team in label:
                # Picked away team
                return 'win' if away_score > home_score else 'lose'

        elif market == 'totals':
            # Parse total from label (e.g., "BOS vs TOR Over 5.5")
            if 'Over' in label:
                threshold = float(label.split('Over')[1].strip())
                return 'win' if total > threshold else 'lose'
            elif 'Under' in label:
                threshold = float(label.split('Under')[1].strip())
                return 'win' if total < threshold else 'lose'

        return None

    def update_bankroll(self, date: Optional[str] = None) -> Dict:
        """
        Update bankroll state for a date.

        Args:
            date: Date string (YYYY-MM-DD), defaults to today

        Returns:
            Updated bankroll state dictionary
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        # Settle picks first
        settlement = self.settle_picks()
        pnl = settlement['pnl']

        # Get current state
        current_state = self.bankroll_state.get_by_date(date)

        if not current_state:
            # Initialize if doesn't exist
            self.initialize_bankroll()
            current_state = self.bankroll_state.get_by_date(date)

        # Calculate new values
        bankroll_start = current_state['bankroll_start']
        bankroll_end = bankroll_start + pnl
        roi = (pnl / bankroll_start * 100) if bankroll_start > 0 else 0

        # Update state
        self.bankroll_state.create(
            date=date,
            bankroll_start=bankroll_start,
            bankroll_end=bankroll_end,
            pnl=pnl,
            roi=roi
        )

        print(f"\n💰 Bankroll updated for {date}:")
        print(f"   Start: {bankroll_start:.2f}€")
        print(f"   End: {bankroll_end:.2f}€")
        print(f"   P&L: {pnl:+.2f}€")
        print(f"   ROI: {roi:+.2f}%")

        return {
            'date': date,
            'bankroll_start': bankroll_start,
            'bankroll_end': bankroll_end,
            'pnl': pnl,
            'roi': roi,
            'settled_picks': settlement['settled'],
            'wins': settlement['wins'],
            'losses': settlement['losses']
        }

    def get_performance_summary(self, days: int = 7) -> Dict:
        """
        Get performance summary for last N days.

        Args:
            days: Number of days to look back

        Returns:
            Performance summary dictionary
        """
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')

        # Get picks in range
        picks = self.pick_model.get_picks_by_date_range(start_date, end_date)

        total_picks = len(picks)
        settled = [p for p in picks if p['result'] != 'pending']
        wins = [p for p in settled if p['result'] == 'win']
        losses = [p for p in settled if p['result'] == 'lose']

        total_staked = sum(p['stake'] for p in settled)
        total_return = sum(p['stake'] * p['odds'] for p in wins) - sum(p['stake'] for p in losses)
        roi = (total_return / total_staked * 100) if total_staked > 0 else 0

        win_rate = (len(wins) / len(settled) * 100) if settled else 0

        return {
            'period_days': days,
            'total_picks': total_picks,
            'settled_picks': len(settled),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_staked': total_staked,
            'total_return': total_return,
            'roi': roi
        }

    def get_current_bankroll(self) -> float:
        """Get current bankroll amount."""
        latest = self.bankroll_state.get_latest()
        return latest['bankroll_end'] if latest else INITIAL_BANKROLL


if __name__ == "__main__":
    # Test bankroll tracker
    from config.config import DATABASE_PATH

    db = Database(DATABASE_PATH)
    tracker = BankrollTracker(db)

    print("Initializing bankroll...")
    tracker.initialize_bankroll()

    print("\nUpdating bankroll...")
    result = tracker.update_bankroll()

    print("\nPerformance summary (7 days):")
    summary = tracker.get_performance_summary(7)
    for key, value in summary.items():
        print(f"  {key}: {value}")
