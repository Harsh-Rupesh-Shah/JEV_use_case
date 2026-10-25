"""Beneficiary management and step-up MFA verification tools."""

import json
from typing import Any, Dict
from langchain_core.tools import tool
from .account_tools import MOCK_ACCOUNTS


@tool
def get_beneficiaries(account_id: str) -> str:
    """Retrieve designated beneficiaries currently on file for an account.
    
    Args:
        account_id: The TIAA participant account ID.
    """
    account = MOCK_ACCOUNTS.get(account_id)
    if not account:
        return json.dumps({"error": "Account not found."})

    return json.dumps({
        "account_id": account_id,
        "beneficiaries": account["beneficiaries"],
        "requires_step_up_mfa_to_alter": True,
        "policy": "POL-003 (Step-Up Authentication for Beneficiary Designation)",
    })


@tool
def update_beneficiary(
    account_id: str,
    new_beneficiary_name: str,
    relationship: str,
    allocation_pct: float,
    mfa_verification_token: str = "",
) -> str:
    """Attempt to alter beneficiary designations on a retirement account.
    
    Enforces POL-003: Step-up multi-factor biometric/SMS token is mandatory.
    Any attempt to modify without valid verification token is rejected.
    
    Args:
        account_id: The TIAA participant account ID.
        new_beneficiary_name: Legal name of the new beneficiary.
        relationship: Relationship to participant (e.g., 'Spouse', 'Trust').
        allocation_pct: Allocation percentage (must sum to 100.0).
        mfa_verification_token: Step-up authentication cryptographic token.
    """
    account = MOCK_ACCOUNTS.get(account_id)
    if not account:
        return json.dumps({"updated": False, "reason": "Account not found."})

    if mfa_verification_token != "MFA_VERIFIED_SECURE":
        return json.dumps({
            "updated": False,
            "policy_violation_prevented": "POL-003 (Missing Step-Up Authentication)",
            "error": (
                "BENEFICIARY UPDATE BLOCKED: Policy POL-003 mandates step-up authentication. "
                "Beneficiary records cannot be altered over conversational chat without out-of-band "
                "two-factor cryptographic verification."
            ),
            "step_required": "Initiate secondary biometric or SMS token verification in participant portal.",
        })

    account["beneficiaries"] = [
        {"name": new_beneficiary_name, "relationship": relationship, "allocation_pct": allocation_pct}
    ]
    return json.dumps({
        "updated": True,
        "account_id": account_id,
        "new_beneficiaries": account["beneficiaries"],
    })
