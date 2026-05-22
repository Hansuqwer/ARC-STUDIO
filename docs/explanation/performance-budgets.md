# Performance budgets

ARC Studio tracks three budgets. Budgets are **informational** for the first two
weeks after introduction (data collection); after that the CI job fails when the
**median of the last 5 runs** exceeds the budget by more than 20%.

| Metric                          | Budget    | Measured by                       |
|---------------------------------|-----------|-----------------------------------|
| Extension build time            | < 90 s    | `scripts/measure-perf.mjs build`  |
| Python test suite wall time     | < 120 s   | `scripts/measure-perf.mjs pytest` |
| Widget first-paint (dev mode)   | < 1.5 s   | `performance.now()` probe         |

Data lands as CI artifacts (`perf-history.jsonl`); we do not commit history to git.
