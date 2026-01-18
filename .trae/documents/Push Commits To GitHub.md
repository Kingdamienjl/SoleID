## Plan
- Fetch latest remote changes.
- Rebase local master onto `origin/master` and resolve any conflicts.
- Push `master` to `origin`.
- Confirm push success.

## Commands
- `git fetch origin`
- `git pull --rebase origin master`
- `git push origin master`

If conflicts occur, I will resolve them and continue the rebase, then push.