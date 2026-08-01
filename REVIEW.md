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

Patched StudioNet contract:

`0x34075eF5314858d5fF802bbAd3c4905b52eE1f53`

Explorer:

https://explorer-studio.genlayer.com/address/0x34075eF5314858d5fF802bbAd3c4905b52eE1f53

Live transaction evidence:

- Deploy: `0x1cfecb4db88c06c635efcf4ec9d848d6651b6f4e3ba86167ca17aa4eb568f6a7`
- `open_mandate`: `0xaeb0e3fa725950d7c664031d2478c5c8e484a41e58f2176957dd2519df8f7b0b`
- `fund_mandate`: `0xe82fdff002ab0a49dd430bcaa4677fcd3ef26f7d6198563487a56cc89bdd937b`
- `pause_mandate`: `0x91b94f53d30fbf97b163be976e68bbf456fdd73e1962bd5cdfd67fbc39a84995`
- `resume_mandate`: `0x7c9740a1122cd2c7df02ddad54c75793667d48e580183165cc22acfdf4dabc35`
- `request_payment`: `0x40c2552808c6c55e0e18e820dac6f051e28cebd1855259b9812f11f811709a7e`
- `resolve_payment`: `0x9c0bbf51b52d5dd894b8385c92fe137eaec51ee1b4cf46c8d6c6910eb535da2e`
- `withdraw`: `0x4ecc9e709ed1dcd6baffcb99acd0f08b1fc80c375b0d47ef3459ab8470d1bec9`
- `reclaim_available`: `0xc20e28dd8f9f3ad4259e40c7b7231d82c8b29b1472db842866d619ec0684770a`

Live resolved payment evidence:

- Payment id: `amf-p-1`
- Evidence URL: `https://raw.githubusercontent.com/Ifem1/Agent-Mandate-Firewall/main/evidence/example-domain-payment.txt`
- Resolved status: `APPROVED`
- Confidence: `HIGH`
- Requested amount: `1`
- Approved amount: `1`
- Recipient: `0xa24Ddf60F3a76Ce6f3d491B657b7965Ff8cc6375`
- Approved recipient: `0xa24Ddf60F3a76Ce6f3d491B657b7965Ff8cc6375`
- Final status after withdrawal: `WITHDRAWN`
