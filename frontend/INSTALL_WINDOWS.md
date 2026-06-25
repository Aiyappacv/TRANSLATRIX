# Windows installation

Requirements:
- Node.js 22 LTS recommended (or Node.js 20.19+)
- npm 10+

From PowerShell in this folder:

```powershell
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
npm cache verify
npm ci --include=dev --no-audit --no-fund
npm run dev
```

The lockfile in this package uses the public npm registry only.
