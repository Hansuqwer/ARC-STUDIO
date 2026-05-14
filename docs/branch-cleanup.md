# Remote Branch Cleanup Review

Review date: 2026-05-14

These remote branches are unmerged into `origin/main`.

Deletion of remote branches is destructive. Do not delete without explicit
maintainer approval.

## Delete candidates

| Branch | Reason |
|--------|--------|
| `origin/handoff/no-mockups-github-ready` | Single old handoff commit (`1737bc7 Prepare ARC Studio handoff`); superseded by current docs and release checklist. |

## Salvage candidates

| Branch | Reason |
|--------|--------|
| `origin/recovered/troubleshooting-docs` | Contains troubleshooting docs (`afc1436`) that may still be useful. Review docs before deletion. |
| `origin/runtime/api-runs-start-field` | Contains runtime/API/frontend changes (`dbdbaac`, `5872303`, `c24a56d`, `5e54d2a`, `fb7b2a5`) that may contain product work. Review before deletion. |

## Parked roadmap branches

| Branch |
|--------|
| `origin/roadmap/pr-h2-web-coverage` |
| `origin/roadmap/pr1-pr3-ag-ui-foundation` |
| `origin/roadmap/pr10-health-monitor` |
| `origin/roadmap/pr11-real-swarmgraph` |
| `origin/roadmap/pr7-virtualized-list` |
| `origin/roadmap/pr8-event-filtering` |
| `origin/roadmap/pr9-otel-export` |

Recommendation: keep only roadmap branches with an owner and target date. If
no owner/date can be named, delete or convert to tracked issues.
