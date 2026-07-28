# Decision Record: Agent Mandate Firewall

## Chosen Primitive

`AgentMandateFirewall` is a reusable Intelligent Contract primitive for delegated agent spending. A principal deposits GEN into a mandate, gives an agent a natural-language purchasing or reimbursement policy, and lets any resolver ask consensus whether public evidence supports a proposed payment. If consensus approves, deterministic code lets the recipient withdraw; if evidence is rejected or unknown, the funds return to the mandate.

This is intentionally different from the existing workspace contracts:

- Not visual proof: it uses text/API evidence, not screenshots.
- Not bonded claim slashing: the claimant is not staked and slashed; a principal-funded mandate controls delegated spend.
- Not a semantic callback router: the core outcome is a budgeted payment authorization, with callback as an optional side effect.

## Candidate Generation

1. Agent mandate spend firewall: deposits GEN into reusable agent budgets and releases payment only when public evidence matches a delegated policy; imported by agent wallets and procurement agents.
2. Cross-chain intent receipt gate: records an EVM tx hash and declared purpose, then gates a downstream IC state transition on whether public metadata matches the stated intent; imported by accountability contracts.
3. Policy-family vector registry: stores approved policy families and rejects clauses that are semantically outside the nearest family; imported by governance modules.
4. Deterministic rule capsule runner: stores caller-supplied scoring scripts and runs them in a sandbox after consensus normalizes evidence; imported by compliance contracts.
5. Contract factory for micro-arbitration vaults: deploys isolated configured vaults for projects that need immutable settings; imported by marketplaces.
6. API attestation normalizer: fetches signed API responses and normalizes messy records into agreed categories; imported by insurance and logistics contracts.
7. Agent authority revocation monitor: checks public agent registry pages for revocation or suspension signals before permitting calls; imported by agent identity systems.
8. Semantic license compatibility gate: judges whether a submitted license/terms page is compatible with a project policy; imported by dataset and software registries.
9. Revenue-split evidence meter: releases pooled GEN across contributors based on consensus-normalized contribution evidence; imported by grant programs.
10. Public counterparty sanctions gate: fetches public compliance records and abstains unless consensus can safely classify a counterparty status; imported by guarded wallets.
11. Semantic duplicate registry: embeds artifact descriptions and rejects near-duplicates; imported by grant and app registries.
12. Covenant-aware upgrade guard: blocks an upgrade unless public release notes and code metadata match immutable upgrade covenants; imported by upgradeable IC systems.

Capability coverage:

- Live web/API access: 1, 2, 6, 7, 8, 10, 12
- Native value: 1, 5, 9
- Contract-to-contract composition: 1, 2, 5, 12
- EVM interop: 1, 2, 10
- Embeddings/vector search: 3, 11
- Sandboxed evaluation: 4
- Contract factories: 5

The two most similar candidates are `Agent mandate spend firewall` and `Revenue-split evidence meter`. They are different primitives: the mandate firewall decides whether one requested payment is inside a principal's delegated policy, while the revenue meter allocates a pool across many contributors.

If web access did not exist, the strongest pick would be the deterministic rule capsule runner, because sandboxing custom deterministic rules is structurally different from web oracles. I did not pick it because it does not by itself prove a real-world condition; it needs another primitive to supply normalized evidence.

The strongest discarded candidate is the cross-chain intent receipt gate. It is sharp, but Studio currently limits EVM contract interaction beyond value transfers, which makes the live run less convincing this week. The mandate firewall can still use EVM-style EOA payout while fully exercising its own state machine on StudioNet.

## Gate Check

- **Gate A: counterfactual.** Without GenLayer, an agent wallet backend or the principal's server decides whether a payment fits the mandate. The recipient and principal must trust that operator not to misread the evidence, overpay, or censor valid payments.
- **Gate B: trust problem.** The principal funds the mandate, the agent requests payment, and the recipient wants settlement. The agent may control some submitted text; the recipient may benefit from broad interpretations; the principal wants policy limits enforced. One answer controls money.
- **Gate C: judgement.** The core question is semantic: does public evidence show that this requested amount, recipient, purpose, and merchant fit the mandate policy? A deterministic parser cannot decide whether an invoice is within "approved security-audit tooling" or "customer-support travel".
- **Gate D: importability.** Agent wallets import a small interface: fund a mandate, submit payment requests, resolve them, read the status, and let recipients withdraw. The consumer does not embed evidence fetching, prompt design, abstention, or payout state.
- **Gate E: consequential decision.** Consensus gates native GEN. Approved requests create withdrawable value for the recipient; rejected and unknown requests return the reserved amount to the mandate.
- **Gate F: originality.** It is not a frontend, not a format validator, not text-only advice, not a page-change watcher, not multi-source corroboration, and not a re-skin of the existing three workspace primitives. It is a delegated authority/payment-control primitive for agent commerce.

## Consumer Sketch

```python
@gl.contract_interface
class IAgentMandateFirewall:
    class View:
        def payment_status(self, payment_id: str) -> str: ...
        def withdrawable(self, payment_id: str, account: str) -> u256: ...
    class Write:
        def request_payment(self, mandate_id: str, amount: int, recipient: str, purpose: str, evidence_url: str, request_key: str) -> str: ...
        def resolve_payment(self, payment_id: str) -> None: ...
        def withdraw(self, payment_id: str) -> None: ...
```

An agent wallet owns the user experience and imports this primitive as the policy/firewall layer. The wallet never asks an off-chain service to decide whether money should move.
