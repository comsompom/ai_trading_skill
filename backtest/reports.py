from __future__ import annotations


def markdown_summary(report: dict) -> str:
    return "\n".join(
        [
            f"# Backtest Summary: {report['symbol']} {report['timeframe']}",
            "",
            f"- Total return: {report['total_return']:.2%}",
            f"- Win rate: {report['win_rate']:.2%}",
            f"- Max drawdown: {report['max_drawdown']:.2%}",
            f"- Trades: {report['number_of_trades']}",
            f"- Average trade return: {report['average_trade_return']:.2%}",
        ]
    )

