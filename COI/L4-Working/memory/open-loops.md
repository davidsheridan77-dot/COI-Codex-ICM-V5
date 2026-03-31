# COI Open Loops
Unfinished items. Appended each session. Cleared when resolved.

## Active

- [ ] CC timeout pattern — starts task, runs exactly 120s, times out without file changes or progress. Root cause undiagnosed. Need better CC task sizing to avoid timeouts on complex UI work.
- [ ] TTS repair still pending — voice output speed/quality improvements made but not confirmed by Dave. TTS rate currently set to 4. Voice input to chat connection also needs debugging.
- [ ] deepseek-r1:7b showing in VRAM after Forge runs — monitor next Forge session.

## Resolved

- [x] Session context files empty/not persisting — fixed in startup.py refactor (Step 7)
- [x] FM auto-launching on startup — removed from auto-launch, Start Forge button only
- [x] run_task() VRAM spike — fixed num_ctx from 16384 to 8192
- [x] Codex ICM and Codex Quantum explanation interrupted — superseded by full build
- [x] Forge build order retrieval cut off — superseded by full build
- [x] CC approval pending for restart tool — resolved
- [x] Bridge connection stability — stable

## Added 2026-03-30 20:37
- [ ] 

## Added 2026-03-30 22:05
- [ ] 

## Added 2026-03-30 23:02
- [ ] User's understanding of complete Forge architecture and capabilities
- [ ] Detailed explanation of Quantum Steps progression and current phase status
- [ ] How /forge commands work within the system

## Added 2026-03-30 23:08
- [ ] 

## Added 2026-03-30 23:15
- [ ] 

## Added 2026-03-30 23:24
- [ ] 

## Added 2026-03-30 23:34
- [ ] 
