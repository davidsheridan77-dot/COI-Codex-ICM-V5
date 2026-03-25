# Stage 04 — Sandbox
Layer 2. Read when testing.

## Job
Install the reviewed code into the sandbox and test it.

## Execution
Claude API (Sonnet 4.6) via COI-CC bridge. COI controls the Hyper-V sandbox VM via PowerShell.

## Inputs
| Source | File | Why |
|--------|------|-----|
| Stage 02 | ../02-generate/output/generated-code.md | Code to install |
| Stage 03 | ../03-review/output/review-report.md | Review findings |

## Process
1. Install code to sandbox (Hyper-V VM)
2. Run the code
3. Capture output and any errors
4. Log result: PASS or FAIL
5. If FAIL — package error and return to Stage 02
6. If PASS — write test result to output/

## Testing Philosophy
Test not inspect. Run changed code and report pass or fail. Never read files to check if something worked — run it and see.

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Test result | output/test-result.md | PASS/FAIL, output log, timestamp |

## Sandbox
- Hyper-V VM controlled by COI via PowerShell
- Isolated from live system
- All test results logged automatically
