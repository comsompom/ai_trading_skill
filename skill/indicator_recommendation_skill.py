from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from data.providers import get_provider
from indicators.common import clamp, true_ranges
from skill.signal_schema import AnalyzeRequest, Candle, FeatureSignal
from skill.strategy_skill import StrategySkill

MIN_RECOMMENDATION_CANDLES = 90
DEFAULT_FORWARD_BARS = 3

INDICATOR_DESCRIPTIONS = {
    "regime": {
        "name": "Fisher regime",
        "category": "regime",
        "default_role": "Trend/regime filter",
        "setting_basis": "Use as a directional filter before accepting trigger signals.",
    },
    "structure": {
        "name": "Rolling structure",
        "category": "structure",
        "default_role": "Breakout and range context",
        "setting_basis": "Prefer signals near rolling support/resistance breaks.",
    },
    "structure_abcd": {
        "name": "ABCD projection",
        "category": "structure",
        "default_role": "Projected support/resistance",
        "setting_basis": "Use projected D and Fibonacci levels as target/invalidations.",
    },
    "structure_demark": {
        "name": "DeMark support/resistance",
        "category": "structure",
        "default_role": "Support/resistance confirmation",
        "setting_basis": "Use with breakout triggers when the nearest level is not blocking the trade.",
    },
    "structure_hl_session": {
        "name": "Session high/low",
        "category": "structure",
        "default_role": "Session reversal context",
        "setting_basis": "Use as a session-level blocker or reversal confirmation.",
    },
    "momentum_rsi_mfi": {
        "name": "RSI/MFI/MA3 momentum",
        "category": "momentum",
        "default_role": "Momentum confirmation",
        "setting_basis": "Require momentum agreement when trigger quality is borderline.",
    },
    "momentum_osma": {
        "name": "MACD OSMA",
        "category": "momentum",
        "default_role": "Momentum impulse confirmation",
        "setting_basis": "Use OSMA direction changes as secondary confirmation.",
    },
    "trigger_vwap": {
        "name": "VWAP candle breakout",
        "category": "trigger",
        "default_role": "Entry trigger",
        "setting_basis": "Use as an entry trigger when trend and structure agree.",
    },
    "trigger_apex": {
        "name": "APEX pattern",
        "category": "trigger",
        "default_role": "Pattern trigger",
        "setting_basis": "Use only when recent pattern signals have enough sample support.",
    },
    "trigger_power_candle": {
        "name": "Power candle",
        "category": "trigger",
        "default_role": "Impulse trigger",
        "setting_basis": "Use a range multiplier around 1.7 and confirm direction with momentum.",
    },
}


@dataclass
class IndicatorEvaluation:
    key: str
    name: str
    category: str
    role: str
    signal_count: int
    buy_signals: int
    sell_signals: int
    win_rate: float
    average_forward_return: float
    profit_factor: float
    average_strength: float
    coverage: float
    suitability_score: float
    recommendation: str
    settings: dict[str, Any]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "role": self.role,
            "signal_count": self.signal_count,
            "buy_signals": self.buy_signals,
            "sell_signals": self.sell_signals,
            "win_rate": round(self.win_rate, 4),
            "average_forward_return": round(self.average_forward_return, 6),
            "profit_factor": round(self.profit_factor, 4),
            "average_strength": round(self.average_strength, 4),
            "coverage": round(self.coverage, 4),
            "suitability_score": round(self.suitability_score, 4),
            "recommendation": self.recommendation,
            "settings": self.settings,
            "reason": self.reason,
        }


class IndicatorRecommendationSkill:
    """
    Checks a symbol/timeframe against historical candles and recommends which
    available strategy indicators are best suited to that market.

    The skill evaluates each indicator independently on rolling historical
    windows. BUY and SELL signals are compared with forward returns over a
    small holding horizon. The output is a deterministic suitability report,
    not a live trading signal.
    """

    def analyze_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = AnalyzeRequest.from_payload(payload)
        candles = request.market_data or self._fetch_candles(request)
        forward_bars = int(payload.get("forward_bars", DEFAULT_FORWARD_BARS))
        forward_bars = max(1, min(12, forward_bars))
        return self.analyze(
            symbol=request.symbol,
            timeframe=request.timeframe,
            candles=candles,
            provider=request.provider,
            forward_bars=forward_bars,
        )

    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Candle],
        provider: str = "inline",
        forward_bars: int = DEFAULT_FORWARD_BARS,
    ) -> dict[str, Any]:
        if len(candles) < MIN_RECOMMENDATION_CANDLES:
            raise ValueError(f"indicator recommendation requires at least {MIN_RECOMMENDATION_CANDLES} candles")

        raw_stats = {key: self._empty_stats() for key in INDICATOR_DESCRIPTIONS}
        strategy = StrategySkill()
        evaluation_count = 0
        last_values: dict[str, dict[str, Any]] = {}

        last_index = len(candles) - forward_bars - 1
        for index in range(60, last_index + 1):
            window = candles[: index + 1]
            features, _ = strategy._calculate_features(window)
            entry = candles[index].close
            exit_price = candles[index + forward_bars].close
            forward_return = (exit_price - entry) / entry
            threshold = self._movement_threshold(window, entry)
            evaluation_count += 1

            for key, signal in features.items():
                if key not in raw_stats:
                    continue
                self._record_signal(raw_stats[key], signal, forward_return, threshold)

        latest_features, latest_values = strategy._calculate_features(candles)
        for key, signal in latest_features.items():
            if key in raw_stats:
                last_values[key] = signal.to_dict()

        evaluations = [
            self._build_evaluation(key, stats, evaluation_count)
            for key, stats in raw_stats.items()
        ]
        evaluations.sort(key=lambda item: item.suitability_score, reverse=True)

        recommended = [item for item in evaluations if item.recommendation == "use"]
        confirm = [item for item in evaluations if item.recommendation == "use_with_confirmation"]
        avoid = [item for item in evaluations if item.recommendation == "avoid_for_now"]
        regime = self._market_regime(candles)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "provider": provider,
            "skill": indicator_recommendation_spec(),
            "summary": self._summary(symbol, timeframe, recommended, confirm, avoid, regime),
            "market_profile": regime,
            "recommended_indicators": [item.to_dict() for item in recommended],
            "confirmation_indicators": [item.to_dict() for item in confirm],
            "avoid_indicators": [item.to_dict() for item in avoid],
            "all_indicators": [item.to_dict() for item in evaluations],
            "latest_signals": last_values,
            "latest_indicator_values": latest_values,
            "analysis_settings": {
                "candles": len(candles),
                "forward_bars": forward_bars,
                "min_candles": MIN_RECOMMENDATION_CANDLES,
                "evaluated_windows": evaluation_count,
                "signal_strength_floor": 0.15,
            },
            "input_data_range": {
                "start": candles[0].timestamp,
                "end": candles[-1].timestamp,
                "candles": len(candles),
            },
            "assumptions": [
                "Indicator suitability is scored on historical closed candles only.",
                "Forward returns use close-to-close movement and do not include fees or slippage.",
                "A recommendation describes indicator fit for this symbol/timeframe, not a BUY or SELL order.",
            ],
        }

    def _fetch_candles(self, request: AnalyzeRequest) -> list[Candle]:
        provider = get_provider(request.provider)
        return provider.get_candles(request.symbol, request.timeframe, request.lookback)

    def _empty_stats(self) -> dict[str, Any]:
        return {
            "signals": 0,
            "buy_signals": 0,
            "sell_signals": 0,
            "wins": 0,
            "signed_returns": [],
            "strengths": [],
            "gross_wins": 0.0,
            "gross_losses": 0.0,
        }

    def _record_signal(
        self,
        stats: dict[str, Any],
        signal: FeatureSignal,
        forward_return: float,
        threshold: float,
    ) -> None:
        if signal.direction not in {"BUY", "SELL"} or signal.strength < 0.15:
            return
        signed_return = forward_return if signal.direction == "BUY" else -forward_return
        stats["signals"] += 1
        stats["buy_signals"] += 1 if signal.direction == "BUY" else 0
        stats["sell_signals"] += 1 if signal.direction == "SELL" else 0
        stats["wins"] += 1 if signed_return > threshold else 0
        stats["signed_returns"].append(signed_return)
        stats["strengths"].append(signal.strength)
        if signed_return > 0:
            stats["gross_wins"] += signed_return
        elif signed_return < 0:
            stats["gross_losses"] += abs(signed_return)

    def _build_evaluation(self, key: str, stats: dict[str, Any], evaluation_count: int) -> IndicatorEvaluation:
        meta = INDICATOR_DESCRIPTIONS[key]
        signal_count = stats["signals"]
        returns = stats["signed_returns"]
        strengths = stats["strengths"]
        win_rate = stats["wins"] / signal_count if signal_count else 0.0
        avg_return = sum(returns) / len(returns) if returns else 0.0
        avg_strength = sum(strengths) / len(strengths) if strengths else 0.0
        coverage = signal_count / evaluation_count if evaluation_count else 0.0
        profit_factor = stats["gross_wins"] / stats["gross_losses"] if stats["gross_losses"] > 0 else stats["gross_wins"] * 100
        profit_factor_score = clamp(profit_factor / (profit_factor + 1.0), 0.0, 1.0) if profit_factor > 0 else 0.0
        sample_score = clamp(signal_count / 18.0, 0.0, 1.0)
        suitability = (
            0.38 * win_rate
            + 0.26 * profit_factor_score
            + 0.18 * avg_strength
            + 0.10 * sample_score
            + 0.08 * clamp(coverage / 0.55, 0.0, 1.0)
        )
        recommendation = self._recommendation(suitability, signal_count)
        min_strength = self._recommended_strength_floor(recommendation, avg_strength, signal_count)
        settings = {
            "recommended_action": recommendation,
            "minimum_signal_strength": min_strength,
            "confirmation_required": recommendation != "use",
            "role": meta["default_role"],
            "setting_basis": meta["setting_basis"],
        }
        reason = self._reason(recommendation, signal_count, win_rate, avg_return, profit_factor)
        return IndicatorEvaluation(
            key=key,
            name=meta["name"],
            category=meta["category"],
            role=meta["default_role"],
            signal_count=signal_count,
            buy_signals=stats["buy_signals"],
            sell_signals=stats["sell_signals"],
            win_rate=win_rate,
            average_forward_return=avg_return,
            profit_factor=profit_factor,
            average_strength=avg_strength,
            coverage=coverage,
            suitability_score=suitability,
            recommendation=recommendation,
            settings=settings,
            reason=reason,
        )

    def _recommendation(self, suitability: float, signal_count: int) -> str:
        if signal_count < 5:
            return "avoid_for_now"
        if suitability >= 0.58:
            return "use"
        if suitability >= 0.45:
            return "use_with_confirmation"
        return "avoid_for_now"

    def _recommended_strength_floor(self, recommendation: str, average_strength: float, signal_count: int) -> float:
        if signal_count < 5:
            return 0.7
        base = 0.58 if recommendation == "use" else 0.66 if recommendation == "use_with_confirmation" else 0.72
        return round(clamp(max(base, average_strength * 0.9), 0.15, 0.9), 2)

    def _reason(
        self,
        recommendation: str,
        signal_count: int,
        win_rate: float,
        avg_return: float,
        profit_factor: float,
    ) -> str:
        if signal_count < 5:
            return "Not enough historical directional signals for this symbol/timeframe."
        action = {
            "use": "Suitable as a primary input",
            "use_with_confirmation": "Usable only with confirmation",
            "avoid_for_now": "Weak historical fit",
        }[recommendation]
        return (
            f"{action}: {signal_count} signals, {win_rate:.0%} win rate, "
            f"{avg_return:.3%} average forward return, {profit_factor:.2f} profit factor."
        )

    def _movement_threshold(self, candles: list[Candle], entry_price: float) -> float:
        ranges = true_ranges([c.high for c in candles], [c.low for c in candles], [c.close for c in candles])
        atr = sum(ranges[-14:]) / min(14, len(ranges))
        return clamp((atr / entry_price) * 0.18, 0.001, 0.025)

    def _market_regime(self, candles: list[Candle]) -> dict[str, Any]:
        closes = [c.close for c in candles]
        recent = closes[-30:]
        older = closes[-60:-30]
        trend_return = (recent[-1] - recent[0]) / recent[0]
        older_return = (older[-1] - older[0]) / older[0] if older else 0.0
        ranges = true_ranges([c.high for c in candles], [c.low for c in candles], [c.close for c in candles])
        atr_pct = (sum(ranges[-14:]) / min(14, len(ranges))) / closes[-1]
        direction = "uptrend" if trend_return > 0.025 else "downtrend" if trend_return < -0.025 else "range"
        volatility = "high" if atr_pct > 0.035 else "low" if atr_pct < 0.012 else "normal"
        return {
            "direction": direction,
            "volatility": volatility,
            "recent_return": round(trend_return, 6),
            "prior_return": round(older_return, 6),
            "atr_percent": round(atr_pct, 6),
        }

    def _summary(
        self,
        symbol: str,
        timeframe: str,
        recommended: list[IndicatorEvaluation],
        confirm: list[IndicatorEvaluation],
        avoid: list[IndicatorEvaluation],
        regime: dict[str, Any],
    ) -> str:
        top = ", ".join(item.name for item in recommended[:3]) or "no primary indicators"
        secondary = ", ".join(item.name for item in confirm[:2]) or "no secondary indicators"
        return (
            f"{symbol} on {timeframe} currently profiles as {regime['direction']} with {regime['volatility']} volatility. "
            f"Use {top}. Keep {secondary} for confirmation. {len(avoid)} indicators should be avoided until their sample improves."
        )


def indicator_recommendation_spec() -> dict[str, Any]:
    return {
        "name": "Historical Indicator Recommendation Skill",
        "mode": "deterministic_indicator_fit_analysis",
        "description": (
            "Evaluates a user-selected symbol on historical candle data and recommends "
            "which implemented indicators are best suited for that symbol/timeframe."
        ),
        "inputs": {
            "symbol": "Trading pair such as BTCUSDT",
            "timeframe": "Supported provider timeframe, currently 4h or 1d in the UI",
            "lookback": f"Historical candle count, minimum {MIN_RECOMMENDATION_CANDLES}",
            "provider": "Market-data provider or inline market_data",
            "forward_bars": f"Forward close-to-close evaluation horizon, default {DEFAULT_FORWARD_BARS}",
        },
        "outputs": [
            "market_profile",
            "recommended_indicators",
            "confirmation_indicators",
            "avoid_indicators",
            "all_indicators",
            "analysis_settings",
        ],
        "not_live_trading": True,
    }
