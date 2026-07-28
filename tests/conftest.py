import pytest
from pathlib import Path

from gltest.direct.sdk_loader import setup_sdk_paths


setup_sdk_paths(Path("contracts/agent_mandate_firewall.py"))


def _patch_windows_fd0_unlink() -> None:
    import os
    import sys
    import tempfile

    if sys.platform != "win32":
        return

    import gltest.direct.loader as loader

    def tolerant_inject_message_to_fd0(vm):
        try:
            from genlayer.py import calldata
            from genlayer.py.types import Address
        except ImportError:
            return

        sender_addr = vm.sender
        if isinstance(sender_addr, bytes):
            sender_addr = Address(sender_addr)
        contract_addr = vm._contract_address
        if isinstance(contract_addr, bytes):
            contract_addr = Address(contract_addr)
        origin_addr = vm.origin
        if isinstance(origin_addr, bytes):
            origin_addr = Address(origin_addr)

        message_data = {
            "contract_address": contract_addr,
            "sender_address": sender_addr,
            "origin_address": origin_addr,
            "stack": [],
            "value": vm._value,
            "datetime": vm._datetime,
            "is_init": False,
            "chain_id": vm._chain_id,
            "entry_kind": 0,
            "entry_data": b"",
            "entry_stage_data": None,
        }

        encoded = calldata.encode(message_data)
        fd, path = tempfile.mkstemp()
        try:
            os.write(fd, encoded)
            os.lseek(fd, 0, os.SEEK_SET)
            vm._original_stdin_fd = os.dup(0)
            os.dup2(fd, 0)
        finally:
            os.close(fd)
            try:
                os.unlink(path)
            except PermissionError:
                pass

    loader._inject_message_to_fd0 = tolerant_inject_message_to_fd0


_patch_windows_fd0_unlink()


@pytest.fixture(autouse=True)
def reset_known_contract():
    yield
    try:
        import genlayer.gl as gl

        gl.genvm_contracts.__known_contract__ = None
    except Exception:
        pass


def as_hex_address(value) -> str:
    if hasattr(value, "as_hex"):
        return value.as_hex
    from genlayer.py.types import Address

    return Address(value).as_hex


def deploy_firewall(direct_deploy, **kwargs):
    args = [
        kwargs.get("max_mandates", 1000),
        kwargs.get("max_payments", 5000),
        kwargs.get("max_attempts", 3),
        kwargs.get("max_policy_chars", 900),
        kwargs.get("max_purpose_chars", 360),
        kwargs.get("max_url_chars", 320),
        kwargs.get("max_summary_chars", 500),
    ]
    return direct_deploy("contracts/agent_mandate_firewall.py", *args)


def open_mandate(direct_vm, contract, agent, value=1000, max_payment=300, callback=None):
    if callback is None:
        callback = "0x0000000000000000000000000000000000000000"
    direct_vm.value = value
    try:
        return contract.open_mandate(
            as_hex_address(agent),
            "Allow customer-support SaaS subscriptions and security audit tooling when public invoice evidence names the service, amount, and business purpose.",
            max_payment,
            as_hex_address(callback),
        )
    finally:
        direct_vm.value = 0


def request_payment(
    direct_vm,
    contract,
    agent,
    mandate_id,
    recipient,
    amount=120,
    request_key="invoice-1",
    purpose="Reimburse customer-support SaaS subscription for July operations.",
    evidence_url="https://example.com/invoice",
):
    with direct_vm.prank(agent):
        return contract.request_payment(
            mandate_id,
            amount,
            as_hex_address(recipient),
            purpose,
            evidence_url,
            request_key,
        )


def mock_evidence_and_llm(direct_vm, llm_response, status=200):
    direct_vm.mock_web(
        r"https://example.com/.*",
        {
            "status": status,
            "body": b"Invoice: HelpDesk Pro. Amount: 120 wei. Purpose: customer-support SaaS subscription.",
        },
    )
    direct_vm.mock_llm(r".*Agent Mandate Firewall.*", llm_response)
