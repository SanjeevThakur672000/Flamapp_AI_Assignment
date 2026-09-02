# Pushing to GitHub

`starter_kit/` (36 KB) is committed so the grader can clone and run everything
with no arguments. Scripts search `..`, `../..` and `../../..` for it, so both
layouts work. `corpus/` is committed too (~2 MB, FLORES-200 devtest for 8
languages) so the A3 numbers are reproducible without a 25 MB download.

Excluded via `.gitignore`: `.venv/`, `__pycache__/`, `*.tar.gz`.

```bash
cd ~/JOBS/placement/audit_submission/submission
git init
git add -A
git status --short          # confirm no .venv, no .tar.gz
git commit -m "Tokenizer and serving-stack audit"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

Check size before pushing: `du -sh --exclude=.venv --exclude=.git .`
Should be a few MB. If it is hundreds, `.venv` or the FLORES tarball leaked in.

**Private repo.** This is a take-home; keep it private and add the reviewer as
a collaborator rather than publishing it.

**Sanity check after pushing** — clone fresh and run, the way the grader will:

```bash
cd /tmp && git clone <your-repo-url> check && cd check
python3 -m venv .venv && source .venv/bin/activate && pip install -q regex
python partB/reconcile.py && python partA/decompose.py
```

If those two print, the repo is self-contained.
