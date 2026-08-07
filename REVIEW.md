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
- `latest_payment_for(mandate_id, request_key)`: new two-argument signature, resolves against the scoped key.

Updated call sites and docs to match the new signature: `README.md`, `examples/mandate_wallet_consumer.py`, `scripts/live-exercise.mjs`, `tests/direct/test_agent_mandate_firewall.py`.

## Regression Tests

Added:

- `test_request_key_rejects_replay_within_same_mandate` — same mandate, same `request_key` twice → second call reverts with `"request_key already used for this mandate"`.
- `test_request_key_is_scoped_per_mandate` — two different mandates using the identical `request_key` each get their own payment id, and `latest_payment_for` resolves the correct one per mandate.

Updated:

- `test_request_payment_reserves_budget_and_indexes_key` now asserts `latest_payment_for(mandate_id, "invoice-1")`.

Local verification:

- `pytest tests/direct/ -q`: `44 passed`
- `genvm-lint check contracts/agent_mandate_firewall.py --json`: `ok: true`
- `genvm-lint check examples/mandate_wallet_consumer.py --json`: `ok: true`

## Deployment

New StudioNet contract (patched, this fix):

`0xD5259E2c6e2D0433e47d775769085de3A09ADc4c`

Explorer:

https://explorer-studio.genlayer.com/address/0xD5259E2c6e2D0433e47d775769085de3A09ADc4c

Live transaction evidence:

- Deploy: `0xa6032c2e5353a05cb90781bcf6c5f06c9851714a093e7673950f1056cb6266ca`
- `open_mandate`: `0xb52ab7590d43ca1e947bf72bfa4745edf55f873f5d973c1b596cc8d3da64c038`
- `fund_mandate`: `0xee58ce5feec872ed274c69cb45c502ae2ed79bb46789a49b1d18520f4fa6f6ab`
- `pause_mandate`: `0x7e1c02f2ff103379825a672e9800671049658f5d036a6018b8a16815d93419ee`
- `resume_mandate`: `0x6b2d12e8af0b81682b063382394a777be1ed6bde800d3c8870cdd6ce7955f0ec`
- `request_payment`: `0x5ede6634a972bf4851824cb5491d39212b30b4e802241a9c8bc34c5cd2c5130d`
- `reclaim_available`: `0x852c2469c391d12084b33cec19605051ab85679c9eb2dc0a4a9348d18bcd5a06`
- `resolve_payment` (APPROVED): `0x115d305061529300ed44eec81800b0a17a8b5104986c8a8d6e8cfdb271c0ce54`
- `withdraw`: `0x346dceb78cdac23150b629c121fdddc7e86f66a03fe6a9afdfc4244575f6d5dd`

Live resolved payment evidence:

- Payment id: `amf-p-1`
- Evidence URL: `https://raw.githubusercontent.com/Ifem1/Agent-Mandate-Firewall/main/evidence/example-domain-payment.txt`
- Resolved status: `APPROVED`
- Confidence: `HIGH`
- Requested amount: `1` wei
- Approved amount: `1` wei
- Recipient: `0xc5b5755fc0338684346380c1d16e78049273bc97`
- Approved recipient: `0xc5b5755fc0338684346380c1d16e78049273bc97`
- Merchant summary: `Example Domain Documentation Service - documentation verification`
- Policy reason: `Evidence identifies the public documentation check service, exact amount of 1 wei, matching recipient address, and matching purpose; this fits the mandate for tiny payments for public web documentation checks.`
- Final status after withdrawal: `WITHDRAWN`
- `withdrawn: true`, `approved_amount: 0` (zeroed after payout)

## Notes on UNDETERMINED Rounds

Several `resolve_payment` calls returned `UNDETERMINED` with `MAJORITY_DISAGREE` before the successful round. This is normal StudioNet behavior: when validators fetch the same evidence URL and run the same prompt independently, transient consensus rounds can fail to reach quorum before eventually succeeding. The contract is retryable by design — `UNDETERMINED` writes no state, so any caller can re-invoke `resolve_payment`. This is documented in the README's honest limits section.
