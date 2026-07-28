# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *


@gl.contract_interface
class IAgentMandateFirewall:
    class View:
        def payment_status(self, payment_id: str) -> str: ...
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


class MandateWalletConsumer(gl.Contract):
    firewall: Address
    mandate_id: str
    last_payment_id: str
    last_status: str
    last_recipient: Address
    last_amount: u256

    def __init__(self, firewall: str, mandate_id: str):
        self.firewall = Address(firewall)
        self.mandate_id = mandate_id
        self.last_payment_id = ""
        self.last_status = "NONE"
        self.last_recipient = Address("0x0000000000000000000000000000000000000000")
        self.last_amount = u256(0)

    @gl.public.write
    def submit_agent_payment(
        self,
        amount: int,
        recipient: str,
        purpose: str,
        evidence_url: str,
        request_key: str,
    ) -> None:
        IAgentMandateFirewall(self.firewall).emit().request_payment(
            self.mandate_id,
            amount,
            recipient,
            purpose,
            evidence_url,
            request_key,
        )

    @gl.public.write
    def ask_resolution(self, payment_id: str) -> None:
        IAgentMandateFirewall(self.firewall).emit().resolve_payment(payment_id)

    @gl.public.write
    def on_payment_resolved(
        self, payment_id: str, status: str, recipient: str, amount: int
    ) -> None:
        self.last_payment_id = payment_id
        self.last_status = status
        self.last_recipient = Address(recipient)
        self.last_amount = u256(amount)

    @gl.public.view
    def last_callback(self) -> dict:
        return {
            "payment_id": self.last_payment_id,
            "status": self.last_status,
            "recipient": self.last_recipient.as_hex,
            "amount": int(self.last_amount),
        }

    @gl.public.view
    def payment_summary(self, payment_id: str, account: str) -> dict:
        firewall = IAgentMandateFirewall(self.firewall)
        return {
            "status": firewall.view().payment_status(payment_id),
            "withdrawable": int(firewall.view().withdrawable(payment_id, account)),
        }
