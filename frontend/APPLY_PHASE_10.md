# Apply Phase 10 Update Only

This package contains only files added or modified for Phase 10. It is not the complete project.

## Apply

1. Extract this folder.
2. Copy its contents into the root of your existing Phase 0–9 project.
3. Allow matching files to be replaced.
4. Keep every `.tsx` extension exactly as provided.
5. From the project root run:

```bash
npm install
npm run build
npm run lint
npm test
npm run dev
```

A backend-authenticated user with the Super Admin role is redirected to `/super-admin/dashboard` after login.

## Modified existing files

- `src/app/router.tsx`
- `src/components/common/Breadcrumbs.tsx`
- `src/components/layout/Topbar.tsx`
- `src/layouts/SuperAdminLayout.tsx`
- `src/pages/auth/LoginPage.tsx`
- `src/services/superAdminApi.ts`
- `src/types/index.ts`
- `src/utils/permissions.ts`

## New files and folders

- `PHASE_10_COMPLETED.md`
- `src/app/superAdminRouteConfig.ts`
- `src/components/super-admin/`
- `src/mocks/phase10MockData.ts`
- `src/pages/super-admin/`
- `src/tests/unit/phase10.test.ts`
- `src/types/superAdmin.ts`

## Validation performed

- TypeScript production build: passed
- ESLint: passed with zero warnings
- Vitest: 17 tests passed
- Production dependency audit: zero known vulnerabilities
