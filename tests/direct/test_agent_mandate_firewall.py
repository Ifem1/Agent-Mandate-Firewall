import pytest

from tests.conftest import (
    as_hex_address,
    deploy_firewall,
    mock_evidence_and_llm,
    open_mandate,
    request_payment,
)


REJECTED_JSON = (
    '{"verdict":"REJECTED","confidence":"HIGH","approved_amount":0,'
    '"merchant_summary":"Luxury hotel booking",'
    '"policy_reason":"Travel is outside this software mandate",'
    '"error_code":"NONE"}'
)

UNKNOWN_JSON = (
    '{"verdict":"UNKNOWN","confidence":"NONE","approved_amount":0,'
    '"merchant_summary":"","policy_reason":"","error_code":"EXPECTED"}'
)


def approved_json(recipient, amount=120):
    return (
        '{"verdict":"APPROVED","confidence":"HIGH","approved_amount":'
        + str(amount)
        + ',"recipient_address":"'
        + as_hex_address(recipient)
        + '","merchant_summary":"HelpDesk Pro invoice for support SaaS",'
        + '"policy_reason":"Customer-support SaaS is allowed by the mandate",'
        + '"error_code":"NONE"}'
    )


def test_constructor_exposes_config(direct_deploy):
    contract = deploy_firewall(direct_deploy, max_mandates=10, max_payments=20)
    config = contract.get_config()
    assert config["max_mandates"] == 10
    assert config["max_payments"] == 20
    assert config["next_mandate_id"] == 1
    assert config["next_payment_id"] == 1


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"max_mandates": 0}, "max_mandates out of range"),
        ({"max_payments": 0}, "max_payments out of range"),
        ({"max_attempts": 0}, "max_attempts out of range"),
        ({"max_policy_chars": 20}, "max_policy_chars out of range"),
        ({"max_purpose_chars": 5}, "max_purpose_chars out of range"),
        ({"max_url_chars": 5}, "max_url_chars out of range"),
        ({"max_summary_chars": 20}, "max_summary_chars out of range"),
    ],
)
def test_constructor_rejects_bad_caps(direct_deploy, direct_vm, kwargs, error):
    with direct_vm.expect_revert(error):
        deploy_firewall(direct_deploy, **kwargs)


def test_open_mandate_requires_deposit(direct_deploy, direct_vm, direct_alice):
    contract = deploy_firewall(direct_deploy)
    with direct_vm.expect_revert("deposit required"):
        open_mandate(direct_vm, contract, direct_alice, value=0)


def test_open_mandate_requires_positive_max_payment(direct_deploy, direct_vm, direct_alice):
    contract = deploy_firewall(direct_deploy)
    with direct_vm.expect_revert("max_payment required"):
        open_mandate(direct_vm, contract, direct_alice, max_payment=0)


def test_open_mandate_rejects_max_payment_above_deposit(direct_deploy, direct_vm, direct_alice):
    contract = deploy_firewall(direct_deploy)
    with direct_vm.expect_revert("max_payment exceeds deposit"):
        open_mandate(direct_vm, contract, direct_alice, value=100, max_payment=101)


def test_open_mandate_stores_budget_and_roles(direct_deploy, direct_vm, direct_alice):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice, value=1000, max_payment=250)
    mandate = contract.get_mandate(mandate_id)
    assert mandate["exists"] is True
    assert mandate["agent"] == as_hex_address(direct_alice)
    assert mandate["available"] == 1000
    assert mandate["reserved"] == 0
    assert mandate["spent"] == 0
    assert mandate["status"] == "ACTIVE"


def test_only_principal_can_fund_mandate(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    with direct_vm.prank(direct_bob):
        direct_vm.value = 50
        try:
            with direct_vm.expect_revert("only principal"):
                contract.fund_mandate(mandate_id)
        finally:
            direct_vm.value = 0


def test_fund_mandate_increases_available(direct_deploy, direct_vm, direct_alice):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice, value=1000)
    direct_vm.value = 200
    try:
        contract.fund_mandate(mandate_id)
    finally:
        direct_vm.value = 0
    mandate = contract.get_mandate(mandate_id)
    assert mandate["deposited"] == 1200
    assert mandate["available"] == 1200


def test_pause_and_resume_are_principal_only(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("only principal"):
            contract.pause_mandate(mandate_id)
    contract.pause_mandate(mandate_id)
    assert contract.mandate_status(mandate_id) == "PAUSED"
    contract.resume_mandate(mandate_id)
    assert contract.mandate_status(mandate_id) == "ACTIVE"


def test_paused_mandate_rejects_payment_request(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    contract.pause_mandate(mandate_id)
    with direct_vm.expect_revert("mandate paused"):
        request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)


def test_only_agent_can_request_payment(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("only agent"):
            contract.request_payment(
                mandate_id,
                120,
                as_hex_address(direct_bob),
                "Reimburse customer-support SaaS subscription.",
                "https://example.com/invoice",
                "bad-agent",
            )


@pytest.mark.parametrize(
    "amount,error",
    [(0, "amount required"), (301, "amount exceeds max_payment")],
)
def test_payment_amount_validation(direct_deploy, direct_vm, direct_alice, direct_bob, amount, error):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice, max_payment=300)
    with direct_vm.expect_revert(error):
        request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob, amount=amount)


def test_request_payment_rejects_insufficient_balance(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice, value=100, max_payment=100)
    request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob, amount=80)
    with direct_vm.expect_revert("insufficient mandate balance"):
        request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob, amount=80, request_key="two")


def test_request_payment_rejects_non_https_evidence(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    with direct_vm.expect_revert("evidence_url must be https"):
        request_payment(
            direct_vm,
            contract,
            direct_alice,
            mandate_id,
            direct_bob,
            evidence_url="http://example.com/invoice",
        )


def test_request_payment_reserves_budget_and_indexes_key(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice, value=1000)
    payment_id = request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)
    mandate = contract.get_mandate(mandate_id)
    payment = contract.get_payment(payment_id)
    assert mandate["available"] == 880
    assert mandate["reserved"] == 120
    assert mandate["payments_count"] == 1
    assert payment["status"] == "PENDING"
    assert contract.latest_payment_for(mandate_id, "invoice-1") == payment_id


def test_request_key_rejects_replay_within_same_mandate(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice, value=1000, max_payment=1000)
    request_payment(
        direct_vm, contract, direct_alice, mandate_id, direct_bob, amount=100, request_key="invoice-1"
    )
    with direct_vm.expect_revert("request_key already used for this mandate"):
        request_payment(
            direct_vm, contract, direct_alice, mandate_id, direct_bob, amount=100, request_key="invoice-1"
        )


def test_request_key_is_scoped_per_mandate(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy)
    mandate_a = open_mandate(direct_vm, contract, direct_alice, value=1000, max_payment=1000)
    mandate_b = open_mandate(direct_vm, contract, direct_alice, value=1000, max_payment=1000)
    payment_a = request_payment(
        direct_vm, contract, direct_alice, mandate_a, direct_bob, amount=100, request_key="invoice-1"
    )
    payment_b = request_payment(
        direct_vm, contract, direct_alice, mandate_b, direct_bob, amount=100, request_key="invoice-1"
    )
    assert payment_a != payment_b
    assert contract.latest_payment_for(mandate_a, "invoice-1") == payment_a
    assert contract.latest_payment_for(mandate_b, "invoice-1") == payment_b


def test_unknown_payment_reads_fail_closed(direct_deploy):
    contract = deploy_firewall(direct_deploy)
    assert contract.payment_status("missing") == "UNKNOWN"
    assert contract.withdrawable("missing", "0x0000000000000000000000000000000000000000") == 0
    assert contract.get_payment("missing")["exists"] is False


def test_approved_payment_becomes_recipient_withdrawable(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice, value=1000)
    payment_id = request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)
    mock_evidence_and_llm(direct_vm, approved_json(direct_bob))
    contract.resolve_payment(payment_id)
    payment = contract.get_payment(payment_id)
    mandate = contract.get_mandate(mandate_id)
    assert payment["status"] == "APPROVED"
    assert payment["approved_amount"] == 120
    assert mandate["reserved"] == 0
    assert mandate["available"] == 880
    assert mandate["spent"] == 120
    assert contract.withdrawable(payment_id, as_hex_address(direct_bob)) == 120


def test_over_requested_approval_is_unknown_not_clamped(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy, max_attempts=1)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    payment_id = request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob, amount=120)
    mock_evidence_and_llm(direct_vm, approved_json(direct_bob, amount=999999))
    contract.resolve_payment(payment_id)
    payment = contract.get_payment(payment_id)
    mandate = contract.get_mandate(mandate_id)
    assert payment["status"] == "UNKNOWN"
    assert payment["approved_amount"] == 0
    assert mandate["reserved"] == 0
    assert mandate["available"] == 1000


def test_approval_requires_exact_recipient_binding(direct_deploy, direct_vm, direct_alice, direct_bob, direct_charlie):
    contract = deploy_firewall(direct_deploy, max_attempts=1)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    payment_id = request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)
    mock_evidence_and_llm(direct_vm, approved_json(direct_charlie))
    contract.resolve_payment(payment_id)
    payment = contract.get_payment(payment_id)
    mandate = contract.get_mandate(mandate_id)
    assert payment["status"] == "UNKNOWN"
    assert payment["approved_amount"] == 0
    assert payment["approved_recipient"] == "0x0000000000000000000000000000000000000000"
    assert mandate["reserved"] == 0
    assert mandate["available"] == 1000


def test_approval_requires_recipient_in_judgement(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy, max_attempts=1)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    payment_id = request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)
    missing_recipient = (
        '{"verdict":"APPROVED","confidence":"HIGH","approved_amount":120,'
        '"merchant_summary":"HelpDesk Pro invoice for support SaaS",'
        '"policy_reason":"Customer-support SaaS is allowed by the mandate",'
        '"error_code":"NONE"}'
    )
    mock_evidence_and_llm(direct_vm, missing_recipient)
    contract.resolve_payment(payment_id)
    assert contract.payment_status(payment_id) == "UNKNOWN"
    assert contract.withdrawable(payment_id, as_hex_address(direct_bob)) == 0


def test_rejected_payment_returns_reserved_budget(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice, value=1000)
    payment_id = request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)
    mock_evidence_and_llm(direct_vm, REJECTED_JSON)
    contract.resolve_payment(payment_id)
    mandate = contract.get_mandate(mandate_id)
    assert contract.payment_status(payment_id) == "REJECTED"
    assert mandate["available"] == 1000
    assert mandate["reserved"] == 0
    assert mandate["spent"] == 0


def test_unknown_after_retry_cap_returns_budget(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy, max_attempts=1)
    mandate_id = open_mandate(direct_vm, contract, direct_alice, value=1000)
    payment_id = request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)
    mock_evidence_and_llm(direct_vm, UNKNOWN_JSON)
    contract.resolve_payment(payment_id)
    mandate = contract.get_mandate(mandate_id)
    assert contract.payment_status(payment_id) == "UNKNOWN"
    assert mandate["available"] == 1000
    assert mandate["reserved"] == 0


def test_unknown_before_retry_cap_remains_pending(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy, max_attempts=2)
    mandate_id = open_mandate(direct_vm, contract, direct_alice, value=1000)
    payment_id = request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)
    mock_evidence_and_llm(direct_vm, UNKNOWN_JSON)
    contract.resolve_payment(payment_id)
    payment = contract.get_payment(payment_id)
    assert payment["status"] == "PENDING"
    assert payment["attempts"] == 1


def test_external_fetch_failure_is_unknown_not_rejected(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy, max_attempts=1)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    payment_id = request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)
    mock_evidence_and_llm(direct_vm, approved_json(direct_bob), status=500)
    contract.resolve_payment(payment_id)
    payment = contract.get_payment(payment_id)
    assert payment["status"] == "UNKNOWN"
    assert payment["error_code"] == "EXTERNAL"


def test_malformed_model_output_is_unknown(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy, max_attempts=1)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    payment_id = request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)
    mock_evidence_and_llm(direct_vm, "not json")
    contract.resolve_payment(payment_id)
    assert contract.get_payment(payment_id)["error_code"] == "LLM_ERROR"


def test_low_confidence_approval_is_unknown(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy, max_attempts=1)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    payment_id = request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)
    mock_evidence_and_llm(direct_vm, approved_json(direct_bob).replace('"HIGH"', '"MEDIUM"'))
    contract.resolve_payment(payment_id)
    assert contract.payment_status(payment_id) == "UNKNOWN"


def test_resolve_unknown_payment_reverts(direct_deploy, direct_vm):
    contract = deploy_firewall(direct_deploy)
    with direct_vm.expect_revert("unknown payment"):
        contract.resolve_payment("missing")


def test_terminal_payment_cannot_resolve_again(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    payment_id = request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)
    mock_evidence_and_llm(direct_vm, approved_json(direct_bob))
    contract.resolve_payment(payment_id)
    with direct_vm.expect_revert("payment terminal"):
        contract.resolve_payment(payment_id)


def test_withdraw_requires_approved_payment(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    payment_id = request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)
    with direct_vm.expect_revert("payment not approved"):
        contract.withdraw(payment_id)


def test_only_recipient_can_withdraw(direct_deploy, direct_vm, direct_alice, direct_bob, direct_charlie):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    payment_id = request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)
    mock_evidence_and_llm(direct_vm, approved_json(direct_bob))
    contract.resolve_payment(payment_id)
    with direct_vm.prank(direct_charlie):
        with direct_vm.expect_revert("only recipient"):
            contract.withdraw(payment_id)


def test_withdraw_writes_state_before_value_path(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    payment_id = request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)
    mock_evidence_and_llm(direct_vm, approved_json(direct_bob))
    contract.resolve_payment(payment_id)
    with direct_vm.prank(direct_bob):
        contract.withdraw(payment_id)
    payment = contract.get_payment(payment_id)
    assert payment["withdrawn"] is True
    assert payment["status"] == "WITHDRAWN"
    assert payment["approved_amount"] == 0
    assert contract.withdrawable(payment_id, as_hex_address(direct_bob)) == 0


def test_double_withdraw_reverts(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    payment_id = request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)
    mock_evidence_and_llm(direct_vm, approved_json(direct_bob))
    contract.resolve_payment(payment_id)
    with direct_vm.prank(direct_bob):
        contract.withdraw(payment_id)
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("payment not approved"):
            contract.withdraw(payment_id)


def test_reclaim_available_is_principal_only_and_reduces_budget(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice, value=1000)
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("only principal"):
            contract.reclaim_available(mandate_id, 100)
    contract.reclaim_available(mandate_id, 100)
    mandate = contract.get_mandate(mandate_id)
    assert mandate["available"] == 900
    assert mandate["deposited"] == 900


def test_reclaim_available_cannot_take_reserved_funds(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy)
    mandate_id = open_mandate(direct_vm, contract, direct_alice, value=1000, max_payment=1000)
    request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob, amount=950)
    with direct_vm.expect_revert("insufficient available"):
        contract.reclaim_available(mandate_id, 100)


def test_mandate_and_payment_caps_are_enforced(direct_deploy, direct_vm, direct_alice, direct_bob):
    contract = deploy_firewall(direct_deploy, max_mandates=1, max_payments=1)
    mandate_id = open_mandate(direct_vm, contract, direct_alice)
    with direct_vm.expect_revert("mandate cap reached"):
        open_mandate(direct_vm, contract, direct_alice)
    request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob)
    with direct_vm.expect_revert("payment cap reached"):
        request_payment(direct_vm, contract, direct_alice, mandate_id, direct_bob, request_key="two")
