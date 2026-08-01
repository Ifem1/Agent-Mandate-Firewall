# Agent Mandate Firewall

`AgentMandateFirewall` is a reusable GenLayer Intelligent Contract for agent wallets and procurement systems: a principal deposits GEN, names an agent and policy, and the contract releases payment only when consensus agrees that public evidence supports the requested spend.

## The Primitive

Autonomous agents need bounded authority. A normal wallet can cap token amounts, but it cannot tell whether an invoice is actually for "customer-support SaaS" rather than a personal purchase. A backend can make that judgement, but then the principal, agent, and recipient all trust one operator. This primitive keeps the budget, the evidence judgement, and the payout state in one consensus-controlled contract.

Existing workspace contracts cover visual state, bonded claim slashing, and generic semantic callback routing. This one is a different umbrella: delegated spend authorization for agent commerce.

## How It Works

1. Principal calls payable `open_mandate` with an agent, policy, max payment, optional callback, and GEN deposit.
2. Principal may add funds with payable `fund_mandate`, or pause/resume the mandate.
3. Agent calls `request_payment`, which reserves the requested amount from mandate availability.
4. Anyone calls `resolve_payment`; validators fetch the evidence URL and judge whether it supports the requested spend under the policy.
5. Approved payments become recipient-withdrawable. Rejected or unknown payments return the reserved amount to the mandate.
6. Recipient calls `withdraw`. Principal can reclaim unused available funds with `reclaim_available`.

## Consensus Boundary

Nondeterministic calls:

- `gl.nondet.web.get(evidence_url)` fetches public invoice/order/API evidence.
- `gl.nondet.exec_prompt(...)` classifies the evidence against the mandate.
- `gl.eq_principle.prompt_comparative(...)` compares the semantic judgement.

Deterministic code handles all roles, caps, accounting, state transitions, result normalization, callback dispatch, and value transfer emission. The model never decides who receives funds; it only reports what the evidence supports.

Equivalence principle:

> Compare leader and validator outputs as semantic judgements about whether the same public evidence supports the same requested agent payment under the same mandate policy. Equivalent outputs preserve the same verdict, confidence band, exact approved_amount integer, exact recipient_address, material merchant or service summary, policy-fit reason, and abstention reason. Different wording, ordering, casing, or style is equivalent when meaning is unchanged. A different verdict, approved amount, recipient address, named recipient, merchant, purpose, policy fit, or error reason is not equivalent. UNKNOWN is equivalent only to UNKNOWN for substantially the same reason, such as fetch failure, ambiguity, insufficient evidence, unreadable evidence, or missing exact amount, recipient, or purpose details.

## Review Fix: Exact Payout Consensus

The rejected version allowed consensus equivalence over a supported amount band while the contract later transferred the exact `approved_amount`. It also did not require the recipient address to appear in the judgement. That could let validator-compatible outputs approve different payable sums or fail to bind the evidence to the recipient.

The patched contract fixes this by requiring the consensus judgement to include:

- exact integer `approved_amount`
- exact `recipient_address`
- evidence-backed merchant/service summary
- policy-fit reason

An `APPROVED` result now fails closed to `UNKNOWN` unless `recipient_address` exactly equals the stored payment recipient. If the model returns an amount greater than the requested payment, the result also becomes `UNKNOWN`; the contract no longer clamps a different consensus amount into the transferred amount.

## Safety Rules

- Fetch failure is `UNKNOWN`, never `REJECTED`.
- Low-confidence approvals become `UNKNOWN`.
- Unparseable model output becomes `UNKNOWN`.
- Recipient-free or wrong-recipient approvals become `UNKNOWN`.
- Over-requested approvals become `UNKNOWN`; the contract never silently changes the consensus amount before payout.
- State is written before value leaves.
- `APPROVED` funds go to the recipient; `REJECTED` and `UNKNOWN` funds return to the mandate; unused mandate funds can be reclaimed by the principal.

## API

Writes:

- `open_mandate(agent, policy, max_payment, callback)` payable
- `fund_mandate(mandate_id)` payable
- `pause_mandate(mandate_id)`
- `resume_mandate(mandate_id)`
- `request_payment(mandate_id, amount, recipient, purpose, evidence_url, request_key="")`
- `resolve_payment(payment_id)`
- `withdraw(payment_id)`
- `reclaim_available(mandate_id, amount)`

Views:

- `mandate_status(mandate_id)`
- `payment_status(payment_id)`
- `get_mandate(mandate_id)`
- `get_payment(payment_id)`
- `withdrawable(payment_id, account)`
- `latest_payment_for(request_key)`
- `get_config()`

## Consumer

`examples/mandate_wallet_consumer.py` shows an agent wallet contract that submits payment requests, asks for resolution, and receives optional callback notifications without embedding evidence fetching, prompts, parsing, or accounting.

## Reuse From Another Project

Other projects can use the deployed contract as-is. They do not need a private copy or a redeploy unless they want different contract code. Each project creates its own isolated mandate inside the shared contract:

1. The project principal calls payable `open_mandate(agent, policy, max_payment, callback)` with its own policy and budget.
2. The same principal can add more funds with payable `fund_mandate(mandate_id)`.
3. Only the configured `agent` can call `request_payment(...)` for that mandate.
4. Anyone can call `resolve_payment(payment_id)`, so the agent cannot censor settlement.
5. If the payment is `APPROVED`, the recipient calls `withdraw(payment_id)`.
6. If the payment is `REJECTED` or `UNKNOWN`, the reserved funds return to mandate availability.
7. The principal can recover unused available funds with `reclaim_available(mandate_id, amount)`.

Minimal import surface:

```python
@gl.contract_interface
class IAgentMandateFirewall:
    class View:
        def payment_status(self, payment_id: str) -> str: ...
        def get_payment(self, payment_id: str) -> dict: ...
        def withdrawable(self, payment_id: str, account: str) -> u256: ...
        def latest_payment_for(self, request_key: str) -> str: ...

    class Write:
        def request_payment(
            self,
            mandate_id: str,
            amount: int,
            recipient: str,
            purpose: str,
            evidence_url: str,
            request_key: str,
        ) -> str: ...

        def resolve_payment(self, payment_id: str) -> None: ...
```

The important nuance is intentional: a project must either open its own mandate or be configured as the agent on an existing mandate. That keeps one shared deployed primitive from becoming one shared uncontrolled pool.

## Verification

Local:

```powershell
pytest tests/direct/ -q
genvm-lint check contracts\agent_mandate_firewall.py --json
genvm-lint check examples\mandate_wallet_consumer.py --json
```

Latest local result: `42 passed`; both lints `ok: true`.

StudioNet:

- Contract: `0x34075eF5314858d5fF802bbAd3c4905b52eE1f53`
- Explorer: https://explorer-studio.genlayer.com/address/0x34075eF5314858d5fF802bbAd3c4905b52eE1f53
- Deploy: `0x1cfecb4db88c06c635efcf4ec9d848d6651b6f4e3ba86167ca17aa4eb568f6a7`
- `open_mandate`: `0xaeb0e3fa725950d7c664031d2478c5c8e484a41e58f2176957dd2519df8f7b0b`
- `fund_mandate`: `0xe82fdff002ab0a49dd430bcaa4677fcd3ef26f7d6198563487a56cc89bdd937b`
- `pause_mandate`: `0x91b94f53d30fbf97b163be976e68bbf456fdd73e1962bd5cdfd67fbc39a84995`
- `resume_mandate`: `0x7c9740a1122cd2c7df02ddad54c75793667d48e580183165cc22acfdf4dabc35`
- `request_payment`: `0x40c2552808c6c55e0e18e820dac6f051e28cebd1855259b9812f11f811709a7e`
- `resolve_payment`: `0x9c0bbf51b52d5dd894b8385c92fe137eaec51ee1b4cf46c8d6c6910eb535da2e`
- `withdraw`: `0x4ecc9e709ed1dcd6baffcb99acd0f08b1fc80c375b0d47ef3459ab8470d1bec9`
- `reclaim_available`: `0xc20e28dd8f9f3ad4259e40c7b7231d82c8b29b1472db842866d619ec0684770a`

Measured live result: payment `amf-p-1` against `https://raw.githubusercontent.com/Ifem1/Agent-Mandate-Firewall/main/evidence/example-domain-payment.txt` resolved `APPROVED` with `HIGH` confidence, `approved_amount: 1`, and `approved_recipient: 0xa24Ddf60F3a76Ce6f3d491B657b7965Ff8cc6375`. After withdrawal, `get_payment` shows `status: WITHDRAWN`, `withdrawn: true`, and `approved_amount: 0`.

## Honest Limits

This first version deliberately keeps the nondeterminism budget short; it does not use screenshots, vector search, factories, or sandboxed caller code. It uses the GenLayer capabilities most relevant to this primitive: public web evidence, LLM consensus, native GEN custody, optional contract callback composition, and EVM-style recipient transfers.

StudioNet confirmed the value-moving paths. The `withdraw` receipt emitted an outbound value message of `1` wei to the recipient, and `reclaim_available` emitted an outbound value message of `1` wei to the principal. The live demo intentionally left `13` wei of mandate budget available. Explorer displays tiny wei balances as `0.000000 GEN` because it rounds at GEN precision.
