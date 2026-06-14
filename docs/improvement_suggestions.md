# Improvement Suggestions From External Resources

This document captures suggested ways to use the listed hackathon and ecosystem resources to improve the AI Trading Skill project.

First implemented indicator-based Strategy Skill demo video:

- https://www.youtube.com/watch?v=TA6gRVvitJs

Indicator Recommendation Skill demo video:

- https://youtu.be/j8ii27bbz4A

## Current Project Constraint

The project is currently positioned as a Track 2 CMC-powered Strategy Skill:

- It produces deterministic, backtestable `BUY`, `SELL`, or `HOLD` decisions.
- It exposes Flask and FastMCP interfaces.
- It does not execute live trades.
- It does not sign transactions.

Keep this boundary unless the project intentionally adds a separate execution demo. Execution-related integrations should remain optional, user-approved, and clearly separated from the core strategy engine.

## CoinMarketCap AI Agent Hub

Resource:

- https://coinmarketcap.com/api/agent

Best use:

- Improve market intelligence and hackathon alignment.
- Use CMC Agent Hub as a premium/context data layer beside Binance, CoinGecko, CoinPaprika, and DefiLlama.
- Treat CMC outputs as structured market context and confidence modifiers, not as untested direct trade triggers.

Suggested implementation:

1. Add `data/providers/cmc_agent_hub.py`.
2. Add `CMC_API_KEY` and any Agent Hub-specific settings to `.env.example`.
3. Add `provider="cmc"` to the skill input schema.
4. Normalize CMC outputs into the existing analysis response under `indicator_values.market_context`.
5. Map CMC signals into current feature groups:
   - `regime`: market cycle, dominance, broad risk-on/risk-off context.
   - `momentum`: RSI, MACD, EMA, gainers/losers, trend strength.
   - `structure`: support/resistance, liquidity zones, market breadth.
   - `risk_context`: Fear & Greed, ETF flows, liquidations, funding rates, volatility.
6. Add tests with fixture responses so the strategy stays deterministic in CI.

Demo value:

- Shows strong CMC ecosystem alignment.
- Gives judges richer explanations than raw OHLCV-only signals.
- Reduces the need to compute every external market signal locally.

## Trust Wallet Agent Kit

Resource:

- https://portal.trustwallet.com

Best use:

- Add an optional self-custody execution-readiness demo.
- Keep execution separate from the core strategy skill.
- Prefer quote-only and user-in-the-loop WalletConnect flows before any autonomous wallet path.

Suggested implementation:

1. Add a separate `agent/trust_wallet_runner.py` module.
2. Add a read-only or quote-only command path first:
   - price lookup
   - wallet portfolio summary
   - swap quote with `--quote-only`
   - alert creation
3. Extend the existing MCP decision envelope with optional execution metadata:
   - `twak_enabled`
   - `quote_available`
   - `requires_user_approval`
   - `walletconnect_recommended`
4. Do not pass raw wallet keys into strategy code.
5. Do not place orders automatically from `BUY` or `SELL` decisions.
6. Add docs showing that Trust Wallet integration is optional and self-custody/user-approved.

Safe demo flow:

1. Run `/analyze` or `make_trading_decision`.
2. If the result is `BUY` or `SELL`, request a quote only.
3. Show the quote and risk plan.
4. If using WalletConnect, require the user to review and approve the transaction manually.

Demo value:

- Shows a credible path from analysis to self-custody action.
- Avoids weakening the Track 2 claim that the core project is deterministic and non-executing.

## BNB AI Agent SDK

Resource:

- https://github.com/bnb-chain/bnbagent-sdk

Best use:

- Use the SDK as a discovery, identity, and paid-service wrapper around the existing skill.
- Do not make it the core strategy engine.

Suggested implementation:

1. Expand `agent/bnb_agent_runner.py` beyond the current thin wrapper.
2. Add a BNB SDK optional dependency group, for example `bnb = ["bnbagent>=..."]` once the compatible version is confirmed.
3. Register the strategy as an ERC-8004 testnet agent for discoverability.
4. Optionally expose the skill as an ERC-8183 service:
   - client submits symbol, timeframe, risk profile, and optional candles
   - agent runs the deterministic strategy/backtest
   - agent returns JSON and Markdown deliverables
   - payment/settlement stays in the BNB SDK layer
5. Add a short demo script for:
   - local strategy call
   - BNB SDK wrapped strategy call
   - optional testnet registration

Good service deliverables:

- Current market decision.
- Score breakdown.
- Indicator snapshot.
- Risk assumptions.
- Backtest summary.
- Reproducible input payload.

Demo value:

- Targets possible bonus credit for BNB AI Agent SDK usage.
- Makes the strategy discoverable as an agent service.
- Keeps the strategy independently testable and usable without BNB SDK setup.

## BNB Hack Telegram

Resource:

- https://t.me/+MhiOLT0YUnlmNWFk

Best use:

- Validate assumptions with organizers and other builders before spending time on risky integrations.

Questions to ask:

1. For Track 2, is CMC Agent Hub usage expected, optional, or bonus-relevant?
2. Which Agent Hub skills or APIs should strategy-skill submissions prioritize?
3. Does BNB AI Agent SDK registration or ERC-8183 wrapping count for extra judging value in Track 2?
4. Is a Trust Wallet quote-only or WalletConnect proposal demo acceptable without live autonomous execution?
5. Are there required submission formats for strategy skills, MCP manifests, or skill marketplace listings?

## Recommended Priority

1. Add CMC Agent Hub provider/context integration.
2. Improve docs and demo script around CMC-backed strategy reasoning.
3. Add BNB SDK identity/job wrapper for demo and bonus value.
4. Add Trust Wallet quote-only or user-approved execution demo.
5. Use the Telegram group to validate assumptions before deeper execution work.

## Guardrails

- Keep the core skill deterministic and backtestable.
- Keep live execution out of `skill/strategy_skill.py`.
- Keep signing and wallet logic out of data providers and indicators.
- Treat external context as additional evidence, not as a replacement for reproducible candles and indicators.
- Add fixtures and tests for each external adapter.
- Clearly mark optional integrations in README and demo docs.
