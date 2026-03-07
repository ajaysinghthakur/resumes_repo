#!/usr/bin/env python3
"""
parse_json.py  —  JSONResume v1.0.0 → LaTeX resume generator
=============================================================
Single source of truth: input/resume.json

Schema: https://jsonresume.org/schema
        https://raw.githubusercontent.com/jsonresume/resume-schema/master/schema.json

Usage:
  python3 parse_json.py                    # parse + validate
  python3 parse_json.py --build            # parse + pdflatex
  python3 parse_json.py --validate         # validate only, no file output
  python3 parse_json.py --input path.json  # custom input file
  python3 parse_json.py --watch            # watch & rebuild on save
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────
DEFAULT_INPUT = Path("input") / "resume.json"
OUTPUT_DIR    = Path("output")

# ─────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────
_WARNINGS = []

def warn(msg):
    _WARNINGS.append(msg)
    print(f"  ⚠  {msg}")

def fatal(msg):
    print(f"\n  ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

def esc(value):
    """
    Return value as a LaTeX-safe string.
    Escapes bare & so company names like 'Texas A&M' compile correctly.
    Values already written as LaTeX (\\& etc.) are left untouched.
    """
    if value is None:
        return ""
    s = str(value).strip()
    out, prev = [], ""
    for ch in s:
        if ch == "&" and prev != "\\":
            out.append("\\&")
        else:
            out.append(ch)
        prev = ch
    return "".join(out)

def tex_url(url, label=None):
    """Clickable \\href{url}{label}, or bare label when url is empty."""
    u = esc(url)
    l = esc(label) if label else u
    return f"\\href{{{u}}}{{{l}}}" if u else l

def w(filename, text):
    """Write to output dir and confirm."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / filename).write_text(text, encoding="utf-8")
    print(f"  [OK] output/{filename}")

def fmt_date(value, label="date"):
    """
    Accept ISO date (YYYY-MM-DD, YYYY-MM, YYYY), date object, or '' for present.
    Returns display string like 'Aug. 2021' or 'Present'.
    """
    if value is None or str(value).strip() == "":
        return "Present"
    s = str(value).strip().lower()
    if s in ("present", "now", "current"):
        return "Present"
    try:
        if isinstance(value, (date, datetime)):
            d = value if isinstance(value, date) else value.date()
        elif len(s) == 4:
            d = date(int(s), 1, 1)
        elif len(s) == 7:
            d = date(int(s[:4]), int(s[5:7]), 1)
        else:
            d = date.fromisoformat(s[:10])
        return d.strftime("%b. %Y")
    except (ValueError, AttributeError):
        warn(f"'{value}' is not a valid ISO date for {label}; using as-is.")
        return esc(value)

def date_range(start, end):
    """Return 'Aug. 2018 -- May 2021' or 'Jun. 2020 -- Present'."""
    s = fmt_date(start, "startDate")
    e = fmt_date(end,   "endDate")
    if s == "Present" and e == "Present":
        return ""
    if s and e:
        return f"{s} -- {e}"
    return s or e

def bullets_tex(items, indent="        "):
    """Convert a list of strings to \\resumeItem lines."""
    return "\n".join(f"{indent}\\resumeItem{{{esc(b)}}}" for b in (items or []))

# ─────────────────────────────────────────────────────────────
# JSON loader
# ─────────────────────────────────────────────────────────────
def load_json(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        fatal(f"Invalid JSON in {path}: {e}")
    if not isinstance(data, dict):
        fatal("resume.json must be a JSON object at the top level.")
    return data

# ─────────────────────────────────────────────────────────────
# Validation  (JSONResume v1.0.0)
# ─────────────────────────────────────────────────────────────
def validate(data: dict) -> bool:
    basics = data.get("basics") or {}
    if not basics.get("name"):
        warn("basics.name is missing (recommended minimum).")
    if not basics.get("email"):
        warn("basics.email is missing (recommended minimum).")

    # Date sanity check
    for section in ("work", "education", "volunteer", "projects"):
        for i, e in enumerate(data.get(section) or []):
            s_raw = e.get("startDate", "")
            e_raw = e.get("endDate", "")
            if s_raw and e_raw and str(e_raw).strip() not in ("", "present", "now", "current"):
                try:
                    sd = date.fromisoformat(str(s_raw)[:10])
                    ed = date.fromisoformat(str(e_raw)[:10])
                    if ed < sd:
                        warn(f"{section}[{i}] endDate ({e_raw}) is before startDate ({s_raw}).")
                except ValueError:
                    pass

    # Warn about non-standard legacy keys
    for old, new in [("personal","basics"), ("experience","work"), ("certifications","certificates")]:
        if old in data:
            warn(f"Non-standard key '{old}' found — JSONResume standard uses '{new}'.")

    return len(_WARNINGS) == 0

# ─────────────────────────────────────────────────────────────
# Section generators
# ─────────────────────────────────────────────────────────────

def gen_basics(data: dict, version: str):
    """basics → output/basics_data.tex  (\\newcommand macros for resume.tex)"""
    b   = data.get("basics") or {}
    loc = b.get("location") or {}

    def nc(name, value):
        return f"\\newcommand{{\\resume{name}}}{{{esc(value)}}}"

    # Build city/region display from structured location
    city   = esc(loc.get("city", ""))
    region = esc(loc.get("region", ""))
    location_str = ", ".join(filter(None, [city, region]))

    lines = [
        f"% basics_data.tex — generated from resume.json {version}",
        nc("Name",     b.get("name")),
        nc("Label",    b.get("label")),
        nc("Image",    b.get("image")),
        nc("Email",    b.get("email")),
        nc("Phone",    b.get("phone")),
        nc("Website",  b.get("url")),
        nc("Summary",  b.get("summary")),
        nc("Location", location_str),
        # Structured location sub-fields
        nc("LocationCity",       loc.get("city")),
        nc("LocationRegion",     loc.get("region")),
        nc("LocationPostalCode", loc.get("postalCode")),
        nc("LocationCountry",    loc.get("countryCode")),
        nc("LocationAddress",    loc.get("address")),
    ]

    # profiles[] → per-network macros
    profiles = b.get("profiles") or []
    for prof in profiles:
        net = esc(prof.get("network", "")).replace(" ", "")
        if not net:
            continue
        username = esc(prof.get("username", ""))
        url      = esc(prof.get("url", ""))
        label    = username or url   # display label prefers username
        lines += [
            nc(f"{net}Username", username),
            nc(f"{net}URL",      url),
            nc(f"{net}Label",    label),
        ]

    # Legacy \providecommand aliases for LinkedIn / GitHub
    # (\providecommand avoids 'already defined' if network was listed above)
    for net_name, idx in [("LinkedIn", 0), ("GitHub", 1)]:
        if idx < len(profiles):
            prof = profiles[idx]
            lv = esc(prof.get("username") or prof.get("url") or "")
            uv = esc(prof.get("url") or "")
        else:
            lv, uv = "", ""
        lines += [
            f"\\providecommand{{\\resume{net_name}Label}}{{{lv}}}",
            f"\\providecommand{{\\resume{net_name}URL}}{{{uv}}}",
        ]

    # Any extra flat basics fields become macros automatically
    known = {"name","label","image","email","phone","url",
             "summary","location","profiles"}
    for key, val in b.items():
        if key not in known and not isinstance(val, (dict, list)):
            macro = "resume" + key.strip().title().replace(" ", "")
            lines.append(f"\\newcommand{{\\{macro}}}{{{esc(val)}}}")

    w("basics_data.tex", "\n".join(lines) + "\n")


def gen_work(entries: list) -> str:
    """work[] — name(company), position(title), highlights(bullets)"""
    out = []
    for e in (entries or []):
        dr       = date_range(e.get("startDate"), e.get("endDate"))
        company  = esc(e.get("name", ""))
        url      = esc(e.get("url", ""))
        co_fmt   = tex_url(url, company) if url else company
        block = (
            f"    \\resumeSubheading\n"
            f"      {{{co_fmt}}}{{{dr}}}\n"
            f"      {{{esc(e.get('position',''))}}}{{{esc(e.get('location',''))}}}\n"
        )
        hi = e.get("highlights") or []
        if hi:
            block += f"      \\resumeItemListStart\n{bullets_tex(hi)}\n      \\resumeItemListEnd\n"
        out.append(block)
    return "\n".join(out)


def gen_education(entries: list) -> str:
    """education[] — institution, area, studyType, score(GPA), courses[]"""
    out = []
    for e in (entries or []):
        dr       = date_range(e.get("startDate"), e.get("endDate"))
        inst     = esc(e.get("institution", ""))
        url      = esc(e.get("url", ""))
        inst_fmt = tex_url(url, inst) if url else inst
        study    = esc(e.get("studyType", ""))
        area     = esc(e.get("area", ""))
        degree   = f"{study} in {area}" if study and area else (study or area)
        block = (
            f"    \\resumeSubheading\n"
            f"      {{{inst_fmt}}}{{{esc(e.get('location',''))}}}\n"
            f"      {{{degree}}}{{{dr}}}\n"
        )
        extras = []
        if e.get("score"):
            extras.append(f"GPA: {esc(e['score'])}")
        for c in (e.get("courses") or []):
            extras.append(f"Course: {esc(c)}")
        if extras:
            blines = "\n".join(f"        \\resumeItem{{{x}}}" for x in extras)
            block += f"      \\resumeItemListStart\n{blines}\n      \\resumeItemListEnd\n"
        out.append(block)
    return "\n".join(out)


def gen_volunteer(entries: list) -> str:
    """volunteer[] — organization, position, highlights[]"""
    out = []
    for e in (entries or []):
        dr      = date_range(e.get("startDate"), e.get("endDate"))
        org     = esc(e.get("organization", ""))
        url     = esc(e.get("url", ""))
        org_fmt = tex_url(url, org) if url else org
        block = (
            f"    \\resumeSubheading\n"
            f"      {{{esc(e.get('position',''))}}}{{{dr}}}\n"
            f"      {{{org_fmt}}}{{{esc(e.get('location',''))}}}\n"
        )
        hi = e.get("highlights") or []
        if hi:
            block += f"      \\resumeItemListStart\n{bullets_tex(hi)}\n      \\resumeItemListEnd\n"
        out.append(block)
    return "\n".join(out)


def gen_skills(entries) -> str:
    """
    skills[] — name, level (Beginner|Intermediate|Advanced|Master), keywords[]
    Also handles legacy flat dict format.
    """
    lines = []
    if isinstance(entries, list):
        for i, s in enumerate(entries):
            name   = esc(s.get("name", ""))
            level  = esc(s.get("level", ""))
            kw     = ", ".join(esc(k) for k in (s.get("keywords") or []))
            suffix = " \\\\" if i < len(entries) - 1 else ""
            parts  = []
            if level: parts.append(f"\\textit{{{level}}}")
            if kw:    parts.append(kw)
            value = " -- ".join(parts) if parts else ""
            lines.append(f"     \\textbf{{{name}}}{{: {value}}}{suffix}")
    elif isinstance(entries, dict):
        items = list(entries.items())
        for i, (cat, vals) in enumerate(items):
            suffix = " \\\\" if i < len(items) - 1 else ""
            lines.append(f"     \\textbf{{{cat}}}{{: {esc(vals)}}}{suffix}")
    return "\\small{\\item{\n" + "\n".join(lines) + "\n    }}"


def gen_projects(entries: list) -> str:
    """projects[] — name, keywords[], highlights[], url, startDate, endDate"""
    out = []
    for e in (entries or []):
        name = esc(e.get("name", ""))
        url  = esc(e.get("url", ""))
        dr   = date_range(e.get("startDate"), e.get("endDate"))
        kw   = ", ".join(esc(k) for k in (e.get("keywords") or []))
        hi   = e.get("highlights") or []

        heading = f"\\textbf{{{tex_url(url, name) if url else name}}}"
        if kw:
            heading += f" $|$ \\emph{{{kw}}}"

        block = f"      \\resumeProjectHeading\n          {{{heading}}}{{{dr}}}\n"
        if hi:
            block += f"          \\resumeItemListStart\n{bullets_tex(hi)}\n          \\resumeItemListEnd\n"
        out.append(block)
    return "\n".join(out)


def gen_awards(entries: list) -> str:
    """awards[] — title, date, awarder, summary"""
    out = []
    for e in (entries or []):
        block = (
            f"    \\resumeSubheading\n"
            f"      {{{esc(e.get('title',''))}}}{{{fmt_date(e.get('date'))}}}\n"
            f"      {{{esc(e.get('awarder',''))}}}{{}}\n"
        )
        if e.get("summary"):
            block += (
                f"      \\resumeItemListStart\n"
                f"        \\resumeItem{{{esc(e['summary'])}}}\n"
                f"      \\resumeItemListEnd\n"
            )
        out.append(block)
    return "\n".join(out)


def gen_certificates(entries: list) -> str:
    """certificates[] — name, date, issuer, url  (JSONResume key: certificates)"""
    out = []
    for e in (entries or []):
        nm     = esc(e.get("name", ""))
        url    = esc(e.get("url", ""))
        nm_fmt = tex_url(url, nm) if url else nm
        out.append(
            f"    \\resumeSubheading\n"
            f"      {{{nm_fmt}}}{{{fmt_date(e.get('date'))}}}\n"
            f"      {{{esc(e.get('issuer',''))}}}{{}}\n"
        )
    return "\n".join(out)


def gen_publications(entries: list) -> str:
    """publications[] — name, publisher, releaseDate, url, summary"""
    out = []
    for e in (entries or []):
        nm     = esc(e.get("name", ""))
        url    = esc(e.get("url", ""))
        nm_fmt = tex_url(url, nm) if url else nm
        d      = fmt_date(e.get("releaseDate") or e.get("date"))
        block  = (
            f"    \\resumeSubheading\n"
            f"      {{{nm_fmt}}}{{{d}}}\n"
            f"      {{{esc(e.get('publisher',''))}}}{{}}\n"
        )
        if e.get("summary"):
            block += (
                f"      \\resumeItemListStart\n"
                f"        \\resumeItem{{{esc(e['summary'])}}}\n"
                f"      \\resumeItemListEnd\n"
            )
        out.append(block)
    return "\n".join(out)


def gen_languages(entries: list) -> str:
    """languages[] — language, fluency"""
    lines = []
    for i, lang in enumerate(entries or []):
        suffix = " \\\\" if i < len(entries) - 1 else ""
        lines.append(
            f"     \\textbf{{{esc(lang.get('language',''))}}}{{: {esc(lang.get('fluency',''))}}}{suffix}"
        )
    return "\\small{\\item{\n" + "\n".join(lines) + "\n    }}"


def gen_interests(entries: list) -> str:
    """interests[] — name, keywords[]"""
    lines = []
    for i, item in enumerate(entries or []):
        kw     = ", ".join(esc(k) for k in (item.get("keywords") or []))
        suffix = " \\\\" if i < len(entries) - 1 else ""
        lines.append(f"     \\textbf{{{esc(item.get('name',''))}}}{{: {kw}}}{suffix}")
    return "\\small{\\item{\n" + "\n".join(lines) + "\n    }}"


def gen_references(entries: list) -> str:
    """references[] — name, reference"""
    out = []
    for e in (entries or []):
        block = (
            f"    \\resumeSubheading\n"
            f"      {{{esc(e.get('name',''))}}}{{}}\n"
            f"      {{}}{{}}\n"
        )
        if e.get("reference"):
            block += (
                f"      \\resumeItemListStart\n"
                f"        \\resumeItem{{{esc(e['reference'])}}}\n"
                f"      \\resumeItemListEnd\n"
            )
        out.append(block)
    return "\n".join(out)


def gen_custom_section(key: str, entries) -> str:
    """Auto-renderer for non-standard / user-added sections."""
    if isinstance(entries, dict):
        items = list(entries.items())
        lines = []
        for i, (k, v) in enumerate(items):
            suffix = " \\\\" if i < len(items) - 1 else ""
            lines.append(f"     \\textbf{{{k}}}{{: {esc(v)}}}{suffix}")
        return "\\small{\\item{\n" + "\n".join(lines) + "\n    }}"

    if isinstance(entries, list):
        if all(isinstance(e, str) for e in entries):
            blines = "\n".join(f"  \\resumeItem{{{esc(b)}}}" for b in entries)
            return f"  \\resumeItemListStart\n{blines}\n  \\resumeItemListEnd"
        if all(isinstance(e, dict) for e in entries):
            out = []
            for e in entries:
                keys = list(e.keys())
                c = [esc(e.get(keys[j], "")) if j < len(keys) else "" for j in range(4)]
                block = (
                    f"    \\resumeSubheading\n"
                    f"      {{{c[0]}}}{{{c[1]}}}\n"
                    f"      {{{c[2]}}}{{{c[3]}}}\n"
                )
                hi = e.get("highlights") or []
                if hi:
                    block += f"      \\resumeItemListStart\n{bullets_tex(hi)}\n      \\resumeItemListEnd\n"
                out.append(block)
            return "\n".join(out)
    return f"% Could not render section: {key}"

# ─────────────────────────────────────────────────────────────
# Section registry
# ─────────────────────────────────────────────────────────────
SECTION_TITLES = {
    "work":         "Experience",
    "education":    "Education",
    "volunteer":    "Volunteer Experience",
    "skills":       "Technical Skills",
    "projects":     "Projects",
    "awards":       "Awards \\& Honours",
    "certificates": "Certificates",
    "publications": "Publications",
    "languages":    "Languages",
    "interests":    "Interests",
    "references":   "References",
}

LIST_WRAP    = {"work", "education", "volunteer", "projects",
                "awards", "certificates", "publications", "references"}
ITEMIZE_WRAP = {"skills", "languages", "interests"}

SECTION_GENERATORS = {
    "work":         gen_work,
    "education":    gen_education,
    "volunteer":    gen_volunteer,
    "skills":       gen_skills,
    "projects":     gen_projects,
    "awards":       gen_awards,
    "certificates": gen_certificates,
    "publications": gen_publications,
    "languages":    gen_languages,
    "interests":    gen_interests,
    "references":   gen_references,
}

# Keys that are structural — not rendered as sections
SKIP_KEYS = {"$schema", "basics", "meta"}

def resolve_title(key: str, data: dict) -> str:
    """Return display title, respecting optional meta.section_titles overrides."""
    custom = (data.get("meta") or {}).get("section_titles") or {}
    return custom.get(key) or SECTION_TITLES.get(key, key.replace("_", " ").title())

def wrap_section(key: str, body: str, title: str) -> str:
    if key in LIST_WRAP or "\\resumeSubheading" in body or "\\resumeProjectHeading" in body:
        return (
            f"\\section{{{title}}}\n"
            f"  \\resumeSubHeadingListStart\n"
            f"{body}\n"
            f"  \\resumeSubHeadingListEnd\n"
        )
    if key in ITEMIZE_WRAP:
        return (
            f"\\section{{{title}}}\n"
            f" \\begin{{itemize}}[leftmargin=0.15in, label={{}}]\n"
            f"    {body}\n"
            f" \\end{{itemize}}\n"
        )
    return f"\\section{{{title}}}\n{body}\n"

# ─────────────────────────────────────────────────────────────
# Master build
# ─────────────────────────────────────────────────────────────
def build(data: dict, input_path: Path):
    version = (data.get("meta") or {}).get("version", "v1.0.0")
    header  = f"% Auto-generated from {input_path.name} {version} — do not edit\n\n"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Basics macros (heading commands)
    print("\n[basics]")
    gen_basics(data, version)

    # 2. All other sections in JSON key order
    section_blocks = []
    for key in [k for k in data if k not in SKIP_KEYS]:
        entries = data[key]
        title   = resolve_title(key, data)
        print(f"\n[{key}]  →  \"{title}\"")

        gen_fn = SECTION_GENERATORS.get(key)
        body   = gen_fn(entries) if gen_fn else gen_custom_section(key, entries)
        if not gen_fn:
            print("      (auto-rendered custom section)")

        w(f"{key}_data.tex", header + body)
        count = len(entries) if isinstance(entries, (list, dict)) else 1
        print(f"      → {count} item(s)")

        section_blocks.append(wrap_section(key, body, title))

    # 3. Master include file — one \input covers all sections
    w("resume_sections.tex", header + "\n".join(section_blocks))
    print(f"\n  [OK] output/resume_sections.tex  ({len(section_blocks)} sections)")

# ─────────────────────────────────────────────────────────────
# pdflatex runner
# ─────────────────────────────────────────────────────────────
def run_pdflatex():
    if not Path("resume.tex").exists():
        warn("resume.tex not found — skipping pdflatex.")
        return
    print("\n  Running pdflatex...")
    r = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "resume.tex"],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        print("  [OK] resume.pdf compiled successfully.")
    else:
        for line in r.stdout.splitlines():
            if line.startswith("!") or "Error" in line:
                print(f"    {line}")

# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(
        description="JSONResume v1.0.0 JSON → LaTeX resume generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 parse_json.py --build            # parse + compile PDF
  python3 parse_json.py --validate         # check JSON only
  python3 parse_json.py --input other.json # use different file
  python3 parse_json.py --watch --build    # auto-rebuild on save
        """
    )
    ap.add_argument("--input",    default=str(DEFAULT_INPUT),
                    help="Path to JSONResume JSON file (default: input/resume.json)")
    ap.add_argument("--build",    action="store_true",
                    help="Run pdflatex after generating .tex files")
    ap.add_argument("--validate", action="store_true",
                    help="Validate JSON only — no output files written")
    ap.add_argument("--watch",    action="store_true",
                    help="Watch for file changes and rebuild automatically")
    args = ap.parse_args()

    ip = Path(args.input)
    if not ip.exists():
        fatal(f"Input file not found: {ip}")

    # ── Watch mode ──────────────────────────────────────────
    if args.watch:
        print(f"Watching {ip} for changes... (Ctrl+C to stop)\n")
        last_mtime = None
        try:
            while True:
                mtime = ip.stat().st_mtime
                if mtime != last_mtime:
                    last_mtime = mtime
                    ts = datetime.now().strftime("%H:%M:%S")
                    print(f"[{ts}] Change detected — rebuilding...")
                    _WARNINGS.clear()
                    data = load_json(ip)
                    validate(data)
                    build(data, ip)
                    if args.build:
                        run_pdflatex()
                    print(f"[{ts}] Done. Watching...\n")
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nWatch mode stopped.")
        return

    # ── Single run ──────────────────────────────────────────
    data = load_json(ip)

    print(f"\nSource  : {ip}")
    print(f"Schema  : JSONResume v1.0.0")
    print(f"Version : {(data.get('meta') or {}).get('version', '?')}")

    print("\n── Validation ──────────────────────────────────────")
    validate(data)
    if _WARNINGS:
        print(f"  {len(_WARNINGS)} warning(s) found.")
    else:
        print("  All checks passed ✓")

    if args.validate:
        return

    print("\n── Generating .tex files ───────────────────────────")
    build(data, ip)

    if args.build:
        run_pdflatex()

    print("\nDone." + ("" if args.build else "  Use --build to also compile the PDF."))


if __name__ == "__main__":
    main()
