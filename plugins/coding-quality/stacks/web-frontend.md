# Stack Overlay — Web Frontend

Layered on top of all core rules. Covers the traps that bite shipped web apps.

## Resilient data fetching

- **MUST** wrap data-fetching components in error boundaries — one failed fetch must not blank the whole app.
- **MUST** render explicit loading and error states for every async operation. No infinite spinners, no blank screens.
- **SHOULD** handle empty states distinctly from loading and error.

```
❌ const { data } = useQuery();  return <List items={data} />;   // crashes on error/undefined
✅ if (isLoading) return <Spinner />;
   if (error)     return <ErrorState onRetry={refetch} />;
   if (!data?.length) return <EmptyState />;
   return <List items={data} />;
```

## Legal / privacy — you are a data processor

**Why this rule exists:** the moment a form collects an email, you are processing personal
data. Missing a privacy policy is a GDPR exposure and a fast way to get banned from ad
platforms or payment processors (Stripe), long before any lawsuit.

- **MUST** publish a Privacy Policy (e.g. `/privacy`) before collecting any personal data, including email signups.
- **MUST** publish Terms of Service when taking payments or accounts.
- **SHOULD** add a cookie/consent notice if serving EU users with non-essential cookies/analytics.
- **SHOULD** collect the minimum data needed and state retention/usage in the policy.

## General hardening

- **MUST** escape/encode output to prevent XSS (see [security](../rules/03-security.md)).
- **MUST NOT** put secrets/API keys in client-side code or bundles.
- **SHOULD** validate on the server even when validating on the client — client checks are UX, not security.
- **SHOULD** set sensible security headers (CSP, HSTS) for production deployments.
