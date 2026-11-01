---
name: commit-by-matter
description: Group pending changes by subject and commit each group using Conventional Commits, after scanning for secrets.
argument-hint: "[--dry-run]"
disable-model-invocation: true
---

# Commit by Matter

Turn the pending changes into small commits, one per subject. With `--dry-run` in `$ARGUMENTS`, stop
after step 4 and show the draft without staging or committing anything.

## 1. Inspect

Run `git status --short -uall`, `git diff`, `git diff --cached`, `git branch --show-current` and
`git log --oneline -10`. Read each untracked file before assigning it to a group.

- If there is nothing to commit, say so and stop.
- If a merge or rebase is in progress, stop and report it.
- If the current branch is the default branch, ask whether to create a branch or commit there. Skip
  this question for `--dry-run`.

## 2. Scan for sensitive content

Run from the repository root:

```bash
{ git ls-files -z -m -o --exclude-standard; git diff --cached --name-only -z; } \
  | python3 -I .claude/skills/commit-by-matter/scan_secrets.py
```

If it exits non-zero, stop before committing, list the reported files and let the user decide. Never
print a secret value. Also stop for anything else in the diff that looks private, such as real personal
data, internal hostnames or credentials in an unusual format.

## 3. Group by matter

Group by the reason for the change, not by folder or file type. Each file goes in exactly one commit.
If one file covers two subjects, put it with its main subject and mention this in the summary.

Order the commits so that each one makes sense with only the earlier ones applied. Do not commit files
the user excluded, and report any file you leave out and why.

## 4. Write the messages

Follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

```text
<type>(<optional scope>)!: <description>

<optional body>

<optional footers>
```

| Type | Use for |
|---|---|
| `feat` | A new capability for the user of the software |
| `fix` | A bug fix |
| `docs` | Documentation only |
| `style` | Formatting with no change in behavior |
| `refactor` | A code change that is neither a feature nor a fix |
| `perf` | A performance improvement |
| `test` | Adding or correcting tests |
| `build` | The build system or dependencies |
| `ci` | Continuous integration configuration |
| `chore` | Other maintenance that does not touch source or tests |
| `revert` | Reverting an earlier commit |

- Write the description in the imperative mood and lowercase, with no final period, and keep the first
  line within 72 characters.
- Use a scope only when it adds information, such as `feat(agent): ...`.
- Use a body to explain why, when the description is not enough. Wrap it at 72 characters.
- Mark breaking changes with `!` after the type or scope and a `BREAKING CHANGE: <details>` footer.
- Do not add a `Co-Authored-By` line unless the project's attribution rules ask for one.

## 5. Commit

Run `git restore --staged .` if anything is staged, so that only the planned files enter each commit.
Then, for each group in order:

```bash
git add -- <explicit paths>
git diff --cached --stat
git commit -F - <<'EOF'
<message>
EOF
```

- Stage explicit paths only. Never use `git add -A` or `git add .`.
- Never amend, rebase, force-push or use `--no-verify`.
- Never push. Pushing is a separate decision for the user.
- If a commit or hook fails, stop, leave the remaining groups uncommitted and report the error.

## 6. Report

Show a table of each commit's hash, message and file count. Then run `git status --short` and report
anything left uncommitted, along with the fact that nothing was pushed.
