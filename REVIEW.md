# Review Response: Payment Key Replay Protection

## Review Request

Requested by Joaquin on Aug 4, 2026 14:31 — status: More information requested.

> The evidence fetch, consensus checks, and escrow flow are substantive, but the payment key currently has no replay protection: the same key can create multiple payable records, and another mandate can overwrite the global latest-payment lookup. Please scope keys to a mandate and enforce idempotency or uniqueness, then provide matching repository and deployed source.

## Fix Summary

`request_key` is now scoped per mandate and enforced unique within that mandate.

Before:

- `latest_payment_by_key` was keyed only by the raw `request_key`, global across all mandates.
- Two different mandates using the same `request_key` string would silently overwrite each other's `latest_payment_for` lookup.
- Nothing stopped the same `request_key` from being reused on the same mandate to create additional payable `PaymentRecord`s.

After:

- Every stored key is scoped as `mandate_id + "\x1f" + request_key` before being written to `latest_payment_by_key`, so two mandates can safely reuse the same human-provided key without collision.
- `request_payment` now rejects a repeat of an already-used scoped key with `"request_key already used for this mandate"`, so a caller cannot mint a second payable record under the same idempotency key.
- `latest_payment_for` now takes `(mandate_id, request_key)` and reads the scoped key, matching the write side.

## Code Changes

Changed in `contracts/agent_mandate_firewall.py`:

- `request_payment`: computes `scoped_key = clean_mandate_id + "\x1f" + clean_key`, reverts if `scoped_key` already exists in `latest_payment_by_key`, and stores under `scoped_key` instead of the raw key.
- `latest_payment_for(mandate_id, request_key)`: new signature, resolves against the scoped key.

Updated call sites and docs to match the new `latest_payment_for` signature: `README.md`, `examples/mandate_wallet_consumer.py`, `scripts/live-exercise.mjs`, `tests/direct/test_agent_mandate_firewall.py`.

## Regression Tests

Added:

- `test_request_key_rejects_replay_within_same_mandate` — same mandate, same `request_key` twice → second call reverts with `"request_key already used for this mandate"`.
- `test_request_key_is_scoped_per_mandate` — two different mandates using the identical `request_key` each get their own payment id, and `latest_payment_for` resolves the correct one per mandate.

Updated:

- `test_request_payment_reserves_budget_and_indexes_key` now asserts `latest_payment_for(mandate_id, "invoice-1")`.

Current local verification:

- `pytest tests/direct/ -q`: `44 passed`
- `genvm-lint check contracts/agent_mandate_firewall.py --json`: `ok: true`
- `genvm-lint check examples/mandate_wallet_consumer.py --json`: `ok: true`

## Deployment

Not yet redeployed. The previously reviewed deployment (`0x34075eF5314858d5fF802bbAd3c4905b52eE1f53`) still runs the pre-fix contract and does not have this patch. A fresh StudioNet deploy + live write/read exercise (matching the pattern used for the prior round) is needed before resubmission so the deployed bytecode matches this repository. That requires the deployer's funded key, which is not available in this environment — deploy and re-run `scripts/live-exercise.mjs` (or the equivalent write sequence) from your machine, then record the new contract address and transaction hashes here and in `SUBMISSION_PACKAGE.md`.
