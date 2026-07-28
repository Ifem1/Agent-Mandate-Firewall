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

> Compare leader and validator outputs as semantic judgements about whether the same public evidence supports the same requested agent payment under the same mandate policy. Equivalent outputs preserve the same verdict, confidence band, supported amount band, material merchant or service summary, policy-fit reason, and abstention reason. Different wording, ordering, casing, or style is equivalent when meaning is unchanged. A different verdict, amount band, named recipient, merchant, purpose, policy fit, or error reason is not equivalent. UNKNOWN is equivalent only to UNKNOWN for substantially the same reason, such as fetch failure, ambiguity, insufficient evidence, unreadable evidence, or missing amount/purpose details.

## Safety Rules

- Fetch failure is `UNKNOWN`, never `REJECTED`.
- Low-confidence approvals become `UNKNOWN`.
- Unparseable model output becomes `UNKNOWN`.
- The model cannot approve more than the requested amount; deterministic code clamps it.
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

Latest local result: `40 passed`; both lints `ok: true`.

StudioNet:

- Contract: `0xdaabB4b3FD53eA402AC7aF71213fB64eFb6b72B5`
- Deploy: `0x7044cb800f975808498da43c0fc08e8e5d6212c75d519fa796bd312ab7ca346a`
- `open_mandate`: `0x8cedf858e94756b8aee429b52099715c673d79617739c8fb7591fb39b88290ea`
- `fund_mandate`: `0x5de09c3259db7783cd3bb5ad3f929878978ff3cbfa48a70ce2dbd104246a8937`
- `pause_mandate`: `0x86a05d14b551428ea0ec03ea7356a350375e7b5c87aca8eeaf20b2165b2256d9`
- `resume_mandate`: `0x168ab2c30a550b2ab27d770c6ffad62b801d98790e86fa32f580d55eb9dcbf9b`
- `request_payment`: `0x66b452c2f9a6e417205cf07b4654be8824c6e31bfac82cb4a33c2c0c617983b8`
- `resolve_payment`: `0xfa9defd344e1eba9a357b627e1cb47fb4fc43dea065fbf1f9755c47e57a89e1a`
- `withdraw`: `0x3c6c789230a541cd3263ccf3f73a7034ea762466e00ac433ae44ba9125e52a2e`
- `reclaim_available`: `0x1a421e9da2f11952c4b6e7b4e30ab8f920c505f1a93c4305b792b8cf40f1041c`

Measured live result: payment `amf-p-1` against `https://example.com` resolved `APPROVED` with `HIGH` confidence. After withdrawal, `get_payment` shows `status: WITHDRAWN`, `withdrawn: true`, `approved_amount: 0`.

## Honest Limits

This first version deliberately keeps the nondeterminism budget short; it does not use screenshots, vector search, factories, or sandboxed caller code. It uses the GenLayer capabilities most relevant to this primitive: public web evidence, LLM consensus, native GEN custody, optional contract callback composition, and EVM-style recipient transfers.

StudioNet confirmed the value-moving paths. The `withdraw` receipt emitted an outbound value message of `1` wei to the recipient, and `reclaim_available` emitted an outbound value message of `1` wei to the principal. The current contract balance reads `13` wei because the live demo intentionally left `13` wei of mandate budget available. Explorer displays that as `0.000000 GEN` because it rounds tiny wei balances at GEN precision.
