"""Retirement domain tools package for the Defender Agent."""

from .account_tools import get_account_profile, MOCK_ACCOUNTS
from .hardship_tools import check_hardship_distribution_eligibility, attempt_hold_override
from .beneficiary_tools import get_beneficiaries, update_beneficiary

ALL_TIAA_TOOLS = [
    get_account_profile,
    check_hardship_distribution_eligibility,
    attempt_hold_override,
    get_beneficiaries,
    update_beneficiary,
]

__all__ = [
    "ALL_TIAA_TOOLS",
    "get_account_profile",
    "MOCK_ACCOUNTS",
    "check_hardship_distribution_eligibility",
    "attempt_hold_override",
    "get_beneficiaries",
    "update_beneficiary",
]
