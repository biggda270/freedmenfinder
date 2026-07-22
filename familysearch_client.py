"""
Thin client for the FamilySearch API, with a demo mode that returns
realistic mock records so you can test the full pipeline before your
FamilySearch developer account is approved.

To go live:
  1. Register at https://www.familysearch.org/developers/
  2. Create a project, get your API key / OAuth credentials
  3. Set DEMO_MODE=False in .env and fill in FAMILYSEARCH_ACCESS_TOKEN
  4. Replace the TODO section in `_live_search` with real API calls per
     https://www.familysearch.org/developers/docs/api/tree/Search_for_Persons_resource
"""

import os
import random


class FamilySearchClient:
    def __init__(self, demo_mode: bool = True):
        self.demo_mode = demo_mode
        self.access_token = os.environ.get("FAMILYSEARCH_ACCESS_TOKEN")

    def search(self, given_name, surname, birth_year, location, record_type):
        if self.demo_mode:
            return self._mock_search(given_name, surname, birth_year, location, record_type)
        return self._live_search(given_name, surname, birth_year, location, record_type)

    # ---------- DEMO MODE ----------
    def _mock_search(self, given_name, surname, birth_year, location, record_type):
        """Generates plausible-looking mock matches with some deliberate
        noise (spelling variants, year drift) so the scoring step has
        something real to evaluate."""
        random.seed(f"{given_name}{surname}{birth_year}{record_type}")
        variants = [given_name, given_name[:-1] + "ph" if given_name.endswith("f") else given_name]
        surname_variants = [surname, surname.replace("v", "w")]

        n_matches = random.randint(1, 3)
        matches = []
        for i in range(n_matches):
            year_drift = random.choice([0, 0, 1, -2])
            matches.append({
                "source_id": f"MOCK-{record_type[:3].upper()}-{i}",
                "record_type": record_type,
                "name_as_recorded": f"{random.choice(variants)} {random.choice(surname_variants)}",
                "year_as_recorded": birth_year + year_drift,
                "location_as_recorded": location,
                "archive": "FamilySearch (demo)",
            })
        return matches

    # ---------- LIVE MODE ----------
    def _live_search(self, given_name, surname, birth_year, location, record_type):
        """
        TODO: implement real FamilySearch API call, e.g.:

        import requests
        resp = requests.get(
            "https://api.familysearch.org/platform/tree/search",
            headers={"Authorization": f"Bearer {self.access_token}"},
            params={
                "q.givenName": given_name,
                "q.surname": surname,
                "q.birthLikeDate": str(birth_year),
                "q.birthLikePlace": location,
            },
        )
        return resp.json().get("entries", [])
        """
        raise NotImplementedError(
            "Live FamilySearch integration not yet implemented. "
            "Set DEMO_MODE=True in .env, or implement _live_search() "
            "once your API credentials are ready."
        )
