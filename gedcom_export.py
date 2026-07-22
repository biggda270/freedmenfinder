"""
Convert research findings to GEDCOM format.
"""

def build_gedcom(person: dict, scored: dict) -> str:
    """
    Build a simple GEDCOM file from person data and scored evidence.
    """
    surname = person.get("surname", "Unknown")
    given_name = person.get("given_name", "Unknown")
    birth_year = person.get("birth_year", 0)
    location = person.get("location", "Unknown")
    
    ged_lines = [
        "0 HEAD",
        "1 GEDC",
        "2 VERS 5.5.1",
        "1 CHAR UTF-8",
        "0 @I1@ INDI",
        f"1 NAME {given_name} /{surname}/",
        f"2 GIVN {given_name}",
        f"2 SURN {surname}",
        f"1 BIRT",
        f"2 DATE {birth_year}",
        f"2 PLAC {location}",
        "0 TRLR",
    ]
    
    return "\n".join(ged_lines)