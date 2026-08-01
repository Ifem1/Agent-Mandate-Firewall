# Review Response: Exact Payout And Recipient Binding

## Review Request

The team rejected the previous Agent Mandate Firewall version because payout consensus was not safe enough:

> The payout consensus is not safe yet: the equivalence rule accepts a supported amount band, but the exact approved amount is later transferred, so validator-compatible outputs can move different sums. The recipient address is also absent from the judgment. Please require agreement on the exact payable amount and include and bind the recipient to the evidence before resubmitting matching source and deployment.

## Fix Summary

The patched contract requires consensus on the exact payable amount and the exact recipient address.

Before:

- Equivalence allowed a supported amount band.
- The LLM result did not include `recipient_address`.
- The parser clamped over-requested `approved_amount` down to the requested amount.

After:

- Equivalence requires the exact integer `approved_amount`.
- The prompt requires `recipient_address`.
- `APPROVED` fails closed to `UNKNOWN` unless `recipient_address` exactly equals the stored payment recipient.
- Over-requested approvals fail closed to `UNKNOWN`; the contract no longer clamps one consensus amount into a different transferred amount.

## Code Changes

Changed in `contracts/agent_mandate_firewall.py`:

- Updated `MANDATE_EQUIVALENCE_PRINCIPLE` from amount-band agreement to exact approved amount and exact recipient agreement.
- Added `approved_recipient` storage to `PaymentRecord`.
- Added recipient parsing and deterministic recipient equality checks.
- Passed the requested recipient into `_judge_payment`, `_build_prompt`, and `_parse_result`.
- Updated the prompt to require evidence-backed `recipient_address`.
- Removed silent amount clamping for over-requested approvals.

## Regression Tests

Added or updated direct tests:

- `test_over_requested_approval_is_unknown_not_clamped`
- `test_approval_requires_exact_recipient_binding`
- `test_approval_requires_recipient_in_judgement`

Current local verification:

- `pytest tests/direct/ -q`: `42 passed`
- `genvm-lint check contracts/agent_mandate_firewall.py --json`: `ok: true`
- `genvm-lint check examples/mandate_wallet_consumer.py --json`: `ok: true`

## Deployment

Patched StudioNet deployment will be recorded here after the matching source is deployed and exercised.
