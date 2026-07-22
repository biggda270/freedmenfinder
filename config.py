"""
Configuration management for FREEDMENFINDER app.
Handles environment variables, API keys, and settings.

SECURITY: API keys are NEVER logged or exposed in error messages.
"""

import os
import re
from dotenv import load_dotenv

# Load .env first, then override with Streamlit secrets if available
load_dotenv()

# Pattern to mask sensitive keys in logs
SENSITIVE_PATTERNS = [
    r"sk-ant-[a-zA-Z0-9\-]+",  # Anthropic keys
    r"(ANTHROPIC_API_KEY|FAMILYSEARCH_PASSWORD|FAMILYSEARCH_TOKEN|access_token)\s*=\s*[^\s]+",
]

def mask_sensitive_data(text: str) -> str:
    """Remove/mask API keys and passwords from strings (for logging)."""
    if not text:
        return text
    
    masked = str(text)
    for pattern in SENSITIVE_PATTERNS:
        masked = re.sub(pattern, "***REDACTED***", masked, flags=re.IGNORECASE)
    return masked

def get_config():
    """Load and validate configuration from environment."""
    config = {}
    
    # Try to get Streamlit secrets if available
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            try:
                config = st.secrets.to_dict()
            except:
                pass
    except (ImportError, AttributeError, FileNotFoundError):
        # Fallback to environment variables only
        pass
    
    # Merge with environment variables (env vars take precedence)
    config.update({
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", config.get("ANTHROPIC_API_KEY")),
        "DEMO_MODE": os.environ.get("DEMO_MODE", config.get("DEMO_MODE", "True")) == "True",
        "FAMILYSEARCH_USERNAME": os.environ.get("FAMILYSEARCH_USERNAME", config.get("FAMILYSEARCH_USERNAME")),
        "FAMILYSEARCH_PASSWORD": os.environ.get("FAMILYSEARCH_PASSWORD", config.get("FAMILYSEARCH_PASSWORD")),
        "FAMILYSEARCH_ACCESS_TOKEN": os.environ.get("FAMILYSEARCH_ACCESS_TOKEN", config.get("FAMILYSEARCH_ACCESS_TOKEN")),
    })
    
    return config

def validate_api_key(api_key: str) -> bool:
    """Validate API key format without logging the actual key."""
    if not api_key:
        return False
    return api_key.startswith("sk-ant-") and len(api_key) > 20

def get_app_info():
    """Get app version and metadata."""
    return {
        "version": "1.0.0",
        "name": "🌳 FREEDMENFINDER",
        "tagline": "Tracing Black family lineage — including back through the era of slavery.",
        "description": (
            "An AI-powered genealogy research assistant built specifically to help Black "
            "Americans trace their family history, using the record types and search "
            "strategies unique to African American genealogy — Freedmen's Bureau records, "
            "Freedman's Bank records, cohabitation registers, and slave schedules indexed "
            "by enslaver's name — to help you find your ancestors on both sides of the "
            "'1870 brick wall.'"
        ),
    }


