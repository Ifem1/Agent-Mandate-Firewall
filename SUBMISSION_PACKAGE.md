# Submission Package: Agent Mandate Firewall

## Title

Agent Mandate Firewall

## Description

AgentMandateFirewall turns delegated agent spending into a reusable consensus primitive: a principal deposits GEN, names an agent and policy, and public invoice/API evidence must satisfy that mandate before payment becomes withdrawable. Review fix: payout consensus now requires exact `approved_amount` agreement and exact `recipient_address` binding. Wrong-recipient, missing-recipient, or over-requested approvals fail closed to `UNKNOWN`; no consensus amount is silently clamped before payout. Local verification: 42 direct tests passed; primitive and consumer lints are clean.

## Evidence

- Contract address: `0xdaabB4b3FD53eA402AC7aF71213fB64eFb6b72B5`
- Deploy tx: `0x7044cb800f975808498da43c0fc08e8e5d6212c75d519fa796bd312ab7ca346a`
- Explorer base: `https://genlayer-explorer.vercel.app`

## Writes Exercised

- `open_mandate`: `0x8cedf858e94756b8aee429b52099715c673d79617739c8fb7591fb39b88290ea`
- `fund_mandate`: `0x5de09c3259db7783cd3bb5ad3f929878978ff3cbfa48a70ce2dbd104246a8937`
- `pause_mandate`: `0x86a05d14b551428ea0ec03ea7356a350375e7b5c87aca8eeaf20b2165b2256d9`
- `resume_mandate`: `0x168ab2c30a550b2ab27d770c6ffad62b801d98790e86fa32f580d55eb9dcbf9b`
- `request_payment`: `0x66b452c2f9a6e417205cf07b4654be8824c6e31bfac82cb4a33c2c0c617983b8`
- `resolve_payment`: `0xfa9defd344e1eba9a357b627e1cb47fb4fc43dea065fbf1f9755c47e57a89e1a`
- `withdraw`: `0x3c6c789230a541cd3263ccf3f73a7034ea762466e00ac433ae44ba9125e52a2e`
- `reclaim_available`: `0x1a421e9da2f11952c4b6e7b4e30ab8f920c505f1a93c4305b792b8cf40f1041c`

## Verification

- `pytest tests/direct/ -q`: `42 passed`
- `genvm-lint check contracts\agent_mandate_firewall.py --json`: `ok: true`
- `genvm-lint check examples\mandate_wallet_consumer.py --json`: `ok: true`

## Notes

All write methods were accepted on StudioNet. Storage after live withdrawal shows `WITHDRAWN`, `withdrawn: true`, and `approved_amount: 0`. Receipts for `withdraw` and `reclaim_available` each emitted outbound value messages of `1` wei. The contract still holds `13` wei because that amount remains as unused mandate budget.
