# TRANSLATRIX PRO MFA correction

## What changed

- Local Docker development no longer forces MFA for seeded/test accounts.
- The bypass is limited to `APP_ENV=development` and controlled by `DEV_DISABLE_MFA=true`.
- New companies now default to MFA off.
- Super Admin can open **Companies → Company Details → Security** and enable or disable tenant MFA.
- Disabling both MFA options clears tenant-user MFA enrollments when the policy is saved.
- A tenant MFA policy selected during company provisioning is now persisted by the backend.
- Production remains policy-controlled because the development bypass is ignored unless `APP_ENV=development`.

## Apply and rebuild

From the folder containing `docker-compose.yml`:

```bash
docker compose -p translatrix-pro up -d --build
```

Do not use `docker compose down -v`; that would remove persistent volumes.

After rebuilding, reload the login page and sign in with the Company Admin development account. The six-digit MFA screen should no longer appear.

## Re-enable MFA testing later

Set this in the backend environment or Compose environment:

```text
DEV_DISABLE_MFA=false
```

Then rebuild. Tenant MFA settings will again be enforced.
