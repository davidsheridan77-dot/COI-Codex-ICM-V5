# Stage 03 — Review
Layer 2. Read when reviewing code.

## Job
Review the generated code for quality, security, and correctness.

## Execution
Claude API (Sonnet 4.6) via COI-CC bridge. One instruction, one response.

## Inputs
| Source | File | Why |
|--------|------|-----|
| Stage 02 | ../02-generate/output/generated-code.md | Code to review |
| Stage 01 | ../01-intake/output/task-brief.md | Original requirements |

## Process
1. Read the generated code
2. Check against original task brief — does it do what was asked?
3. Check for: security gaps, redundant code, inefficient patterns, broken references
4. Assign severity to each finding: Critical / High / Medium / Low
5. Write review report to output/

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Review report | output/review-report.md | Findings list, severity, recommendation |

## Gate
- Zero Critical findings → proceed to Stage 04
- Any Critical finding → return to Stage 02 with findings
