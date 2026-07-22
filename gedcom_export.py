"""
Convert research findings to GEDCOM format.
"""

_SPOUSE_RELATIONS = {"wife": "WIFE", "husband": "HUSB", "spouse": None, "partner": None}
_PARENT_RELATIONS = {"father": "HUSB", "mother": "WIFE"}
_CHILD_RELATIONS = {"son", "daughter", "child"}


def _parse_relative(entry: str) -> tuple[str, str]:
    """Split 'wife: Anna Novak' into ('wife', 'Anna Novak')."""
    relation, _, name = entry.partition(":")
    return relation.strip().lower(), name.strip()


def _format_gedcom_name(name: str) -> str:
    """Wrap the surname in slashes per GEDCOM convention: 'Anna Novak' -> 'Anna /Novak/'."""
    parts = name.split()
    if len(parts) < 2:
        return name
    return f"{' '.join(parts[:-1])} /{parts[-1]}/"


def build_gedcom(person: dict, scored: dict) -> str:
    """
    Build a GEDCOM file from person data, known relatives, and scored evidence.
    """
    surname = person.get("surname", "Unknown")
    given_name = person.get("given_name", "Unknown")
    birth_year = person.get("birth_year", 0)
    location = person.get("location", "Unknown")

    indi_records: list[tuple[str, list[str]]] = []  # (indi_id, body lines)
    fam_records: dict[str, list[str]] = {}  # fam_id -> body lines
    person_links = []  # FAMS/FAMC lines attached to @I1@
    unparsed_notes = []

    next_indi = 2
    next_fam = 1
    spouse_fam_id = None

    def new_indi(name: str, extra_lines: list[str]) -> str:
        nonlocal next_indi
        indi_id = f"@I{next_indi}@"
        next_indi += 1
        indi_records.append((indi_id, [f"1 NAME {_format_gedcom_name(name)}"] + extra_lines))
        return indi_id

    def new_fam() -> str:
        nonlocal next_fam
        fam_id = f"@F{next_fam}@"
        next_fam += 1
        fam_records[fam_id] = []
        return fam_id

    for entry in person.get("known_relatives", []):
        relation, name = _parse_relative(entry)
        if not name:
            if relation:
                unparsed_notes.append(entry)
            continue

        if relation in _SPOUSE_RELATIONS:
            fam_id = new_fam()
            role = _SPOUSE_RELATIONS[relation]
            spouse_id = new_indi(name, [f"1 FAMS {fam_id}"])
            husb, wife = (spouse_id, "@I1@") if role == "HUSB" else ("@I1@", spouse_id)
            fam_records[fam_id].extend([f"1 HUSB {husb}", f"1 WIFE {wife}"])
            person_links.append(f"1 FAMS {fam_id}")
            spouse_fam_id = fam_id

        elif relation in _PARENT_RELATIONS:
            fam_id = new_fam()
            tag = _PARENT_RELATIONS[relation]
            parent_id = new_indi(name, [f"1 FAMS {fam_id}"])
            fam_records[fam_id].extend([f"1 {tag} {parent_id}", "1 CHIL @I1@"])
            person_links.append(f"1 FAMC {fam_id}")

        elif relation in _CHILD_RELATIONS:
            if spouse_fam_id is None:
                spouse_fam_id = new_fam()
                fam_records[spouse_fam_id].append("1 HUSB @I1@")
                person_links.append(f"1 FAMS {spouse_fam_id}")
            child_id = new_indi(name, [f"1 FAMC {spouse_fam_id}"])
            fam_records[spouse_fam_id].append(f"1 CHIL {child_id}")

        else:
            unparsed_notes.append(f"{relation}: {name}" if relation else name)

    # Source citations from scored evidence
    sour_defs = []
    sour_refs = []
    for i, match in enumerate(scored.get("scored_matches", []), start=1):
        sour_id = f"@S{i}@"
        title = f"{match.get('record_type', 'Record')} ({match.get('source_id', 'unknown')})"
        text = f"{match.get('reasoning', '')} (confidence: {match.get('confidence', '?')})"
        sour_defs.extend([f"0 {sour_id} SOUR", f"1 TITL {title}", f"1 TEXT {text}"])
        sour_refs.append(f"1 SOUR {sour_id}")

    ged_lines = [
        "0 HEAD",
        "1 GEDC",
        "2 VERS 5.5.1",
        "1 CHAR UTF-8",
        "0 @I1@ INDI",
        f"1 NAME {given_name} /{surname}/",
        f"2 GIVN {given_name}",
        f"2 SURN {surname}",
        "1 BIRT",
        f"2 DATE {birth_year}",
        f"2 PLAC {location}",
        *person_links,
        *sour_refs,
    ]
    if unparsed_notes:
        ged_lines.append(f"1 NOTE Other known relatives: {'; '.join(unparsed_notes)}")

    for indi_id, lines in indi_records:
        ged_lines.append(f"0 {indi_id} INDI")
        ged_lines.extend(lines)

    for fam_id, lines in fam_records.items():
        ged_lines.append(f"0 {fam_id} FAM")
        ged_lines.extend(lines)

    ged_lines.extend(sour_defs)
    ged_lines.append("0 TRLR")

    return "\n".join(ged_lines)


# ---------- GEDCOM -> plain English ----------

def _split_tag(line: str) -> tuple[str, str]:
    """'NAME Josef /Novak/' -> ('NAME', 'Josef /Novak/')."""
    tag, _, value = line.partition(" ")
    return tag, value


def _parse_gedcom_records(gedcom_text: str) -> dict[str, dict]:
    """Group a GEDCOM file's lines by top-level (level 0) record."""
    records: dict[str, dict] = {}
    current = None
    for raw_line in gedcom_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        level, _, rest = line.partition(" ")
        if level == "0":
            xref, _, rtype = rest.partition(" ")
            current = records.setdefault(xref, {"type": rtype, "lines": []}) if xref.startswith("@") else None
        elif current is not None:
            current["lines"].append(line)
    return records


def _parse_indi(lines: list[str]) -> dict:
    data = {"name": None, "birth_date": None, "birth_place": None,
            "fams": [], "famc": [], "sour": [], "note": None}
    in_birt = False
    for line in lines:
        level, rest = line.split(" ", 1)
        tag, value = _split_tag(rest)
        if level == "1":
            in_birt = tag == "BIRT"
            if tag == "NAME":
                data["name"] = value.replace("/", "").strip()
            elif tag == "FAMS":
                data["fams"].append(value)
            elif tag == "FAMC":
                data["famc"].append(value)
            elif tag == "SOUR":
                data["sour"].append(value)
            elif tag == "NOTE":
                data["note"] = value
        elif level == "2" and in_birt:
            if tag == "DATE":
                data["birth_date"] = value
            elif tag == "PLAC":
                data["birth_place"] = value
    return data


def _parse_fam(lines: list[str]) -> dict:
    data = {"husb": None, "wife": None, "chil": []}
    for line in lines:
        level, rest = line.split(" ", 1)
        if level != "1":
            continue
        tag, value = _split_tag(rest)
        if tag == "HUSB":
            data["husb"] = value
        elif tag == "WIFE":
            data["wife"] = value
        elif tag == "CHIL":
            data["chil"].append(value)
    return data


def _parse_sour(lines: list[str]) -> dict:
    data = {"title": None, "text": None}
    for line in lines:
        level, rest = line.split(" ", 1)
        if level != "1":
            continue
        tag, value = _split_tag(rest)
        if tag == "TITL":
            data["title"] = value
        elif tag == "TEXT":
            data["text"] = value
    return data


def gedcom_to_plain_english(gedcom_text: str) -> str:
    """Translate a GEDCOM file back into a plain-English summary."""
    records = _parse_gedcom_records(gedcom_text)
    indis = {xref: _parse_indi(r["lines"]) for xref, r in records.items() if r["type"] == "INDI"}
    fams = {xref: _parse_fam(r["lines"]) for xref, r in records.items() if r["type"] == "FAM"}
    sours = {xref: _parse_sour(r["lines"]) for xref, r in records.items() if r["type"] == "SOUR"}

    root = indis.get("@I1@")
    if not root:
        return "No person record found in this GEDCOM file."

    name = root["name"] or "This person"
    sentences = []

    if root["birth_date"] or root["birth_place"]:
        when = f" around {root['birth_date']}" if root["birth_date"] else ""
        where = f" in {root['birth_place']}" if root["birth_place"] else ""
        sentences.append(f"**{name}** was born{when}{where}.")
    else:
        sentences.append(f"**{name}**")

    for fam_id in root["famc"]:
        fam = fams.get(fam_id, {})
        parents = [indis[pid]["name"] for pid in (fam.get("husb"), fam.get("wife"))
                   if pid and pid in indis]
        if parents:
            sentences.append(f"Parents: {' and '.join(parents)}.")

    for fam_id in root["fams"]:
        fam = fams.get(fam_id, {})
        spouse_id = fam.get("wife") if fam.get("husb") == "@I1@" else fam.get("husb")
        spouse_name = indis[spouse_id]["name"] if spouse_id in indis else None
        children = [indis[cid]["name"] for cid in fam.get("chil", []) if cid in indis]
        if spouse_name:
            sentences.append(f"Spouse: {spouse_name}.")
        if children:
            sentences.append(f"Children: {', '.join(children)}.")

    if root["sour"]:
        lines = ["", "**Supporting evidence:**"]
        for sid in root["sour"]:
            source = sours.get(sid)
            if source:
                lines.append(f"- {source.get('title', 'Source')} — {source.get('text', '')}")
        sentences.append("\n".join(lines))

    if root["note"]:
        sentences.append(f"\n*{root['note']}*")

    return "\n\n".join(sentences)
