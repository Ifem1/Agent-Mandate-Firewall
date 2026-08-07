# Submission Package: Agent Mandate Firewall

## Title

Agent Mandate Firewall

## Description

AgentMandateFirewall turns delegated agent spending into a reusable consensus primitive: a principal deposits GEN, names an agent and policy, and public invoice/API evidence must satisfy that mandate before payment becomes withdrawable. Review fix (this round): `request_key` replay protection. Keys are now scoped per mandate (`mandate_id + request_key`) so two mandates can no longer collide on the global `latest_payment_for` lookup, and reusing a key on the same mandate reverts instead of minting a second payable `PaymentRecord`. Local verification: 44 direct tests passed (2 new for this fix); primitive and consumer lints are clean.

## Evidence

- Contract address: pending redeploy — see Deployment Status below.
- Prior (pre-fix) deployment, superseded by this patch: `0x34075eF5314858d5fF802bbAd3c4905b52eE1f53`
- Prior explorer link: `https://explorer-studio.genlayer.com/address/0x34075eF5314858d5fF802bbAd3c4905b52eE1f53`

## Deployment Status

This patch has not yet been redeployed to StudioNet. The address above still runs the pre-patch contract and must not be cited as evidence for this fix. Deploy `contracts/agent_mandate_firewall.py` from this commit, re-run the write sequence below (see `scripts/live-exercise.mjs`), and replace this section with the new contract address, explorer link, and transaction hashes before resubmitting.

## Writes To Exercise On Redeploy

- `open_mandate`
- `fund_mandate`
- `pause_mandate`
- `resume_mandate`
- `request_payment` (including a repeat call with the same `request_key` on the same mandate, to show it reverts with `"request_key already used for this mandate"`)
- `resolve_payment`
- `withdraw`
- `reclaim_available`

## Verification

- `pytest tests/direct/ -q`: `44 passed`
- `genvm-lint check contracts\agent_mandate_firewall.py --json`: `ok: true`
- `genvm-lint check examples\mandate_wallet_consumer.py --json`: `ok: true`

## Notes

See `REVIEW.md` for the full review-response writeup of this round's fix.
