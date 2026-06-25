# Error Handling

Goal: predictable, observable failure with no silent surprises.

- **MUST NOT** swallow exceptions. Log with context or rethrow — never an empty catch.
- **MUST** use specific exception types, not bare `Exception` / `Error` / `catch (e)`.
- **MUST** validate inputs at system boundaries (API endpoints, public function params).
- **SHOULD** fail fast with clear messages — don't let bad state propagate deep into the system.
- **SHOULD** handle errors at the level that can meaningfully recover; don't catch what you can't act on.
- **MUST** log enough context to diagnose (what, when, why) and **MUST NOT** log secrets or PII.

```
❌ try { processPayment(amount); } catch (e) {}

✅ try {
       validateAmount(amount)
       processPayment(amount)
   } catch (PaymentError as e) {
       logger.error(f"Payment failed for amount={amount}: {e}")
       raise PaymentProcessingError() from e
   }
```

## Async & external calls

- **MUST** set timeouts on network/external API calls.
- **SHOULD** make retries idempotent and bounded (cap attempts, use backoff).
- **SHOULD** surface user-facing failures gracefully rather than crashing the flow (see [web frontend](../stacks/web-frontend.md) error boundaries).

## User-facing surfaces

- **MUST** show loading and error states for any async/data-fetching UI — never a blank screen or infinite spinner.
