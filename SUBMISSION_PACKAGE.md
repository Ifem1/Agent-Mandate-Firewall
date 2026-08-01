# Submission Package: Agent Mandate Firewall

## Title

Agent Mandate Firewall

## Description

AgentMandateFirewall turns delegated agent spending into a reusable consensus primitive: a principal deposits GEN, names an agent and policy, and public invoice/API evidence must satisfy that mandate before payment becomes withdrawable. Review fix: payout consensus now requires exact `approved_amount` agreement and exact `recipient_address` binding. Wrong-recipient, missing-recipient, or over-requested approvals fail closed to `UNKNOWN`; no consensus amount is silently clamped before payout. Patched StudioNet run resolved `APPROVED` with amount `1` and the exact recipient, then withdrew. Local verification: 42 direct tests passed; primitive and consumer lints are clean.

## Evidence

- Contract address: `0x34075eF5314858d5fF802bbAd3c4905b52eE1f53`
- Explorer: `https://explorer-studio.genlayer.com/address/0x34075eF5314858d5fF802bbAd3c4905b52eE1f53`
- Deploy tx: `0x1cfecb4db88c06c635efcf4ec9d848d6651b6f4e3ba86167ca17aa4eb568f6a7`

## Writes Exercised

- `open_mandate`: `0xaeb0e3fa725950d7c664031d2478c5c8e484a41e58f2176957dd2519df8f7b0b`
- `fund_mandate`: `0xe82fdff002ab0a49dd430bcaa4677fcd3ef26f7d6198563487a56cc89bdd937b`
- `pause_mandate`: `0x91b94f53d30fbf97b163be976e68bbf456fdd73e1962bd5cdfd67fbc39a84995`
- `resume_mandate`: `0x7c9740a1122cd2c7df02ddad54c75793667d48e580183165cc22acfdf4dabc35`
- `request_payment`: `0x40c2552808c6c55e0e18e820dac6f051e28cebd1855259b9812f11f811709a7e`
- `resolve_payment`: `0x9c0bbf51b52d5dd894b8385c92fe137eaec51ee1b4cf46c8d6c6910eb535da2e`
- `withdraw`: `0x4ecc9e709ed1dcd6baffcb99acd0f08b1fc80c375b0d47ef3459ab8470d1bec9`
- `reclaim_available`: `0xc20e28dd8f9f3ad4259e40c7b7231d82c8b29b1472db842866d619ec0684770a`

## Verification

- `pytest tests/direct/ -q`: `42 passed`
- `genvm-lint check contracts\agent_mandate_firewall.py --json`: `ok: true`
- `genvm-lint check examples\mandate_wallet_consumer.py --json`: `ok: true`

## Notes

All write methods were accepted on StudioNet. Storage after live resolve showed `APPROVED`, `approved_amount: 1`, and `approved_recipient: 0xa24Ddf60F3a76Ce6f3d491B657b7965Ff8cc6375`. Storage after live withdrawal shows `WITHDRAWN`, `withdrawn: true`, and `approved_amount: 0`. Receipts for `withdraw` and `reclaim_available` each emitted outbound value messages of `1` wei.
