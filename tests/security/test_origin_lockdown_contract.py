"""Locally executable validation for the revised origin-lockdown verifier
(feature 003, T054).

The verifier itself needs an external vantage point and the live approved
origin, so its *behaviour* cannot be exercised here. What can — and must —
be checked locally is its classification: after the Option A clarification
(contracts/compute-link.md C1a) the script has to tell three things apart
that the pre-Option-A version conflated:

  1. the one permitted WireGuard UDP transport listener,
  2. application and management listeners, which stay prohibited,
  3. observations that prove neither, which must fail closed.

These tests pin exactly that. They are the "locally executable validation"
T054 is re-marked complete against.
"""

from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "verify"))

import test_origin_lockdown as lockdown  # noqa: E402


# --- 1. The permitted transport listener is accepted, never probed ---------

def test_permitted_transport_is_the_wireguard_udp_port():
    assert lockdown.PERMITTED_TRANSPORT_PROTOCOL == "udp"
    assert lockdown.PERMITTED_TRANSPORT_PORT == 51820


def test_permitted_transport_port_is_not_in_the_prohibited_list():
    assert lockdown.PERMITTED_TRANSPORT_PORT not in lockdown.PROHIBITED_TCP_PORTS


def test_requesting_the_transport_port_is_refused_rather_than_reported_on():
    error = lockdown.validate_ports([443, lockdown.PERMITTED_TRANSPORT_PORT])
    assert error is not None
    assert "C1a" in error


def test_a_normal_prohibited_port_list_is_accepted():
    assert lockdown.validate_ports(list(lockdown.PROHIBITED_TCP_PORTS)) is None


def test_out_of_range_ports_are_refused():
    assert lockdown.validate_ports([0]) is not None
    assert lockdown.validate_ports([70000]) is not None


# --- 2. Application and management listeners stay rejected -----------------

@pytest.mark.parametrize(
    "port",
    [443, 80, 3000, 8000, 8188, 20241, 2019, 22, 3389, 445, 5432, 6379, 9090],
)
def test_application_and_management_ports_are_prohibited(port: int):
    assert port in lockdown.PROHIBITED_TCP_PORTS


def test_a_completed_connection_is_the_only_outright_failure():
    verdict, why = lockdown.classify_probe(lockdown.CONNECTED)
    assert verdict == lockdown.FAIL
    assert "listener" in why


@pytest.mark.parametrize("outcome", [lockdown.REFUSED, lockdown.RESET])
def test_unambiguous_absence_passes(outcome: str):
    verdict, _ = lockdown.classify_probe(outcome)
    assert verdict == lockdown.PASS


# --- 3. Ambiguous observations fail closed ---------------------------------

def test_a_silent_drop_is_inconclusive_not_a_pass():
    verdict, why = lockdown.classify_probe(lockdown.TIMEOUT)
    assert verdict == lockdown.INCONCLUSIVE
    assert "not proof" in why


def test_an_unclassifiable_outcome_is_inconclusive_not_a_pass():
    verdict, _ = lockdown.classify_probe(lockdown.UNKNOWN)
    assert verdict == lockdown.INCONCLUSIVE


def test_an_unrecognised_outcome_string_still_fails_closed():
    verdict, _ = lockdown.classify_probe("something-nobody-anticipated")
    assert verdict == lockdown.INCONCLUSIVE


def test_one_inconclusive_probe_prevents_an_overall_pass():
    assert lockdown.overall_verdict([lockdown.PASS] * 12) == lockdown.PASS
    assert (
        lockdown.overall_verdict([lockdown.PASS] * 11 + [lockdown.INCONCLUSIVE])
        == lockdown.INCONCLUSIVE
    )


def test_a_failure_dominates_every_other_verdict():
    assert (
        lockdown.overall_verdict([lockdown.PASS, lockdown.INCONCLUSIVE, lockdown.FAIL])
        == lockdown.FAIL
    )


def test_no_probes_at_all_is_not_a_pass():
    assert lockdown.overall_verdict([]) == lockdown.INCONCLUSIVE


# --- 4. Guards that keep the run from becoming false evidence --------------

def test_run_is_refused_without_the_off_campus_attestation(capsys):
    assert lockdown.main([]) == 2
    assert "confirm-off-campus" in capsys.readouterr().err


def test_run_is_refused_for_any_address_other_than_the_approved_origin(capsys):
    exit_code = lockdown.main(["--confirm-off-campus", "--origin-address", "203.0.113.9"])
    assert exit_code == 2
    assert lockdown.APPROVED_ORIGIN_ADDRESS in capsys.readouterr().err


def test_run_is_refused_when_the_transport_port_is_passed_as_prohibited(capsys):
    exit_code = lockdown.main(
        ["--confirm-off-campus", "--ports", str(lockdown.PERMITTED_TRANSPORT_PORT)]
    )
    assert exit_code == 2
    assert "C1a" in capsys.readouterr().err
