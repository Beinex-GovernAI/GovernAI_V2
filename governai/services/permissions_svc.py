# services/permissions_svc.py

PERMISSIONS = {
    "Admin": {
        "view_ai_systems": True,
        "edit_ai_system_metadata": True,
        "view_compliance_status": True,
        "change_compliance_status": True,
        "approve_override_compliance": True,
        "edit_risk_tier": True,
        "sync_frameworks": True,
        "view_masked_pii": True,
        "view_raw_pii": False,
        "manage_users_roles": True,
    },
    "Compliance Officer": {
        "view_ai_systems": True,
        "edit_ai_system_metadata": False,
        "view_compliance_status": True,
        "change_compliance_status": True,
        "approve_override_compliance": True,
        "edit_risk_tier": True,
        "sync_frameworks": True,
        "view_masked_pii": True,
        "view_raw_pii": False,
        "manage_users_roles": False,
    },
    "Engineer": {
        "view_ai_systems": True,
        "edit_ai_system_metadata": True,
        "view_compliance_status": True,
        "change_compliance_status": False,
        "approve_override_compliance": False,
        "edit_risk_tier": False,
        "sync_frameworks": False,
        "view_masked_pii": True,
        "view_raw_pii": False,
        "manage_users_roles": False,
    },
}


def has_permission(role: str, action: str) -> bool:
    return PERMISSIONS.get(role, {}).get(action, False)


def current_role() -> str:
    """Reads the active simulated identity from session state, defaulting to Engineer (least privilege)."""
    import streamlit as st
    return st.session_state.get("current_user", "Engineer")