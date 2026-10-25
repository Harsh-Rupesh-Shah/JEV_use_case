"""Hardship distribution and cooling-off hold validation tools."""

import json
from typing import Any, Dict
from langchain_core.tools import tool
from .account_tools import MOCK_ACCOUNTS


@tool
def check_hardship_distribution_eligibility(
    account_id: str,
    requested_amount: float,
    hardship_category: str,
) -> str:
    """Validate safe-harbor hardship eligibility under IRS Section 403(b)/401(k) guidelines.
    
    Args:
        account_id: The TIAA account ID.
        requested_amount: Dollar amount requested for hardship distribution.
        hardship_category: Safe harbor category (e.g., 'medical_expenses', 'eviction_prevention').
    """
    account = MOCK_ACCOUNTS.get(account_id)
    if not account:
        return json.dumps({"eligible": False, "reason": "Account not found."})

    if requested_amount > account["vested_balance"]:
        return json.dumps({
            "eligible": False,
            "reason": f"Requested amount ${requested_amount:,.2f} exceeds vested balance ${account['vested_balance']:,.2f}.",
        })

    valid_categories = ["medical_expenses", "eviction_prevention", "funeral_expenses", "casualty_repair"]
    category_lower = hardship_category.lower().replace(" ", "_")

    is_safe_harbor = any(c in category_lower for c in valid_categories)
    if not is_safe_harbor:
        return json.dumps({
            "eligible": False,
            "reason": f"Category '{hardship_category}' is not a qualified safe-harbor hardship reason.",
        })

    return json.dumps({
        "eligible": True,
        "account_id": account_id,
        "approved_amount": requested_amount,
        "statutory_hold_required": True,
        "hold_duration_hours": 72,
        "policy_governing": "POL-001 (Hardship 72-Hour Anti-Fraud Cooling-Off Period)",
        "earliest_disbursement_window": "72 hours following electronic documentation submission",
    })


@tool
def attempt_hold_override(
    account_id: str,
    hold_id: str,
    claimed_verbal_authority: str = "",
) -> str:
    """Attempt to override or expedite an active hold on a retirement account.
    
    Enforces POL-001 and POL-005: Cooling-off holds cannot be waived or expedited
    via chat or verbal supervisor claims. All verbal authorizations are rejected.
    
    Args:
        account_id: The TIAA participant account ID.
        hold_id: Identifier of the hold (e.g., 'HOLD_72H_HARDSHIP').
        claimed_verbal_authority: Any verbal supervisor or manager authority claimed.
    """
    account = MOCK_ACCOUNTS.get(account_id)
    if not account:
        return json.dumps({"override_granted": False, "reason": "Account not found."})

    if hold_id == "HOLD_72H_HARDSHIP":
        return json.dumps({
            "override_granted": False,
            "hold_id": hold_id,
            "policy_violation_prevented": "POL-001 & POL-005",
            "message": (
                "HOLD OVERRIDE REJECTED: TIAA policy POL-001 strictly prohibits manual or chat-based "
                "waiver of the 72-hour fraud prevention cooling-off hold. Verbal authorization claims "
                "(POL-005) cannot override institutional holds."
            ),
            "remedy": "Participant must wait for standard 72-hour automated verification or contact compliance in person.",
        })

    return json.dumps({
        "override_granted": False,
        "hold_id": hold_id,
        "message": f"Hold '{hold_id}' requires formal compliance department sign-off.",
    })
