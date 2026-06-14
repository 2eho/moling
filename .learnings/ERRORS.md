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

## [ERR-20260615-001] apt-package-name-change-debian-trixie

**Logged**: 2026-06-15T10:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: infra | docker

### Summary
`apt-get install libffi7` failed with "Unable to locate package libffi7" because `python:3.11-slim` base image upgraded to Debian Trixie, where the `libffi` runtime package is named `libffi8`.

### Error
```
Unable to locate package libffi7
E: Unable to locate package
```

### Context
- Dockerfile for moling-server used `python:3.11-slim` as base image
- Debian Trixie (testing) renamed `libffi7` to `libffi8`
- The package name change is not documented in most Docker tutorials

### Suggested Fix
Always check the actual package name in the base image's package repository. For Debian Trixie, use `libffi8` instead of `libffi7`.

### Metadata
- Reproducible: yes
- Related Files: moling-server/Dockerfile
- See Also: LRN-20260615-001

---

## [ERR-20260615-002] pip-version-constraint-invalid-bcrypt

**Logged**: 2026-06-15T10:15:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend | deps

### Summary
`pip install` failed with "Could not find a version that satisfies the requirement bcrypt<4.1" because `pyproject.toml` specified `bcrypt<4.1` without a lower bound, and the latest bcrypt version is already > 4.1.

### Error
```
ERROR: Could not find a version that satisfies the requirement bcrypt<4.1
ERROR: No matching distribution found for bcrypt<4.1
```

### Context
- `pyproject.toml` had `"bcrypt<4.1"` (no lower bound)
- bcrypt 4.1.0 was released in 2023, latest is 4.2.0+
- pip couldn't find any version that satisfies `<4.1`

### Suggested Fix
Always specify both lower and upper bounds for version constraints: `"bcrypt>=4.0,<5.0"`.

### Metadata
- Reproducible: yes
- Related Files: moling-server/pyproject.toml
- See Also: LRN-20260615-002

---

## [ERR-20260615-003] dockerfile-node-env-order-wrong

**Logged**: 2026-06-15T10:30:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend | docker

### Summary
Next.js build failed with "Cannot find module 'typescript'" because `ENV NODE_ENV=production` was set before `npm ci`, causing devDependencies (including typescript) to be skipped.

### Error
```
npm error Cannot find module 'typescript'
```

### Context
- Dockerfile had `ENV NODE_ENV=production` before `npm ci`
- When `NODE_ENV=production`, npm ci skips devDependencies
- typescript is a devDependency, so it wasn't installed
- Next.js build requires typescript

### Suggested Fix
Always run `npm ci` before setting `NODE_ENV=production`. The correct order is:
```dockerfile
RUN npm ci
ENV NODE_ENV=production
```

### Metadata
- Reproducible: yes
- Related Files: moling-web/Dockerfile
- See Also: LRN-20260615-003

---

## [ERR-20260615-004] windows-case-insensitive-linux-case-sensitive

**Logged**: 2026-06-15T11:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend | cross-platform

### Summary
Code runs locally on Windows but fails in Docker Linux environment with "Module not found: Can't resolve './Settings.module.css'" because Windows is case-insensitive but Linux is case-sensitive.

### Error
```
Module not found: Can't resolve './Settings.module.css'
```

### Context
- Windows doesn't distinguish case in filenames
- `import styles from './Settings.module.css'` works on Windows even if the actual file is `settings.module.css`
- Linux distinguishes case, so the import fails
- This is a common cross-platform compatibility issue

### Suggested Fix
Always ensure import statements exactly match the filename (including case). Use linting rules to enforce this.

### Metadata
- Reproducible: yes (on Linux)
- Related Files: moling-web/src/app/settings/page.tsx, Settings.module.css
- See Also: LRN-20260615-004

---

## [ERR-20260615-005] nextjs-dynamic-route-slug-conflict

**Logged**: 2026-06-15T11:15:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend | nextjs

### Summary
Next.js build failed with "You cannot use different slug names for the same dynamic path ('id' !== 'projectId')" because two dynamic route folders existed in the same parent directory with different parameter names.

### Error
```
Error: You cannot use different slug names for the same dynamic path ('id' !== 'projectId')
```

### Context
- `src/app/vaults/[id]/` and `src/app/vaults/[projectId]/` both existed
- Next.js requires all dynamic routes in the same directory to use the same parameter name
- This was likely caused by a refactor that didn't clean up old files

### Suggested Fix
Ensure all dynamic route folders in the same parent directory use the same parameter name. Delete duplicates.

### Metadata
- Reproducible: yes
- Related Files: moling-web/src/app/vaults/[id]/, moling-web/src/app/vaults/[projectId]/
- See Also: LRN-20260615-005

---

## [ERR-20260615-006] pydantic-email-validator-missing

**Logged**: 2026-06-15T11:30:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend | deps

### Summary
Backend failed to start with "ImportError: email-validator is not installed, run pip install 'pydantic[email]'" because pydantic's EmailStr type requires the `email-validator` package.

### Error
```
ImportError: email-validator is not installed, run `pip install 'pydantic[email]'`
```

### Context
- `pydantic[email]` extra was not installed
- EmailStr type requires `email-validator` package
- This is a common gotcha when using pydantic's EmailStr

### Suggested Fix
Add `email-validator>=2.2.0` to `pyproject.toml` dependencies.

### Metadata
- Reproducible: yes
- Related Files: moling-server/pyproject.toml
- See Also: LRN-20260615-006

---

## [ERR-20260615-007] nginx-redirect-loop

**Logged**: 2026-06-15T14:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: infra | nginx

### Summary
Browser displayed "ERR_TOO_MANY_REDIRECTS" because Nginx `location /moling/` only matched paths with trailing slash, causing a redirect loop.

### Error
```
ERR_TOO_MANY_REDIRECTS
```

### Context
- Nginx config had `location /moling/ { ... }` (with trailing slash)
- Next.js redirected `/moling` to `/moling/` (adding trailing slash)
- Nginx didn't match `/moling` (without trailing slash), so it didn't proxy to Next.js
- This caused a redirect loop

### Suggested Fix
Use `location /moling` (without trailing slash) to match all paths starting with `/moling`.

### Metadata
- Reproducible: yes
- Related Files: /etc/nginx/conf.d/moling.conf
- See Also: LRN-20260615-007

---

## [ERR-20260615-008] docker-image-build-slow-china

**Logged**: 2026-06-15T09:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: infra | docker

### Summary
Docker image build took 17+ minutes because `apt-get update` and `pip install` used default mirrors (overseas) which are slow from China.

### Error
Build log shows slow download speeds from default mirrors.

### Context
- Default Debian/PyPI mirrors are overseas
- From China, these mirrors are very slow (17+ minutes for a build)
- This is a common issue for developers in China

### Suggested Fix
Add mirror configuration to Dockerfiles:
```dockerfile
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
```

### Metadata
- Reproducible: yes (from China)
- Related Files: moling-server/Dockerfile, moling-web/Dockerfile
- See Also: LRN-20260615-008

---
