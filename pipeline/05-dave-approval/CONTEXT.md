# Stage 05 — Dave Approval
Layer 2. This stage does not run automatically.

## Job
Surface completed, tested work to Dave for review.
Nothing passes this stage without Dave's explicit approval.
This is a hard stop. No automation past this point.

## Inputs
| Source | File | Why |
|--------|------|-----|
| Stage 04 | ../04-sandbox/output/test-result.md | Test result |
| Stage 02 | ../02-generate/output/generated-code.md | The actual code |
| Stage 01 | ../01-intake/output/task-brief.md | Original task |

## What Dave Sees
- Plain English summary: what was built and why
- Test result: PASS/FAIL
- The code itself
- What changes if this is deployed

## Dave's Options
- APPROVE → file moves to pipeline/06-deploy/output/queue/
- REJECT → returned to Stage 01 with Dave's notes
- HOLD → stays here, flagged for later review

## Output
| Artifact | Location | Format |
|----------|----------|--------|
| Approval record | output/approval-record.md | Decision, timestamp, notes |
