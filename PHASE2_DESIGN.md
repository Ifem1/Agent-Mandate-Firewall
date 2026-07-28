# Agent Mandate Firewall Design

## Nondeterminism Budget

1. `gl.nondet.web.get(evidence_url)` fetches the public invoice, order record, API response, or receipt text.
2. `gl.nondet.exec_prompt(prompt)` asks validators to normalize whether the evidence supports the requested payment under the mandate policy.
3. `gl.eq_principle.prompt_comparative(...)` compares the semantic decision, not just JSON shape.

No screenshots, multi-source corroboration, embeddings, or historical watching are in the first implementation. Those can compose later; this primitive stays focused on delegated spend authorization.

## Deterministic Surface

The contract deterministically handles:

- principal, agent, and recipient address coercion
- all input caps and URL validation
- mandate ID and payment ID assignment
- deposited, available, reserved, approved, rejected, and withdrawn accounting
- per-payment amount caps
- verdict, confidence, and error normalization
- safe failure to `UNKNOWN`
- withdrawer selection
- replay and double-withdraw prevention
- callback dispatch after terminal resolution

The model is asked only what the public evidence says about the requested payment. It is never asked who should receive funds or whether to mutate state.

## Equivalence Principle

Validators compare leader and validator outputs as semantic judgements about whether the same public evidence supports the same requested payment under the same mandate. Equivalent outputs preserve the same verdict, confidence band, supported amount band, material merchant/purpose summary, and abstention reason. Different wording, ordering, casing, or style is equivalent when meaning is unchanged. A different verdict, amount band, recipient identity, merchant, purpose, policy fit, or error reason is not equivalent.

## Failure Semantics

- External fetch failure becomes `UNKNOWN`, not `REJECTED`.
- Unparseable model output becomes `UNKNOWN`.
- Low confidence becomes `UNKNOWN`.
- If the model approves more than the requested amount, deterministic code clamps to the requested amount.
- `UNKNOWN` returns the reserved amount to the mandate. It does not pay the recipient.

Safe failure is no payment. The principal's funds remain in the mandate for a future request or owner withdrawal.

## Storage Layout

All persistent data uses `TreeMap`, `DynArray`, and `@allow_storage` dataclasses. The constructor caps mandates, payments, policy text length, purpose length, URL length, summary length, and resolve attempts.

## Consumer Interface

The primitive exposes pull reads and an optional push callback. Pull reads are the stable integration surface; callbacks are finalization-side notifications for wallets that want async updates. The callback is never responsible for fund movement.

## Trust Model

The principal controls funding and mandate creation. The named agent can request payments from that mandate. Anyone can resolve a pending payment so the agent cannot censor finalization. The principal cannot edit a payment after it is requested; the agent cannot raise the amount or recipient after seeing consensus. Callback failure does not change the payment's terminal accounting.

## Funds

- Mandate deposit: held in the contract and credited to the mandate's available balance.
- Payment request: moves `amount` from mandate available to mandate reserved.
- `APPROVED`: reserved amount becomes recipient-withdrawable.
- `REJECTED`: reserved amount returns to mandate available.
- `UNKNOWN`: reserved amount returns to mandate available.
- `withdraw`: marks the payment withdrawn and emits an external transfer to the recipient.

Funds are never intentionally stranded in a terminal state.

## Latency Budget

Mandate creation and deposits are deterministic writes. Payment resolution is the only slow consensus path: one web fetch plus one LLM judgement, expected around 2-4 minutes on StudioNet and retryable if a round is undetermined.
