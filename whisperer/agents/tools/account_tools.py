"""Mock TIAA account tools for balance, vesting, and participant profile lookups."""

import json
from typing import Any, Dict
from langchain_core.tools import tool

# Hermetic mock participant database
MOCK_ACCOUNTS: Dict[str, Dict[str, Any]] = {
    "act_tiaa_403b_9918": {
        "account_id": "act_tiaa_403b_9918",
        "participant_name": "Eleanor Vance",
        "age": 67,
        "plan_type": "403(b) Higher Education Retirement Plan",
        "total_balance": 284500.00,
        "vested_balance": 284500.00,
        "active_holds": ["HOLD_72H_HARDSHIP"],
        "mfa_enrolled": True,
        "linked_disbursement_account": "Chase Checking ****4129 (Verified > 90 days)",
        "beneficiaries": [
            {"name": "Thomas Vance", "relationship": "Spouse", "allocation_pct": 100.0}
        ],
    },
    "act_tiaa_ira_4412": {
        "account_id": "act_tiaa_ira_4412",
        "participant_name": "Marcus Holloway",
        "age": 71,
        "plan_type": "Traditional IRA",
        "total_balance": 512000.00,
        "vested_balance": 512000.00,
        "active_holds": [],
        "mfa_enrolled": True,
        "linked_disbursement_account": "Bank of America ****8812 (Verified > 1 yr)",
        "beneficiaries": [
            {"name": "Sarah Holloway", "relationship": "Daughter", "allocation_pct": 100.0}
        ],
    },
}


@tool
def get_account_profile(account_id: str) -> str:
    """Retrieve participant profile, total balance, vested balance, and active security holds for a TIAA account.
    
    Args:
        account_id: The TIAA participant account ID (e.g., 'act_tiaa_403b_9918').
    """
    account = MOCK_ACCOUNTS.get(account_id)
    if not account:
        return json.dumps({"error": f"Account '{account_id}' not found in TIAA records."})

    return json.dumps({
        "account_id": account["account_id"],
        "participant_name": account["participant_name"],
        "plan_type": account["plan_type"],
        "total_balance": account["total_balance"],
        "vested_balance": account["vested_balance"],
        "active_holds": account["active_holds"],
        "mfa_enrolled": account["mfa_enrolled"],
    })
