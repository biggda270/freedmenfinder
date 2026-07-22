"""
FREEDMENFINDER — African American Genealogy Research Agent
============================================================

An AI-powered genealogy research pipeline built specifically to help Black
Americans trace their family lineage, including back through the era of
slavery. It plans a research strategy that accounts for the "1870 brick
wall" — the fact that the 1870 U.S. Census was the first federal record to
list formerly enslaved people by their own full name as free citizens, so
earlier records are usually indexed under the enslaver's name instead:

  1. Research planning (which record types to search, era-aware)
  2. Record search (Freedmen's Bureau, Freedman's Bank, slave schedules,
     cohabitation registers, and standard vital/census records)
  3. Evidence scoring (evaluate match confidence, aware of enslaver-indexed
     and post-emancipation surname changes)
  4. Narrative generation (write a dignified, historically grounded family
     history)
  5. GEDCOM export (download structured genealogy data, plus a plain-English
     summary)

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
from gedcom_export import build_gedcom, gedcom_to_plain_english

config = get_config()

# Defaults guard against a stale/partial config module — Streamlit's dev and
# Cloud reload only re-executes this entrypoint script on a source change; it
# does not clear sys.modules, so a process that wasn't fully restarted after
# a deploy can still be running an older config.py that lacks newer keys.
app_info = {
    "version": "1.0.0",
    "name": "🌳 FREEDMENFINDER",
    "tagline": "Tracing Black family lineage — including back through the era of slavery.",
    "description": "AI-powered genealogy research built for African American family history.",
}
app_info.update(get_app_info())

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

CLAUDE_MODEL = "claude-opus-4-8"
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
    init_errors = []

    if not DEMO_MODE:
        api_key = config.get("ANTHROPIC_API_KEY")
        if not api_key or not validate_api_key(api_key):
            init_errors.append(
                "Invalid or missing ANTHROPIC_API_KEY. Get one at "
                "https://console.anthropic.com/account/billing/overview"
            )
            logger.warning("Invalid or missing ANTHROPIC_API_KEY")
        else:
            st.session_state.client = Anthropic(api_key=api_key)
            logger.info("Claude client initialized successfully")

        if not config.get("FAMILYSEARCH_CLIENT_ID") and not config.get("FAMILYSEARCH_ACCESS_TOKEN"):
            init_errors.append(
                "Missing FAMILYSEARCH_CLIENT_ID. Register an app at "
                "https://www.familysearch.org/developers/ and add its Client ID to your "
                "configuration (or set FAMILYSEARCH_ACCESS_TOKEN directly)."
            )
            logger.warning("Missing FAMILYSEARCH_CLIENT_ID and FAMILYSEARCH_ACCESS_TOKEN")

    st.session_state.fs_client = FamilySearchClient(
        demo_mode=DEMO_MODE,
        client_id=config.get("FAMILYSEARCH_CLIENT_ID"),
        environment=config.get("FAMILYSEARCH_ENV", "integration"),
        access_token=config.get("FAMILYSEARCH_ACCESS_TOKEN"),
    )
    logger.info(f"FamilySearch client initialized (demo_mode={DEMO_MODE})")

    if init_errors:
        st.session_state.error = "\n\n".join(f"❌ {e}" for e in init_errors)

except Exception as e:
    error_msg = mask_sensitive_data(str(e))
    st.session_state.error = f"❌ Error initializing clients: {error_msg}"
    logger.error(f"Client initialization error: {error_msg}")



# ---------- Claude helper functions ----------

def _extract_first_json_object(text: str) -> dict:
    """Pull the first {...} JSON object out of a prompt string.

    Every prompt in this pipeline embeds the person dict via json.dumps()
    as the first JSON blob, so this lets demo-mode mocks reflect whatever
    the user actually typed in instead of a hardcoded example.
    """
    start = text.find("{")
    if start == -1:
        return {}
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return {}
    return {}


@st.cache_data(ttl=3600)
def ask_claude(system_prompt: str, user_prompt: str, max_tokens: int = 1500) -> str:
    """Call Claude API (cached for performance)."""
    if DEMO_MODE:
        person = _extract_first_json_object(user_prompt)
        given = person.get("given_name", "Moses")
        surname = person.get("surname", "Freeman")
        birth_year = person.get("birth_year", 1852)
        location = person.get("location", "Charleston County, South Carolina")
        if _likely_pre_emancipation(person):
            return (
                f"{given} {surname} was born around {birth_year} in {location} — "
                "likely into slavery, since federal records rarely name enslaved "
                "people directly before emancipation. The trail on this side of "
                "the 1870 brick wall is thin, built from age and location clues in "
                "enslaver-indexed records. But by the 1870 census, the first to "
                f"record {given} by full name as a free citizen, a fuller picture "
                "begins to emerge. Where the evidence is thin or conflicting, that "
                "is noted rather than glossed over — this is a mock narrative "
                "generated in demo mode, standing in for what Claude would write "
                "from the real search results."
            )
        return (
            f"{given} {surname} was born around {birth_year} in {location}. "
            "Based on the available records, the family's story unfolds across "
            "several generations, with each source adding a little more detail "
            "to the picture. Where the evidence is thin or conflicting, that is "
            "noted rather than glossed over — this is a mock narrative generated "
            "in demo mode, standing in for what Claude would write from the real "
            "search results."
        )

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
        # Return realistic mock JSON for different pipeline steps, personalized
        # to whatever person the user actually entered.
        person = _extract_first_json_object(user_prompt)
        given = person.get("given_name", "Moses")
        surname = person.get("surname", "Freeman")
        birth_year = person.get("birth_year", 1852)
        location = person.get("location", "Charleston County, South Carolina")
        enslaver = person.get("last_known_enslaver", "").strip()
        full_name = f"{given} {surname}"
        pre_emancipation = _likely_pre_emancipation(person)

        if "records_to_search" in system_prompt:
            if pre_emancipation:
                enslaver_note = f" (\"{enslaver}\")" if enslaver else " (name not yet known)"
                return {
                    "records_to_search": [
                        {
                            "type": "Slave Schedule (1860)",
                            "reason": (
                                f"If {full_name} was enslaved before 1865, this record lists "
                                f"them only by age and sex under their enslaver's name{enslaver_note}"
                            ),
                            "search_terms": f"slave schedule {enslaver or location} 1860",
                        },
                        {
                            "type": "Freedmen's Bureau Records",
                            "reason": (
                                "Labor contracts, marriage registers, and family records created "
                                "1865-1872 as freed people transitioned to citizenship"
                            ),
                            "search_terms": f"{full_name} Freedmen's Bureau {location}",
                        },
                        {
                            "type": "1870 Census",
                            "reason": (
                                "The first federal census to record formerly enslaved people by "
                                "full name as free citizens — the key record on the far side of "
                                "the 1870 brick wall"
                            ),
                            "search_terms": f"{full_name} 1870 census {location}",
                        },
                        {
                            "type": "Freedman's Bank Records",
                            "reason": "Often list a former enslaver's name and place of birth",
                            "search_terms": f"{full_name} Freedman's Savings Bank",
                        },
                    ],
                    "pre_1870_brick_wall": True,
                }
            return {
                "records_to_search": [
                    {
                        "type": "Birth Records",
                        "reason": "Primary source for birth date and location",
                        "search_terms": f"{full_name} {birth_year}"
                    },
                    {
                        "type": "Marriage Records",
                        "reason": "Likely exists given the era",
                        "search_terms": f"{full_name} marriage {birth_year + 20}-{birth_year + 35}"
                    },
                    {
                        "type": "Census Records",
                        "reason": f"Multiple census records plausible near {location}",
                        "search_terms": f"{full_name} census {location}"
                    }
                ],
                "pre_1870_brick_wall": False,
            }
        elif "scored_matches" in system_prompt:
            if pre_emancipation:
                return {
                    "scored_matches": [
                        {
                            "record_type": "Slave Schedule (1860)",
                            "source_id": "MOCK-SLS-0",
                            "confidence": 55,
                            "reasoning": (
                                "Age and location are consistent, but slave schedules record no "
                                "name — this is a plausible, not confirmed, match"
                            ),
                            "facts_extracted": {"enslaver": enslaver or "unknown", "location": location},
                        },
                        {
                            "record_type": "Freedmen's Bureau Records",
                            "source_id": "MOCK-FB-0",
                            "confidence": 90,
                            "reasoning": f"Name and location match for {full_name} in a labor contract",
                            "facts_extracted": {"location": location},
                        },
                        {
                            "record_type": "1870 Census",
                            "source_id": "MOCK-1870-0",
                            "confidence": 93,
                            "reasoning": f"Strong name, age, and location match for {full_name}",
                            "facts_extracted": {"birth_year": birth_year, "location": location},
                        },
                    ],
                    "conflicts": [],
                }
            return {
                "scored_matches": [
                    {
                        "record_type": "Birth Records",
                        "source_id": "MOCK-BIR-0",
                        "confidence": 95,
                        "reasoning": f"Perfect name and date match for {full_name}",
                        "facts_extracted": {"birth_year": birth_year, "location": location},
                    },
                    {
                        "record_type": "Marriage Records",
                        "source_id": "MOCK-MAR-0",
                        "confidence": 87,
                        "reasoning": "Name match, plausible date",
                        "facts_extracted": {},
                    },
                    {
                        "record_type": "Census Records",
                        "source_id": "MOCK-CEN-0",
                        "confidence": 72,
                        "reasoning": "Likely same person, minor name variant",
                        "facts_extracted": {},
                    },
                ],
                "conflicts": [],
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

def _likely_pre_emancipation(person: dict) -> bool:
    """True if the birth year suggests the person was likely born enslaved."""
    birth_year = person.get("birth_year")
    return bool(birth_year) and birth_year < 1866


def step1_research_plan(person: dict) -> dict:
    system = (
        "You are a professional genealogist who specializes in African American "
        "family history research, with deep expertise in tracing ancestry through "
        "and beyond the '1870 brick wall' — the 1870 U.S. Census was the first "
        "federal record to list formerly enslaved people by their own full name "
        "as free citizens, so records from before that date are usually indexed "
        "under the name of the person who enslaved them, not the ancestor's name. "
        "Given basic facts about a person, list which record types plausibly exist "
        "and are worth searching for, given the era and location. If the birth year "
        "suggests the person was likely born enslaved (before 1866), prioritize "
        "records indexed by their enslaver — slave schedules (1850/1860), "
        "plantation and probate/estate records — alongside Freedmen's Bureau "
        "records (1865-1872), Freedman's Bank records, and Reconstruction-era "
        "cohabitation/marriage registers. If a 'last_known_enslaver' is given, use "
        "it directly in the search terms for enslaver-indexed record types. "
        "Otherwise, use standard vital, census, and marriage records for the era. "
        "Respond ONLY with JSON: "
        '{"records_to_search": [{"type": "...", "reason": "...", "search_terms": "..."}], '
        '"pre_1870_brick_wall": true/false}'
    )
    user = f"Person details:\n{json.dumps(person, indent=2)}"
    return ask_claude_json(system, user)


def step2_search_records(person: dict, plan: dict) -> list:
    fs_client = st.session_state.fs_client
    common_args = dict(
        given_name=person.get("given_name", ""),
        surname=person.get("surname", ""),
        birth_year=person.get("birth_year"),
        location=person.get("location", ""),
        enslaver=person.get("last_known_enslaver", ""),
    )

    if not fs_client.demo_mode:
        # Live FamilySearch access (Unauthenticated Session) only supports a
        # single general Tree Person Search — it can't filter by collection
        # the way the planned record types imply — so one query covers the
        # whole plan instead of repeating an identical call per record type.
        matches = fs_client.search(record_type="FamilySearch Family Tree", **common_args)
        return [{
            "query": {
                "type": "FamilySearch Family Tree",
                "reason": "General search across FamilySearch's Family Tree",
            },
            "matches": matches,
        }]

    results = []
    for item in plan.get("records_to_search", []):
        matches = fs_client.search(record_type=item.get("type", ""), **common_args)
        results.append({"query": item, "matches": matches})
    return results


def step3_score_evidence(person: dict, search_results: list) -> dict:
    system = (
        "You are a genealogist specializing in African American family history, "
        "evaluating candidate records against a target person. For each match, "
        "assign a confidence score 0-100 based on name similarity, date proximity "
        "(allow +/-2 years), location consistency, and any family cross-references. "
        "Remember that pre-1866 records (slave schedules, plantation records) "
        "typically list enslaved people only by age, sex, and color under their "
        "enslaver's name rather than by their own name — score those on age/location "
        "consistency with the enslaver, not name match, and say so in your reasoning. "
        "Also remember that formerly enslaved people often adopted a new surname "
        "after emancipation, so a surname mismatch across 1865 is not itself a "
        "conflict. Flag genuine conflicts between sources (e.g. two different birth "
        "years) rather than silently picking one. "
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
        "You are a skilled family historian who writes warm, dignified, and "
        "historically grounded narratives about African American family history, "
        "based only on the confirmed facts provided — do not invent details. If "
        "the ancestor was likely enslaved, write about that plainly and with "
        "respect: acknowledge the injustice without dwelling on trauma for its own "
        "sake, and center the person's identity, agency, and the significance of "
        "what was found on either side of the 1870 brick wall. Where confidence is "
        "low or facts conflict, note the uncertainty gracefully rather than "
        "glossing over it. Write 3-5 short paragraphs."
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
st.caption(app_info["tagline"])

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
        st.success(
            "✅ **Live Mode**: Using the real Claude API. FamilySearch results come from its "
            "Family Tree (via the Unauthenticated Session grant) — other researchers' person "
            "profiles, often themselves citing historical records — not a direct search across "
            "every record collection like Freedmen's Bureau records or slave schedules."
        )
with col2:
    if not DEMO_MODE:
        st.metric("Mode", "Live", "active")

st.markdown(
    "This tool is built for a specific challenge in Black family history: most "
    "federal records only began naming formerly enslaved people as full citizens "
    "starting with the **1870 census**. Before that date, ancestors usually appear "
    "only indirectly — indexed under the name of the person who enslaved them. "
    "FREEDMENFINDER plans a research strategy that accounts for that shift, "
    "drawing on Freedmen's Bureau records, Freedman's Bank records, cohabitation "
    "registers, and slave schedules alongside standard vital and census records."
)

st.divider()

# Input form
with st.form("person_intake", clear_on_submit=False):
    st.subheader("1️⃣ Tell me about the person")

    col1, col2 = st.columns(2)
    with col1:
        given_name = st.text_input(
            "Given name",
            value="Moses",
            help="First or given name"
        )
    with col2:
        surname = st.text_input(
            "Surname",
            value="Freeman",
            help="Last or family name — note that many formerly enslaved people "
                 "adopted a new surname after emancipation, so this may differ "
                 "before and after 1865"
        )

    col3, col4 = st.columns(2)
    with col3:
        birth_year = st.number_input(
            "Approx. birth year",
            min_value=1700,
            max_value=2020,
            value=1852,
            help="Approximate year of birth"
        )
    with col4:
        location = st.text_input(
            "Approx. birth location",
            value="Charleston County, South Carolina",
            help="County, state, or region"
        )

    enslaver = st.text_input(
        "Last known enslaver's name or plantation (if applicable)",
        value="",
        placeholder="e.g., Thomas Heyward, or Heyward Plantation",
        help="If this ancestor was likely enslaved before 1865, this is often the "
             "single most useful piece of information — slave schedules, "
             "plantation, and probate records are indexed by the enslaver's name, "
             "not the enslaved person's name."
    )

    st.text_area(
        "Known relatives (optional)",
        placeholder="wife: Anna Freeman\nson: Moses Jr.",
        help="One relative per line, e.g., 'wife: Anna' or 'father: Johann'",
        key="relatives_input"
    )

    submitted = st.form_submit_button(
        "▶️ Run research pipeline", type="primary", use_container_width=True
    )

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
            "last_known_enslaver": enslaver.strip(),
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
                if plan.get("pre_1870_brick_wall"):
                    st.warning(
                        "🧱 **The 1870 brick wall** — based on the birth year, "
                        f"{given_name} was very likely born into slavery. Records "
                        "before 1870 rarely name enslaved people directly, so this "
                        "search leans on enslaver-indexed records (slave schedules, "
                        "plantation and probate records) alongside the Freedmen's "
                        "Bureau and Freedman's Bank records created during "
                        "Reconstruction."
                    )
                for rec in plan.get("records_to_search", []):
                    st.markdown(f"- **{rec.get('type', 'Record')}** — {rec.get('reason', '')}")

                st.write("**Step 2 — Searching records**")
                search_results = step2_search_records(person, plan)
                total_matches = sum(len(r["matches"]) for r in search_results)
                st.caption(
                    f"Found {total_matches} candidate record(s) across "
                    f"{len(search_results)} searches — details below."
                )
                for r in search_results:
                    label = r["query"].get("type", "Record")
                    st.markdown(f"- {label}: {len(r['matches'])} match(es)")

                st.write("**Step 3 — Scoring evidence & flagging conflicts**")
                scored = step3_score_evidence(person, search_results)
                for match in scored.get("scored_matches", []):
                    confidence = match.get("confidence", 0)
                    badge = "🟢" if confidence >= 85 else "🟡" if confidence >= 60 else "🔴"
                    st.markdown(
                        f"{badge} **{match.get('record_type', 'Record')}** — "
                        f"{confidence}% confidence  \n{match.get('reasoning', '')}"
                    )

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
        st.subheader(f"📖 {given_name} {surname}'s Story")
        with st.container(border=True):
            if isinstance(narrative, dict) and "narrative" in narrative:
                st.markdown(narrative["narrative"])
            else:
                st.markdown(narrative)

        st.subheader("🔎 Search Results")
        for r in search_results:
            label = r["query"].get("type", "Record")
            matches = r["matches"]
            with st.expander(f"{label} — {len(matches)} match(es)"):
                if not matches:
                    st.caption("No matches found in this search.")
                for m in matches:
                    st.markdown(
                        f"- **{m.get('name_as_recorded')}**, "
                        f"{m.get('year_as_recorded')} — {m.get('location_as_recorded')}  \n"
                        f"  *Source: {m.get('archive')}*"
                    )

        if scored.get("conflicts"):
            st.subheader("⚠️ Conflicts found (needs your review)")
            for c in scored["conflicts"]:
                with st.expander(f"❌ {c.get('description')}"):
                    st.write(f"**Sources**: {', '.join(c.get('sources', []))}")

        # Results summary + export
        gedcom_text = build_gedcom(person, scored)

        st.divider()
        st.subheader("📋 Record Summary")
        st.markdown(gedcom_to_plain_english(gedcom_text))

        st.divider()
        st.subheader("⬇️ Export")
        st.download_button(
            "📥 Download GEDCOM file",
            data=gedcom_text,
            file_name=f"{surname}_{given_name}.ged",
            mime="text/plain",
            help="Standard genealogy interchange format, importable into "
                 "software like Ancestry, MyHeritage, or Gramps.",
        )
        with st.expander("🔧 View raw GEDCOM (technical)"):
            st.code(gedcom_text, language="text", line_numbers=True)

