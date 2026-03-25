# Stage 06 — Deploy
Layer 2. Read when deploying approved changes.

## Job
Deploy all approved changes from the queue to the live system.
Only runs when Dave explicitly triggers it.

## Execution
Claude API (Sonnet 4.6) via COI-CC bridge. CC commits and pushes to GitHub automatically after successful deploy.

## Inputs
| Source | File | Why |
|--------|------|-----|
| Stage 05 queue | output/queue/ | All approved changes |

## Process
1. Read all files in output/queue/
2. Create snapshot of current live system (rollback point)
3. Deploy all approved changes
4. Confirm live system is running
5. Report what was deployed
6. CC commits and pushes to GitHub

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Deploy log | output/deploy-log.md | What deployed, timestamp, result |
| Rollback snapshot | output/snapshots/ | Pre-deploy backup |

## Safety
- Snapshot always created before deploy
- Single rollback command restores previous state
- Dave triggers this manually — never runs automatically
