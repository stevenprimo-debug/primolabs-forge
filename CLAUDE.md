# primolabs-forge

Laws for this repo; each cites where it was earned.

## The laws

1. **Vercel deploys pin the project and upload only what ships.** A `.vercel/`
   link is gitignored and worktrees are disposable, so run every `vercel deploy`
   with `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` set to the target's team and
   project IDs; never let the CLI link, create or guess a project, and never run
   `vercel link`, which can pull env vars to disk. When the project's Root
   Directory is a subfolder, deploy from the repo root (inside the subfolder the
   CLI stops: `<dir>\<dir> does not exist`) and keep a root `.vercelignore` that
   allowlists only that folder (`/*`, then `!/<dir>`) and repeats the folder's
   own excludes: Vercel reads the root file, not the subfolder's, so without it
   docs, memory, `.claude/` and CLAUDE.md upload as deployment source. After a
   deploy, check the deployment's file list. (PrimoLabs deploy lesson, 2026-11-19.)
