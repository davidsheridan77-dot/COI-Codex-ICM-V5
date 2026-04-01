# Next Session Briefing
## Last Updated: 2026-03-31 22:13
## Source: Shutdown summary

I can see the request to clear all jobs, but I need to use the Forge Manager to handle this properly. Let me execute the queue management:

```bash
forge queue clear --all --confirm
```

The job queue should now be empty. You can verify this with:

```bash
forge queue list
```

This will remove all pending, waiting, and queued jobs. Any currently running jobs will complete but no new jobs will be queued.

Is there a specific reason you wanted to clear the queue? Are we resetting for a new workflow or dealing with stuck jobs?
