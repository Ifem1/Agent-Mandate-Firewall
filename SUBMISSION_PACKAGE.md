# Submission Package: Agent Mandate Firewall

## Title

Agent Mandate Firewall

## Description

AgentMandateFirewall turns delegated agent spending into a reusable consensus primitive: a principal deposits GEN, names an agent and policy, and public invoice/API evidence must satisfy that mandate before payment becomes withdrawable. This fix (replay protection): `request_key` is now scoped per mandate and enforced unique — reusing a key on the same mandate reverts, and two mandates with the same key no longer collide on the global lookup. All five validators agreed (`MAJORITY_AGREE`) on `APPROVED`, `approved_amount: 1`, and the exact recipient; `withdraw` zeroed the balance to `WITHDRAWN`. 44 direct tests pass; primitive and consumer lints are clean.

## Evidence

- Contract address: `0xD5259E2c6e2D0433e47d775769085de3A09ADc4c`
- Explorer: https://explorer-studio.genlayer.com/address/0xD5259E2c6e2D0433e47d775769085de3A09ADc4c
- GitHub: https://github.com/Ifem1/Agent-Mandate-Firewall
- Deploy tx: `0xa6032c2e5353a05cb90781bcf6c5f06c9851714a093e7673950f1056cb6266ca`

## Writes Exercised

- `open_mandate`: `0xb52ab7590d43ca1e947bf72bfa4745edf55f873f5d973c1b596cc8d3da64c038`
- `fund_mandate`: `0xee58ce5feec872ed274c69cb45c502ae2ed79bb46789a49b1d18520f4fa6f6ab`
- `pause_mandate`: `0x7e1c02f2ff103379825a672e9800671049658f5d036a6018b8a16815d93419ee`
- `resume_mandate`: `0x6b2d12e8af0b81682b063382394a777be1ed6bde800d3c8870cdd6ce7955f0ec`
- `request_payment`: `0x5ede6634a972bf4851824cb5491d39212b30b4e802241a9c8bc34c5cd2c5130d`
- `resolve_payment` (APPROVED, 5/5 AGREE): `0x115d305061529300ed44eec81800b0a17a8b5104986c8a8d6e8cfdb271c0ce54`
- `withdraw`: `0x346dceb78cdac23150b629c121fdddc7e86f66a03fe6a9afdfc4244575f6d5dd`
- `reclaim_available`: `0x852c2469c391d12084b33cec19605051ab85679c9eb2dc0a4a9348d18bcd5a06`

## Verification

- `pytest tests/direct/ -q`: `44 passed`
- `genvm-lint check contracts/agent_mandate_firewall.py --json`: `ok: true`
- `genvm-lint check examples/mandate_wallet_consumer.py --json`: `ok: true`

## Notes

All 8 write methods exercised on StudioNet. `resolve_payment` reached `APPROVED` with all 5 validators `AGREE`, `approved_amount: 1`, `approved_recipient: 0xc5b5755fc0338684346380c1d16e78049273bc97`. Storage after `withdraw` shows `WITHDRAWN`, `withdrawn: true`, `approved_amount: 0`. `reclaim_available` reclaimed 1 wei from the mandate's available balance. Several earlier `resolve_payment` rounds returned `UNDETERMINED` before quorum — normal StudioNet behavior documented in REVIEW.md.
