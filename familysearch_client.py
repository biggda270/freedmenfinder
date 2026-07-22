"""
Thin client for the FamilySearch API, with a demo mode that returns
realistic mock records so you can test the full pipeline before your
FamilySearch developer app is approved.

Live mode uses FamilySearch's "Unauthenticated Session" OAuth2 grant (no
personal login required) against the Tree Person Search resource. That grant
is limited by FamilySearch to a handful of resources — Places, the Date
Authority, Person Search, Person Matches Query, and Relationship Finder — and
does NOT cover a general historical-records archive search. In practice this
means live results come from FamilySearch's crowd-sourced Family Tree (other
researchers' person profiles, often themselves citing historical records),
not a direct search across every record collection like Freedmen's Bureau
records or slave schedules. Those specific collections require the broader
Authorization Code (real user login) grant, which this client does not yet
implement.

To go live:
  1. Register at https://www.familysearch.org/developers/ and confirm your
     app's Client ID has "Unauthenticated Session" access enabled.
  2. Set DEMO_MODE=False and FAMILYSEARCH_CLIENT_ID in your .env file.
  3. FamilySearch's per-resource API reference pages require a logged-in
     developer session to view, so the exact base URLs and response shape
     below could not be independently verified while building this and may
     need adjustment — check error messages/logs against your Developer
     Center account if live search calls fail, and confirm the environment
     hostnames in _ENVIRONMENTS below match what your app's settings show.
"""

import logging
import os
import random

import requests

logger = logging.getLogger(__name__)

# FamilySearch environment hosts. These are FamilySearch's commonly
# documented defaults; per the module docstring, they could not be verified
# against the (auth-gated) per-app reference pages, so override them with
# FAMILYSEARCH_IDENT_URL / FAMILYSEARCH_API_URL if your app's Developer
# Center settings show something different.
_ENVIRONMENTS = {
    "integration": {  # formerly called "sandbox"
        "ident": "https://identint.familysearch.org",
        "api": "https://api-integ.familysearch.org",
    },
    "production": {
        "ident": "https://ident.familysearch.org",
        "api": "https://api.familysearch.org",
    },
}


class FamilySearchAuthError(RuntimeError):
    """Raised when FamilySearch OAuth token acquisition fails."""


def _archive_for(record_type: str) -> str:
    """Map a demo-mode record type to a historically appropriate archive name."""
    rt = record_type.lower()
    if "freedmen's bureau" in rt or "freedmen bureau" in rt:
        return "Freedmen's Bureau Records, National Archives (demo)"
    if "freedman's bank" in rt or "freedman bank" in rt or "freedmen's savings" in rt:
        return "Freedman's Savings & Trust Records, NARA (demo)"
    if "slave schedule" in rt:
        return "U.S. Federal Slave Schedules, 1850/1860 (demo)"
    if "cohabitation" in rt:
        return "Reconstruction-era Cohabitation Register (demo)"
    if "wpa" in rt or "slave narrative" in rt:
        return "WPA Slave Narrative Collection, Library of Congress (demo)"
    if "plantation" in rt or "probate" in rt or "estate" in rt:
        return "County Probate & Estate Records (demo)"
    return "FamilySearch (demo)"


class FamilySearchClient:
    def __init__(self, demo_mode: bool = True, client_id: str = None,
                 environment: str = "integration", access_token: str = None):
        self.demo_mode = demo_mode
        self.client_id = client_id or os.environ.get("FAMILYSEARCH_CLIENT_ID")

        env = _ENVIRONMENTS.get((environment or "integration").strip().lower(),
                                 _ENVIRONMENTS["integration"])
        self.ident_base_url = os.environ.get("FAMILYSEARCH_IDENT_URL", env["ident"])
        self.api_base_url = os.environ.get("FAMILYSEARCH_API_URL", env["api"])

        # A manually-supplied token (e.g. from a one-time Authorization Code
        # login) is used as-is and never auto-refreshed. Without one, we fetch
        # and cache an Unauthenticated Session token on first use.
        self._preset_token = access_token or os.environ.get("FAMILYSEARCH_ACCESS_TOKEN") or None
        self._fetched_token = None
        self._search_cache = {}

    def search(self, given_name, surname, birth_year, location, record_type, enslaver=""):
        if self.demo_mode:
            return self._mock_search(given_name, surname, birth_year, location, record_type, enslaver)
        return self._live_search(given_name, surname, birth_year, location, record_type, enslaver)

    # ---------- DEMO MODE ----------
    def _mock_search(self, given_name, surname, birth_year, location, record_type, enslaver=""):
        """Generates plausible-looking mock matches with some deliberate
        noise (spelling variants, year drift) so the scoring step has
        something real to evaluate.

        Slave schedules are handled specially: unlike other 19th-century
        records, they never recorded an enslaved person's name — only age,
        sex, and color under the name of the person who enslaved them. The
        mock reflects that instead of pretending a name match exists.
        """
        random.seed(f"{given_name}{surname}{birth_year}{record_type}")
        archive = _archive_for(record_type)
        n_matches = random.randint(1, 3)
        matches = []

        if "slave schedule" in record_type.lower():
            for i in range(n_matches):
                age = max(0, (1860 - birth_year)) if birth_year else random.randint(1, 40)
                age += random.choice([-1, 0, 0, 1])
                enslaver_label = enslaver.strip() or "enslaver not specified"
                matches.append({
                    "source_id": f"MOCK-SLS-{i}",
                    "record_type": record_type,
                    "name_as_recorded": f"[unnamed], age {max(age, 0)}, listed under \"{enslaver_label}\"",
                    "year_as_recorded": 1860,
                    "location_as_recorded": location,
                    "archive": archive,
                })
            return matches

        variants = [given_name, given_name[:-1] + "ph" if given_name.endswith("f") else given_name]
        surname_variants = [surname, surname.replace("v", "w")] if surname else [surname]

        for i in range(n_matches):
            year_drift = random.choice([0, 0, 1, -2])
            matches.append({
                "source_id": f"MOCK-{record_type[:3].upper()}-{i}",
                "record_type": record_type,
                "name_as_recorded": f"{random.choice(variants)} {random.choice(surname_variants)}",
                "year_as_recorded": birth_year + year_drift,
                "location_as_recorded": location,
                "archive": archive,
            })
        return matches

    # ---------- LIVE MODE ----------
    def _get_access_token(self, force_refresh: bool = False) -> str:
        if self._preset_token:
            if force_refresh:
                raise FamilySearchAuthError(
                    "The configured FAMILYSEARCH_ACCESS_TOKEN was rejected by FamilySearch "
                    "(likely expired). Obtain a fresh token, or remove FAMILYSEARCH_ACCESS_TOKEN "
                    "to fall back to the automatic Unauthenticated Session flow."
                )
            return self._preset_token

        if self._fetched_token and not force_refresh:
            return self._fetched_token

        if not self.client_id:
            raise FamilySearchAuthError(
                "FAMILYSEARCH_CLIENT_ID is not set. Register an app at "
                "https://www.familysearch.org/developers/ and add its Client ID to your "
                "configuration, or set FAMILYSEARCH_ACCESS_TOKEN directly."
            )

        try:
            resp = requests.post(
                f"{self.ident_base_url}/cis-web/oauth2/v3/token",
                data={"grant_type": "unauthenticated_session", "client_id": self.client_id},
                headers={"Accept": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise FamilySearchAuthError(f"Could not reach FamilySearch's identity service: {e}") from e

        token = resp.json().get("access_token")
        if not token:
            raise FamilySearchAuthError(
                "FamilySearch did not return an access_token for the Unauthenticated Session "
                "request. Confirm your app's Client ID has that grant type enabled in the "
                "FamilySearch Developer Center."
            )
        self._fetched_token = token
        return token

    def _live_search(self, given_name, surname, birth_year, location, record_type="", enslaver=""):
        # The Unauthenticated Session grant only supports a single general
        # Tree Person Search — it cannot filter by collection/record type, so
        # record_type and enslaver (used only for demo-mode presentation) are
        # not applicable here.
        cache_key = (given_name, surname, birth_year, location)
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]

        params = {}
        if given_name:
            params["q.givenName"] = given_name
        if surname:
            params["q.surname"] = surname
        if birth_year:
            params["q.birthLikeDate"] = str(birth_year)
        if location:
            params["q.birthLikePlace"] = location

        matches = self._request_person_search(params, retry_on_auth_error=True)
        self._search_cache[cache_key] = matches
        return matches

    def _request_person_search(self, params: dict, retry_on_auth_error: bool) -> list:
        token = self._get_access_token()
        try:
            resp = requests.get(
                f"{self.api_base_url}/platform/tree/search",
                params=params,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                timeout=20,
            )
        except requests.RequestException as e:
            raise RuntimeError(f"Could not reach FamilySearch: {e}") from e

        if resp.status_code == 401 and retry_on_auth_error:
            logger.info("FamilySearch access token was rejected; requesting a new one.")
            self._get_access_token(force_refresh=True)
            return self._request_person_search(params, retry_on_auth_error=False)

        if not resp.ok:
            raise RuntimeError(
                f"FamilySearch search failed with status {resp.status_code}. Confirm your "
                "app's Client ID has Person Search access enabled in the Developer Center."
            )

        try:
            data = resp.json()
        except ValueError as e:
            raise RuntimeError("FamilySearch returned a non-JSON response.") from e

        return self._parse_person_search_response(data)

    @staticmethod
    def _parse_person_search_response(data: dict) -> list:
        """Parse FamilySearch's GEDCOM X-based Tree Person Search response.

        FamilySearch's per-resource API reference (exact field guarantees)
        requires a logged-in developer session to view and could not be
        verified independently — this defensively walks the documented
        GEDCOM X shape (entries[].content.gedcomx.persons[0]) and skips any
        entry it can't parse rather than raising, but logs a warning so a
        shape mismatch is visible instead of silently returning nothing.
        """
        entries = data.get("entries", [])
        if not entries and "entries" not in data:
            logger.warning("Unexpected FamilySearch search response shape: no 'entries' field found.")

        matches = []
        for entry in entries:
            try:
                persons = entry.get("content", {}).get("gedcomx", {}).get("persons", [])
                if not persons:
                    continue
                person = persons[0]

                name = "Unknown"
                for name_record in person.get("names", []):
                    for form in name_record.get("nameForms", []):
                        if form.get("fullText"):
                            name = form["fullText"]
                            break
                    if name != "Unknown":
                        break

                birth_year = None
                birth_place = None
                for fact in person.get("facts", []):
                    if fact.get("type") == "http://gedcomx.org/Birth":
                        original_date = fact.get("date", {}).get("original", "")
                        for token in original_date.replace(",", " ").split():
                            if token.isdigit() and len(token) == 4:
                                birth_year = int(token)
                                break
                        birth_place = fact.get("place", {}).get("original")
                        break

                person_id = person.get("id")
                archive = "FamilySearch Family Tree"
                if person_id:
                    archive += f" — familysearch.org/tree/person/details/{person_id}"

                matches.append({
                    "source_id": entry.get("id", person_id or "unknown"),
                    "record_type": "FamilySearch Family Tree",
                    "name_as_recorded": name,
                    "year_as_recorded": birth_year,
                    "location_as_recorded": birth_place,
                    "archive": archive,
                })
            except (AttributeError, TypeError, KeyError) as e:
                logger.warning(f"Skipping unparseable FamilySearch search entry: {e}")
                continue

        return matches
