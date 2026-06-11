from __future__ import annotations

from indicators.common import clamp, true_ranges
from indicators.custom_mql_ported import fisher_transform, macd_osma, rsi_mfi_ma3, vwap_candle_breakout
from skill.signal_schema import Candle, FeatureSignal, StrategyResult

BACKTESTABLE_RULES = [
    "Evaluate only the most recent closed candle unless explicitly backtesting historical bars.",
    "BUY requires buy_score >= 0.68, buy_score - sell_score >= 0.18, reward_to_risk >= 1.5, and no bearish blocker.",
    "SELL requires sell_score >= 0.68, sell_score - buy_score >= 0.18, reward_to_risk >= 1.5, and no bullish blocker.",
    "HOLD when evidence is mixed, stale, under threshold, or blocked by nearby opposing structure.",
    "Stops use recent swing/VWAP invalidation with average true range padding; targets use at least 1.5R before calibration.",
]


class StrategySkill:
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Candle],
        risk_profile: str = "balanced",
    ) -> StrategyResult:
        if len(candles) < 60:
            raise ValueError("at least 60 normalized candles are required")
        features, indicator_values = self._calculate_features(candles)
        risk = self._risk_context(candles, risk_profile)
        scores = self._score(features, risk["reward_to_risk"])
        buy_blocker = self._has_blocker(features, blocked_direction="BUY")
        sell_blocker = self._has_blocker(features, blocked_direction="SELL")
        decision = "HOLD"
        selected_score = max(scores["buy_score"], scores["sell_score"])
        opposite_score = min(scores["buy_score"], scores["sell_score"])
        if (
            scores["buy_score"] >= 0.68
            and scores["buy_score"] - scores["sell_score"] >= 0.18
            and risk["reward_to_risk"] >= 1.5
            and not buy_blocker
        ):
            decision = "BUY"
            selected_score = scores["buy_score"]
            opposite_score = scores["sell_score"]
        elif (
            scores["sell_score"] >= 0.68
            and scores["sell_score"] - scores["buy_score"] >= 0.18
            and risk["reward_to_risk"] >= 1.5
            and not sell_blocker
        ):
            decision = "SELL"
            selected_score = scores["sell_score"]
            opposite_score = scores["buy_score"]
        probability = self._probability(decision, selected_score, opposite_score, risk)
        explanation = self._explain(decision, features, scores, risk)
        return StrategyResult(
            symbol=symbol,
            timeframe=timeframe,
            decision=decision,
            confidence=selected_score if decision != "HOLD" else max(scores["buy_score"], scores["sell_score"]),
            probability_of_success=probability,
            probability_model="heuristic",
            probability_sample_size=0,
            score_breakdown={
                "regime": scores["regime_selected"],
                "structure": scores["structure_selected"],
                "momentum": scores["momentum_selected"],
                "trigger": scores["trigger_selected"],
                "risk_reward": scores["risk_reward"],
                "buy_score": scores["buy_score"],
                "sell_score": scores["sell_score"],
            },
            indicator_values={
                **indicator_values,
                "features": {key: value.to_dict() for key, value in features.items()},
            },
            explanation=explanation,
            risk_assumptions=risk,
            backtestable_rules=BACKTESTABLE_RULES,
        )

    def _calculate_features(self, candles: list[Candle]) -> tuple[dict[str, FeatureSignal], dict]:
        vwap_signal, vwap_values = vwap_candle_breakout(candles)
        fisher_signal, fisher_values = fisher_transform(candles)
        rsi_mfi_signal, rsi_mfi_values = rsi_mfi_ma3(candles)
        osma_signal, osma_values = macd_osma(candles)
        structure_signal, structure_values = self._rolling_structure(candles)
        power_signal, power_values = self._power_candle(candles)
        features = {
            "regime": fisher_signal,
            "structure": structure_signal,
            "momentum_rsi_mfi": rsi_mfi_signal,
            "momentum_osma": osma_signal,
            "trigger_vwap": vwap_signal,
            "trigger_power_candle": power_signal,
        }
        values = {
            "vwap_candle_breakout": vwap_values,
            "fisher_yur4ik": fisher_values,
            "rsi_mfi_ma3": rsi_mfi_values,
            "macd_osma": osma_values,
            "rolling_structure": structure_values,
            "power_candle": power_values,
        }
        return features, values

    def _rolling_structure(self, candles: list[Candle], lookback: int = 24) -> tuple[FeatureSignal, dict]:
        current = candles[-1]
        previous_window = candles[-lookback - 1 : -1]
        resistance = max(c.high for c in previous_window)
        support = min(c.low for c in previous_window)
        if current.close > resistance:
            return FeatureSignal("BUY", 0.72, 0, resistance, "Close broke above rolling resistance"), {
                "rolling_resistance": resistance,
                "rolling_support": support,
            }
        if current.close < support:
            return FeatureSignal("SELL", 0.72, 0, support, "Close broke below rolling support"), {
                "rolling_resistance": resistance,
                "rolling_support": support,
            }
        midpoint = (resistance + support) / 2.0
        direction = "BUY" if current.close > midpoint else "SELL" if current.close < midpoint else "NEUTRAL"
        strength = 0.28
        return FeatureSignal(direction, strength, 0, midpoint, "Price remains inside rolling structure"), {
            "rolling_resistance": resistance,
            "rolling_support": support,
            "midpoint": midpoint,
        }

    def _power_candle(self, candles: list[Candle], lookback: int = 20, multiplier: float = 1.7) -> tuple[FeatureSignal, dict]:
        current = candles[-1]
        ranges = [c.high - c.low for c in candles[-lookback - 1 : -1]]
        avg_range = sum(ranges) / len(ranges)
        current_range = current.high - current.low
        if current_range >= avg_range * multiplier:
            direction = "BUY" if current.close > current.open else "SELL" if current.close < current.open else "NEUTRAL"
            return FeatureSignal(direction, 0.68, 0, current.close, "Impulse candle range exceeds recent average"), {
                "current_range": current_range,
                "average_range": avg_range,
                "multiplier": multiplier,
            }
        return FeatureSignal("NEUTRAL", 0.0, 0, current.close, "No power candle impulse"), {
            "current_range": current_range,
            "average_range": avg_range,
            "multiplier": multiplier,
        }

    def _risk_context(self, candles: list[Candle], risk_profile: str) -> dict:
        current = candles[-1]
        ranges = true_ranges([c.high for c in candles], [c.low for c in candles], [c.close for c in candles])
        atr = sum(ranges[-14:]) / min(14, len(ranges))
        recent = candles[-20:]
        swing_low = min(c.low for c in recent)
        swing_high = max(c.high for c in recent)
        long_stop_distance = max(current.close - swing_low + 0.25 * atr, atr)
        short_stop_distance = max(swing_high - current.close + 0.25 * atr, atr)
        rr = 1.8 if risk_profile == "aggressive" else 1.6 if risk_profile == "balanced" else 1.5
        return {
            "risk_profile": risk_profile,
            "atr": round(atr, 8),
            "long_stop": round(current.close - long_stop_distance, 8),
            "long_target": round(current.close + long_stop_distance * rr, 8),
            "short_stop": round(current.close + short_stop_distance, 8),
            "short_target": round(current.close - short_stop_distance * rr, 8),
            "reward_to_risk": rr,
            "max_position_size": "10%" if risk_profile != "conservative" else "5%",
            "assumption": "No live execution; stops and targets are deterministic backtest levels.",
        }

    def _score(self, features: dict[str, FeatureSignal], reward_to_risk: float) -> dict[str, float]:
        regime_buy, regime_sell = self._directional_score(features["regime"])
        structure_buy, structure_sell = self._directional_score(features["structure"])
        rsi_buy, rsi_sell = self._directional_score(features["momentum_rsi_mfi"])
        osma_buy, osma_sell = self._directional_score(features["momentum_osma"])
        vwap_buy, vwap_sell = self._directional_score(features["trigger_vwap"])
        power_buy, power_sell = self._directional_score(features["trigger_power_candle"])
        momentum_buy = (rsi_buy + osma_buy) / 2.0
        momentum_sell = (rsi_sell + osma_sell) / 2.0
        trigger_buy = max(vwap_buy, (vwap_buy + power_buy) / 2.0)
        trigger_sell = max(vwap_sell, (vwap_sell + power_sell) / 2.0)
        risk_reward = clamp((reward_to_risk - 1.0) / 1.5, 0.0, 1.0)
        buy_score = (
            0.25 * regime_buy
            + 0.25 * structure_buy
            + 0.20 * momentum_buy
            + 0.20 * trigger_buy
            + 0.10 * risk_reward
        )
        sell_score = (
            0.25 * regime_sell
            + 0.25 * structure_sell
            + 0.20 * momentum_sell
            + 0.20 * trigger_sell
            + 0.10 * risk_reward
        )
        selected_is_buy = buy_score >= sell_score
        return {
            "regime_selected": regime_buy if selected_is_buy else regime_sell,
            "structure_selected": structure_buy if selected_is_buy else structure_sell,
            "momentum_selected": momentum_buy if selected_is_buy else momentum_sell,
            "trigger_selected": trigger_buy if selected_is_buy else trigger_sell,
            "risk_reward": risk_reward,
            "buy_score": buy_score,
            "sell_score": sell_score,
        }

    def _directional_score(self, signal: FeatureSignal) -> tuple[float, float]:
        if signal.direction == "BUY":
            return signal.strength, 0.0
        if signal.direction == "SELL":
            return 0.0, signal.strength
        return 0.0, 0.0

    def _has_blocker(self, features: dict[str, FeatureSignal], blocked_direction: str) -> bool:
        opposing = "SELL" if blocked_direction == "BUY" else "BUY"
        return any(
            key.startswith("trigger") and signal.direction == opposing and signal.strength >= 0.68
            for key, signal in features.items()
        )

    def _probability(self, decision: str, selected_score: float, opposite_score: float, risk: dict) -> float:
        if decision == "HOLD":
            return 0.5
        edge = selected_score - opposite_score
        probability = 0.50 + 0.35 * edge
        if risk["reward_to_risk"] < 1.8:
            probability -= 0.05
        return clamp(probability, 0.35, 0.82)

    def _explain(self, decision: str, features: dict[str, FeatureSignal], scores: dict[str, float], risk: dict) -> str:
        leading = sorted(features.items(), key=lambda item: item[1].strength, reverse=True)[:3]
        reasons = "; ".join(f"{name}: {signal.reason}" for name, signal in leading)
        if decision == "HOLD":
            return f"HOLD because buy_score={scores['buy_score']:.2f}, sell_score={scores['sell_score']:.2f}, and thresholds/conflicts are not clean. {reasons}."
        return f"{decision} because score threshold and conflict checks passed with {risk['reward_to_risk']:.1f}R reward-to-risk. {reasons}."


def strategy_spec() -> dict:
    return {
        "name": "CMC-style VWAP Fisher Momentum Strategy Skill",
        "mode": "deterministic_track_2_backtestable",
        "decisions": ["BUY", "SELL", "HOLD"],
        "feature_groups": ["regime", "structure", "momentum", "trigger", "risk_context"],
        "rules": BACKTESTABLE_RULES,
        "indicators_implemented": [
            "VWAP_CANDLE_BREAKOUT_slope_dir_line",
            "Fisher_Yur4ik3-a_v6_MTF core Fisher transform",
            "RSI_MFI_MA3",
            "MACD_OSMA_Bar_alert",
            "Power_Candle_Alerts_v2 style range impulse",
            "Rolling high/low structure proxy",
        ],
        "not_live_trading": True,
    }

