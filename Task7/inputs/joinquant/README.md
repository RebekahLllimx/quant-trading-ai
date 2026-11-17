# JoinQuant Evidence Boundary

This directory stores structured summaries exported from JoinQuant for course research. It may contain dates, strategy codes, symbols, order direction and size, execution price, costs, holdings, cash, total assets, platform status, and rejection reasons.

It must never contain:

- account identifiers, passwords, or verification codes;
- cookies, access tokens, or browser sessions;
- phone numbers, email addresses, or identity documents;
- private share links; or
- personal asset information unrelated to the research.

`backtest_summary.json` records the three completed platform backtests and the evidence status of each private simulated account. A deployed account without exported fills remains labeled `deployed_waiting_data`; public shadow-portfolio results must not be copied into the platform-performance field.
