# Stage 01 — Intake
Layer 2. Read on task entry.

## Job
Receive a task from Dave or COI. Classify it. Route it through the pipeline.

## Execution
Claude API (Sonnet 4.6) via COI-CC bridge. One instruction, one response.

## Inputs
| Source | File | Why |
|--------|------|-----|
| Dave/COI | Task description (plain text) | The work to be done |
| Layer 0 | CLAUDE.md | Operating rules and constraints |

## Process
1. Read the task description
2. Classify: code task / Codex update / UI change / research
3. Break into sub-tasks if needed
4. Write task brief to output/

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Task brief | output/task-brief.md | Markdown — task, priority, context |

## Drop-Off Protection
Content tagged with `[DROP-OFF-ORIGIN: verified]` is constitutionally protected.
- Do NOT summarize, trim, paraphrase, or reinterpret protected content
- Pass verbatim through all pipeline stages
- Classification may be applied externally (metadata) but content body is immutable
- Chunking via `coi_chunk_file()` IS permitted for large files — preserves all original content

## Routing
- Code → Stage 02 (Generate)
- Review only → Stage 03 (Review)
- Deploy approved queue → Stage 06 (Deploy)
