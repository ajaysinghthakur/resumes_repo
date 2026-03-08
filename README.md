
# 📄 LaTeX Resume Generator

A data-driven resume builder using **JSONResume v1.0.0** as the single source of truth.  
Edit one JSON file → generate LaTeX includes → compile a clean, ATS-friendly PDF.

---

## 🗂️ Project Structure

```
project/
├── .vscode
    ├── settings.json # Latex buid setting
├── parse_json.py          # Generator: resume.json → .tex data files + PDF
├── resume.tex             # LaTeX template (edit for layout only, never for content)
│
├── input/
│   └── resume.json        # ✏️  Single source of truth — edit this
│
├── build/
│   ├── * # ignore all letex build file
│   └── resume.pdf # Generated resume in PDF format
└── output/                # ⚙️  Auto-generated — do not edit by hand
    ├── basics_data.tex         \newcommand macros for the heading
    ├── work_data.tex
    ├── education_data.tex
    ├── projects_data.tex
    ├── skills_data.tex
    ├── certificates_data.tex
    ├── awards_data.tex
    ├── publications_data.tex
    ├── volunteer_data.tex
    ├── languages_data.tex
    ├── interests_data.tex
    ├── references_data.tex
    └── resume_sections.tex     master \input — all sections in JSON key order
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.7+** (stdlib only — no extra packages needed)
- **LaTeX** — [MacTeX
](https://www.tug.org/mactex/) (macOS) or Its alternative for window and linux will also work
- **vscode** — IDE, this is what i used

### Build in one command

```bash
python3 parse_json.py
```

This parses `input/resume.json`, writes all `output/*.tex` files, and runs `pdflatex` automatically.

Or step by step:

```bash
# 1. Edit your resume data, in your favorite editor
input/resume.json

# 2. Generate LaTeX include files
python3 parse_json.py

# 3. Compile the PDF
pdflatex resume.tex
```

---

## 🖥️ CLI Reference

```
python3 parse_json.py [options]

Options:
  --build            Parse + run pdflatex automatically
  --validate         Validate JSON only — no files written
  --watch            Watch input/resume.json and rebuild on every save
  --watch --build    Watch mode + auto-compile PDF on each change
  --input PATH       Use a different JSON file (e.g. for job-specific versions)
```

### Examples

```bash
# Validate your JSON against JSONResume rules
python3 parse_json.py --validate

# Full build
python3 parse_json.py --build

# Use a tailored version for a specific application
python3 parse_json.py --input input/resume_faang.json --build

# Auto-rebuild while editing
python3 parse_json.py --watch --build
```

---

## 📝 `resume.json` Format — JSONResume v1.0.0

`resume.json` follows the [official JSONResume schema](https://jsonresume.org/schema).  
**All fields are optional** except `basics.name` and `basics.email`.  
Section order in the JSON controls section order in the PDF.

### `$schema` + `meta`

```json
{
  "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/master/schema.json",
  "meta": {
    "version": "v1.0.0",
    "lastModified": "2025-03-07",
    "canonical": ""
  }
}
```

---

### `basics` — Personal Info

```json
"basics": {
  "name": "Ajay Singh Thakur",
  "label": "Software Engineer",
  "image": "",
  "email": "hello@world.com",
  "phone": "000-123-123",
  "url": "exmaple.com",
  "summary": "Software engineer with 7+ years building distributed systems.",
  "location": {
    "city": "Pune",
    "region": "Maharashtra",
    "countryCode": "IN",
    "postalCode": "411057"
  },
  "profiles": [
    { "network": "LinkedIn", "username": "ajaythakur", "url": "https://linkedin.com/in/" },
    { "network": "GitHub",   "username": "ajaythakur", "url": "https://github.com/" }
  ]
}
```

> Add any extra profile by appending to the `profiles` array — no parser changes needed.  
> Set `"image"` to a local path or URL to show a photo in the heading.

---

### `work` — Experience

```json
"work": [
  {
    "name": "FAANG LLC",
    "position": "Senior Software Engineer",
    "url": "https://google.com",
    "location": "Mountain View, CA",
    "startDate": "2021-01-01",
    "endDate": "",
    "summary": "Optional role overview.",
    "highlights": [
      "Built microservices handling 10M+ requests/day",
      "Reduced latency by 40% with Redis caching"
    ]
  }
]
```

> `"endDate": ""` means **Present**.  
> Dates use ISO format: `YYYY-MM-DD`, `YYYY-MM`, or `YYYY`.

---

### `education`

```json
"education": [
  {
    "institution": "IVY League",
    "url": "https://ivyleague University",
    "area": "Computer Science, Minor in Business",
    "studyType": "Bachelor of Arts",
    "startDate": "2018-08-01",
    "endDate": "2021-05-01",
    "score": "3.8 / 4.0",
    "courses": ["Data Structures and Algorithms", "Distributed Systems"]
  }
]
```

> `area` + `studyType` combine as `"Bachelor of Arts in Computer Science"` in the PDF.  
> `score` renders as GPA. `courses` render as sub-bullets. Both are optional.

---

### `skills`

```json
"skills": [
  { "name": "Python",     "level": "Master",       "keywords": ["FastAPI", "Flask", "NumPy"] },
  { "name": "JavaScript", "level": "Advanced",     "keywords": ["React", "Node.js"] },
  { "name": "DevOps",     "level": "Intermediate", "keywords": ["Docker", "Kubernetes"] }
]
```

> `level` values: `Beginner` | `Intermediate` | `Advanced` | `Master`  
> Renders as: **Python**: *Master* — FastAPI, Flask, NumPy

---

### `projects`

```json
"projects": [
  {
    "name": "Gitlytics",
    "url": "https://github.com/jake/gitlytics",
    "startDate": "2020-06-01",
    "endDate": "",
    "keywords": ["Python", "Flask", "React", "PostgreSQL"],
    "highlights": [
      "Full-stack web app with Flask REST API and React frontend",
      "Implemented GitHub OAuth and repository data visualization"
    ]
  }
]
```

---

### `certificates`

```json
"certificates": [
  {
    "name": "AWS Certified Solutions Architect",
    "date": "2023-03-15",
    "issuer": "Amazon Web Services",
    "url": "https://aws.amazon.com/certification"
  }
]
```

> The JSONResume standard key is **`certificates`** — not `certifications`.

---

### `awards`, `publications`, `volunteer`, `languages`, `interests`, `references`

All follow the JSONResume standard schema. Example:

```json
"awards": [
  { "title": "Best Paper Award", "date": "2022-11-01", "awarder": "IEEE Conference on AI", "summary": "..." }
],
"languages": [
  { "language": "English", "fluency": "Native speaker" },
  { "language": "Spanish", "fluency": "Professional working proficiency" }
],
"volunteer": [
  {
    "organization": "Apache Foundation",
    "position": "Open Source Maintainer",
    "startDate": "2020-01-01",
    "endDate": "",
    "highlights": ["Triaged 200+ issues", "Wrote onboarding documentation"]
  }
],
"references": [
  { "name": "Dr. Jane Smith", "reference": "Available upon request" }
]
```

---

### Custom Sections

Any top-level JSON key not in the standard schema is **auto-detected** and rendered automatically:

```json
"patents": [
  {
    "title": "Procedural Content Generation System",
    "number": "US1234567",
    "date": "2023-06-01",
    "highlights": ["Awarded for novel dungeon generation algorithm"]
  }
]
```

The parser uses the first four fields as the two-column subheading and renders `highlights` as bullets beneath it.

---

## ⚙️ How It Works

```
input/resume.json
       │
       ▼
 parse_json.py
       │
       ├──▶  output/basics_data.tex       (\newcommand macros for heading)
       ├──▶  output/work_data.tex
       ├──▶  output/education_data.tex
       ├──▶  output/skills_data.tex
       ├──▶  output/projects_data.tex
       ├──▶  output/certificates_data.tex
       ├──▶  output/<section>_data.tex    (one per JSON key, auto-created)
       └──▶  output/resume_sections.tex   (master include, sections in JSON order)
                      │
                      ▼
              resume.tex  ──▶  pdflatex  ──▶  resume.pdf
```

`resume.tex` loads `output/basics_data` for heading macros (`\resumeName`, `\resumeEmail`, etc.) and `output/resume_sections` for the complete body — one `\input` line covers every section regardless of how many exist.

---
## 📄 License

LaTeX template based on **Jake's Resume** by [Jake Gutierrez](https://github.com/jakegut) — MIT License.  
`parse_json.py` and project structure are free to use and modify.
