# Errors

Command failures and integration errors.

---

## [ERR-20260614-001] git-push-credential-helper-windows

**Logged**: 2026-06-14T15:25:54+08:00
**Priority**: high
**Status**: resolved
**Area**: infra | config

### Summary
`git push` failed with exit code 128 and "invalid credentials" because the credential helper path with Windows backslashes was mangled by Git Bash's `sh.exe`.

### Error
```
C:\Users\Admin\AppData\Local\Temp\gh_cli\bin\gh.exe auth git-credential erase: line 1: C:UsersAdminAppDataLocalTempgh_clibin\gh.exe: command not found
remote: invalid credentials
fatal: Authentication failed for 'https://github.com/2eho/moling.git/'
```

### Context
- Windows 10/11, Git for Windows (2.47.0), gh CLI (2.62.0)
- Git's global config had credential.helper set with Windows backslash paths
  - `!'C:\Users\Admin\AppData\Local\Temp\gh_cli\bin\gh.exe' auth git-credential`
  - Git ran this via `sh.exe` which consumed backslashes as escape characters

### Suggested Fix
Always use forward slashes in git credential helper paths on Windows:
```
git config --global credential.helper "!C:/Users/Admin/AppData/Local/Temp/gh_cli/bin/gh.exe auth git-credential"
```

### Metadata
- Reproducible: yes
- Related Files: ~/.gitconfig
- See Also: LRN-20260614-001

---
