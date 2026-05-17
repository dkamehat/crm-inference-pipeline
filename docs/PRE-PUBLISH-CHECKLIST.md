# Pre-Publish Checklist

> Run through this before pushing to a public branch or creating a public PR.
> The pre-commit hook and the GitHub Actions workflow automate most of this — but human review still catches things automation misses.

---

## 1. Automated checks

```bash
# Confirm hook is active
git config core.hooksPath
# Expected output: .githooks

# Re-run hook manually on all tracked files
.githooks/pre-commit
```

If you want to verify the GitHub Actions workflow runs locally:

```bash
# Requires: https://github.com/nektos/act
act -W .github/workflows/check-personal-info.yml
```

---

## 2. Manual grep — the human review

Run these greps. They should all return **empty**.

```bash
# Personal identifiers (the real name belongs in the GitHub handle and README author line only;
# anywhere else it appears is a candidate for review)
grep -rin "kamekichii\|亀畑" . --include='*.md' --include='*.ipynb' --include='*.py' --include='*.sql' --include='*.yml'

# Current employer
grep -rin "demae\|出前館\|デマエカン" . --include='*.md' --include='*.ipynb' --include='*.py' --include='*.sql' --include='*.yml'

# Specific previous employers
grep -rin "rakuten payment\|amazon business japan\|otaru" . --include='*.md' --include='*.ipynb' --include='*.py' --include='*.sql' --include='*.yml'

# Active selection processes (these change over time — keep this list updated locally)
grep -rin "komoju\|sakana ai\|sansan\|smarthr" . --include='*.md' --include='*.ipynb' --include='*.py' --include='*.sql' --include='*.yml'

# Internal stakeholders
grep -rin "立石\|藤田\|君塚\|熊久保\|二宮\|根岸" . --include='*.md' --include='*.ipynb' --include='*.py' --include='*.sql' --include='*.yml'

# Internal project naming
grep -rin "お店価格\|PJ-W" . --include='*.md' --include='*.ipynb' --include='*.py' --include='*.sql' --include='*.yml'

# Specific internal numbers that identify the employer
grep -rin "60,000 merchants\|60K merchants\|105 sales reps\|~105 reps" . --include='*.md' --include='*.ipynb' --include='*.py' --include='*.sql' --include='*.yml'

# Secrets and API key patterns
grep -rinE "api[_-]?key|secret|password|sk_live|pk_live|AKIA[0-9A-Z]{16}" . --include='*.md' --include='*.ipynb' --include='*.py' --include='*.sql' --include='*.yml' --include='*.json' --include='*.env*'

# Local file paths
grep -rin "C:\\\\Users\\\\dkame\|/c/Users/dkame" .
```

---

## 3. File-type danger check

These files should **never** exist in the repository:

```bash
find . -name '.env' -o -name '.env.*' \
       -o -name '*.sqlite' -o -name '*.sqlite-journal' \
       -o -name 'CLAUDE.md' -o -name 'CLAUDE.local.md' \
       -o -path '*/.wrangler/*' \
       -o -path '*/.claude/settings.local.json' \
       -o -path '*/notes/*'
```

If any output appears, **stop and resolve** before pushing.

---

## 4. Repository-level visibility check

```bash
gh repo view --json visibility,isTemplate
```

For a public repo, confirm the description is appropriate and the README's first paragraph contains no sensitive context.

---

## 5. Final pre-push review

Before `git push`:

- [ ] Did you `git diff` the last commit yourself?
- [ ] Did you click through to each modified file on the GitHub web UI after pushing to a branch?
- [ ] Is the commit message free of personal context?
- [ ] If you added images, did you check EXIF / metadata for location info? (`exiftool image.png`)
- [ ] If you added a notebook, did you check the executed output cells for accidentally-leaked dataframe contents?

---

## 6. Emergency procedures

### If you've already pushed sensitive information

1. **Do NOT delete the repository.** Deletion is irreversible and removes audit trail. Make it Private first.
   ```bash
   gh repo edit --visibility private --accept-visibility-change-consequences
   ```

2. **Rotate any leaked secrets immediately.** Revoke API keys, change passwords, regenerate webhooks.

3. For sensitive content removal from history (rare, considered):
   - `git filter-repo` is the modern tool (not `git filter-branch`)
   - Note that anyone who already cloned the repo still has the data
   - Treat the leaked information as **publicly compromised** regardless of cleanup

4. Create a new repository with a clean history if extensive cleanup is needed.

---

## 7. Notes on the automated checks

The pre-commit hook in `.githooks/pre-commit` and the workflow in `.github/workflows/check-personal-info.yml` use the same pattern list. To add a new pattern:

1. Add it to both files (they share a `SELF_EXCLUDE_BEGIN ... SELF_EXCLUDE_END` block)
2. Re-run `.githooks/pre-commit` on existing files to verify nothing breaks
3. Commit both files together

The "self-exclude" design means these script files themselves are exempt from their own pattern check — otherwise the script would block its own commit.
