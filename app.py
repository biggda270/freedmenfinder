"""
FREEDMENFINDER — Genealogy Research Agent
==========================================

AI-powered genealogy research pipeline:
  1. Research planning (identify which record types to search)
  2. Record search (search FamilySearch database)
  3. Evidence scoring (evaluate match confidence)
  4. Narrative generation (write family history)
  5. GEDCOM export (download structured genealogy data)

Run: streamlit run app.py

Requires:
  - ANTHROPIC_API_KEY in .env or .streamlit/secrets.toml
  - python-dotenv, streamlit, anthropic, requests

Demo mode uses realistic mock data. Set DEMO_MODE=False to use live APIs.
"""

import os
import json
import logging
import streamlit as st
from anthropic import Anthropic, APIError
from dotenv import load_dotenv

# Load configuration FIRST, BEFORE any streamlit commands
load_dotenv()

from config import get_config, validate_api_key, get_app_info, mask_sensitive_data
from familysearch_client import FamilySearchClient
from gedcom_export import build_gedcom

config = get_config()
app_info = get_app_info()

# MUST call set_page_config first, before any other st commands
st.set_page_config(
    page_title=app_info["name"],
    page_icon="🌳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# NOW configure logging with sensitive data masking
class SensitiveDataFilter(logging.Filter):
    """Filter to mask API keys in logs."""
    def filter(self, record):
        record.msg = mask_sensitive_data(str(record.msg))
        if record.exc_text:
            record.exc_text = mask_sensitive_data(record.exc_text)
        return True

logger = logging.getLogger(__name__)
logger.addFilter(SensitiveDataFilter())
logging.basicConfig(level=logging.INFO)

CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
DEMO_MODE = config.get("DEMO_MODE", True)


# Initialize session state
if "client" not in st.session_state:
    st.session_state.client = None
if "fs_client" not in st.session_state:
    st.session_state.fs_client = None
if "error" not in st.session_state:
    st.session_state.error = None

# Initialize clients
try:
    if not DEMO_MODE:
        api_key = config.get("ANTHROPIC_API_KEY")
        if not api_key or not validate_api_key(api_key):
            st.session_state.error = "❌ Invalid or missing ANTHROPIC_API_KEY. Get one at https://console.anthropic.com/account/billing/overview"
            logger.warning("Invalid or missing ANTHROPIC_API_KEY")
        else:
            st.session_state.client = Anthropic(api_key=api_key)
            logger.info("Claude client initialized successfully")
    
    st.session_state.fs_client = FamilySearchClient(demo_mode=DEMO_MODE)
    logger.info(f"FamilySearch client initialized (demo_mode={DEMO_MODE})")
    
except Exception as e:
    error_msg = mask_sensitive_data(str(e))
    st.session_state.error = f"❌ Error initializing clients: {error_msg}"
    logger.error(f"Client initialization error: {error_msg}")



# ---------- Claude helper functions ----------

@st.cache_data(ttl=3600)
def ask_claude(system_prompt: str, user_prompt: str, max_tokens: int = 1500) -> str:
    """Call Claude API (cached for performance)."""
    if DEMO_MODE:
        return "Mock response from genealogist AI assistant."
    
    if not st.session_state.client:
        raise RuntimeError("Claude client not initialized. Check API key configuration.")
    
    try:
        resp = st.session_state.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")
    except APIError as e:
        # Don't expose API details in logs
        masked_error = mask_sensitive_data(str(e))
        logger.error(f"Claude API error: {masked_error}")
        if "credit" in str(e).lower():
            raise RuntimeError("Insufficient API credits. Add funds at https://console.anthropic.com/account/billing/overview")
        raise RuntimeError(f"Claude API error: {masked_error}")
    except Exception as e:
        masked_error = mask_sensitive_data(str(e))
        logger.error(f"Unexpected error calling Claude: {masked_error}")
        raise


@st.cache_data(ttl=3600)
def ask_claude_json(system_prompt: str, user_prompt: str, max_tokens: int = 1500) -> dict:
    """Call Claude API and parse JSON response (cached)."""
    if DEMO_MODE:
        # Return realistic mock JSON for different pipeline steps
        if "research strategy" in system_prompt.lower() or "plan" in system_prompt.lower():
            return {
                "records_to_search": [
                    {
                        "type": "Birth Records",
                        "reason": "Primary source for birth date and location",
                        "search_terms": "Josef Novak 1888"
                    },
                    {
                        "type": "Marriage Records",
                        "reason": "Likely exists given the era",
                        "search_terms": "Josef Novak marriage 1910-1920"
                    },
                    {
                        "type": "Census Records",
                        "reason": "Multiple census records available for Austria-Hungary era",
                        "search_terms": "Josef Novak census Bohemia"
                    }
                ]
            }
        elif "evaluating candidate records" in system_prompt.lower() or "score" in system_prompt.lower():
            return {
                "scored_records": [
                    {"record": "1888 Birth Record - Josef Novak", "score": 95, "reason": "Perfect name and date match"},
                    {"record": "1910 Marriage Record - Josef & Maria", "score": 87, "reason": "Name match, plausible date"},
                    {"record": "1900 Census - Joseph Nowak", "score": 72, "reason": "Likely same person, minor name variant"}
                ]
            }
        elif "narrative" in system_prompt.lower() or "family history" in system_prompt.lower():
            return {
                "narrative": "Josef Novak was born in 1888 in Bohemia, Austria-Hungary. Based on available records, he married Maria in the early 1900s. The family likely remained in the Bohemian region until the early 20th century. Multiple census records and church documents support this timeline."
            }
        else:
            return {"response": "Mock AI response"}
    
    raw = ask_claude(system_prompt, user_prompt, max_tokens)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1) if cleaned.lower().startswith("json") else cleaned
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error: {e}")
        st.warning("Claude's response wasn't valid JSON — showing raw output instead.")
        return {"raw": raw}




# ---------- Pipeline steps ----------
def step1_research_plan(person: dict) -> dict:
    system = (
        "You are a professional genealogist planning a research strategy. "
        "Given basic facts about a person, list which record types plausibly "
        "exist and are worth searching for, given the era and location. "
        "Respond ONLY with JSON: "
        '{"records_to_search": [{"type": "...", "reason": "...", "search_terms": "..."}]}'
    )
    user = f"Person details:\n{json.dumps(person, indent=2)}"
    return ask_claude_json(system, user)


def step2_search_records(person: dict, plan: dict) -> list:
    results = []
    for item in plan.get("records_to_search", []):
        matches = st.session_state.fs_client.search(
            given_name=person.get("given_name", ""),
            surname=person.get("surname", ""),
            birth_year=person.get("birth_year"),
            location=person.get("location", ""),
            record_type=item.get("type", ""),
        )
        results.append({"query": item, "matches": matches})
    return results


def step3_score_evidence(person: dict, search_results: list) -> dict:
    system = (
        "You are a genealogist evaluating candidate records against a target person. "
        "For each match, assign a confidence score 0-100 based on name similarity, "
        "date proximity (allow +/-2 years), location consistency, and any family "
        "cross-references. Flag direct conflicts between sources (e.g. two "
        "different birth years) rather than silently picking one. "
        "Respond ONLY with JSON: "
        '{"scored_matches": [{"record_type":"...", "source_id":"...", '
        '"confidence": 0, "reasoning":"...", "facts_extracted": {...}}], '
        '"conflicts": [{"description":"...", "sources": ["..."]}]}'
    )
    user = (
        f"Target person:\n{json.dumps(person, indent=2)}\n\n"
        f"Search results:\n{json.dumps(search_results, indent=2)}"
    )
    return ask_claude_json(system, user, max_tokens=2000)


def step4_write_narrative(person: dict, scored: dict) -> str:
    system = (
        "You are a skilled family historian writing a warm, engaging, factually "
        "grounded narrative about a person's life, based only on the confirmed "
        "facts provided. Do not invent details. Where confidence is low or facts "
        "conflict, note the uncertainty gracefully rather than glossing over it. "
        "Write 3-5 short paragraphs."
    )
    user = (
        f"Person:\n{json.dumps(person, indent=2)}\n\n"
        f"Confirmed facts and confidence scores:\n{json.dumps(scored, indent=2)}"
    )
    return ask_claude(system, user, max_tokens=1200)


# ---------- Streamlit UI ----------

# Sidebar with settings and info
with st.sidebar:
    st.title("⚙️ Settings")
    
    mode_info = "🟢 Demo Mode (Mock Data)" if DEMO_MODE else "🔴 Live Mode (Real APIs)"
    st.info(f"{mode_info}\n\nSwitch by editing `.env` file: `DEMO_MODE=False`")
    
    st.divider()
    
    st.subheader("📖 About")
    st.markdown(f"""
    **{app_info['name']}**
    
    v{app_info['version']}
    
    {app_info['description']}
    
    [GitHub](https://github.com) • [Docs](https://docs.familysearch.org)
    """)
    
    st.divider()
    
    if st.button("🔄 Clear Cache"):
        st.cache_data.clear()
        st.session_state.clear()
        st.success("Cache cleared!")

# Main title
st.title(app_info["name"])

# Show error if present
if st.session_state.error:
    st.error(st.session_state.error)
    st.stop()

# Info banner
col1, col2 = st.columns([3, 1])
with col1:
    if DEMO_MODE:
        st.info("🎯 **Demo Mode**: Using realistic mock data. Add Anthropic credits to enable real API calls.")
    else:
        st.success("✅ **Live Mode**: Using real Claude API and FamilySearch data.")
with col2:
    if not DEMO_MODE:
        st.metric("Mode", "Live", "active")

st.divider()

# Input form
with st.form("person_intake", clear_on_submit=False):
    st.subheader("1️⃣ Tell me about the person")
    
    col1, col2 = st.columns(2)
    with col1:
        given_name = st.text_input(
            "Given name",
            value="Josef",
            help="First or given name"
        )
    with col2:
        surname = st.text_input(
            "Surname",
            value="Novak",
            help="Last or family name"
        )
    
    col3, col4 = st.columns(2)
    with col3:
        birth_year = st.number_input(
            "Approx. birth year",
            min_value=1700,
            max_value=2020,
            value=1888,
            help="Approximate year of birth"
        )
    with col4:
        location = st.text_input(
            "Approx. birth location",
            value="Bohemia, Austria-Hungary",
            help="Region, town, or country"
        )
    
    st.text_area(
        "Known relatives (optional)",
        placeholder="wife: Anna Novak\nson: Josef Jr.",
        help="One relative per line, e.g., 'wife: Anna' or 'father: Johann'",
        key="relatives_input"
    )
    
    col_submit, col_reset = st.columns(2)
    with col_submit:
        submitted = st.form_submit_button("▶️ Run research pipeline", type="primary")
    with col_reset:
        st.form_submit_button("🔄 Reset")

# Run pipeline
if submitted:
    if not given_name or not surname:
        st.error("❌ Please enter at least a given name and surname.")
    else:
        person = {
            "given_name": given_name,
            "surname": surname,
            "birth_year": int(birth_year),
            "location": location,
            "known_relatives": [
                r.strip()
                for r in st.session_state.relatives_input.splitlines()
                if r.strip()
            ],
        }

        with st.status("⏳ Running research pipeline...", expanded=True) as status:
            try:
                st.write("**Step 1 — Planning research strategy**")
                plan = step1_research_plan(person)
                st.json(plan)

                st.write("**Step 2 — Searching records**")
                search_results = step2_search_records(person, plan)
                st.json(search_results)

                st.write("**Step 3 — Scoring evidence & flagging conflicts**")
                scored = step3_score_evidence(person, search_results)
                st.json(scored)

                st.write("**Step 4 — Writing narrative**")
                narrative = step4_write_narrative(person, scored)

                status.update(label="✅ Complete!", state="complete")

            except Exception as e:
                masked_error = mask_sensitive_data(str(e))
                logger.error(f"Pipeline error: {masked_error}")
                status.update(label="❌ Error occurred", state="error")
                st.error(f"❌ Pipeline error: {masked_error}")
                st.stop()

        st.divider()

        # Results
        st.subheader("📖 Family History Narrative")
        if isinstance(narrative, dict) and "narrative" in narrative:
            st.write(narrative["narrative"])
        else:
            st.write(narrative)

        if scored.get("conflicts"):
            st.subheader("⚠️ Conflicts found (needs your review)")
            for c in scored["conflicts"]:
                with st.expander(f"❌ {c.get('description')}"):
                    st.write(f"**Sources**: {', '.join(c.get('sources', []))}")

        # Export
        st.divider()
        st.subheader("⬇️ Export Results")

        col_export, col_view = st.columns(2)

        with col_export:
            gedcom_text = build_gedcom(person, scored)
            st.download_button(
                "📥 Download GEDCOM file",
                data=gedcom_text,
                file_name=f"{surname}_{given_name}.ged",
                mime="text/plain",
                use_container_width=True
            )

        with col_view:
            with st.expander("👁️ View raw GEDCOM"):
                st.code(gedcom_text, language="text", line_numbers=True)

