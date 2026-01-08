#!/usr/bin/env python3
"""
CV Generator - Generates HTML CV from JSON data.

This script reads a JSON file containing CV data and generates an HTML file
that matches the output of the CV Editor web interface. The generated HTML
is optimized for PDF conversion using WeasyPrint.

Usage:
    python cv_generator.py cv_template.json
    python cv_generator.py cv_template.json -o output.html
    python cv_generator.py cv_template.json --stdout
    python cv_generator.py cv_template.json --validate-only
"""

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any, Optional

# Optional jsonschema support
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


class CVGeneratorError(Exception):
    """Custom exception for CV generation errors."""
    pass


# Default section labels
DEFAULT_LABELS = {
    "profile": "Profile",
    "workRights": "Work Rights",
    "coreSkills": "Core Skills &\nTechnologies",
    "employment": "Employment History",
    "education": "Education",
    "certifications": "Certifications"
}

# Complete CSS template matching cv_editor.html
CSS_TEMPLATE = """/* Reset and Base Styles */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        /* A4 Page Setup - margins controlled via @page for WeasyPrint */
        @page {
            size: A4 portrait;
            margin: 18mm 15mm 15mm 15mm;
        }

        @media print {
            * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }

            html, body {
                width: 100%;
                height: auto;
                background: white !important;
                margin: 0;
                padding: 0;
            }

            body {
                background: none !important;
                font-size: 10pt;
            }

            .cv-container {
                width: 100%;
                max-width: none;
                min-height: auto;
                padding: 0;
                margin: 0;
                background: white !important;
                box-shadow: none !important;
            }

            .job-entry {
                page-break-inside: avoid;
            }

            .cv-section {
                page-break-inside: avoid;
            }

            .section-divider-full {
                page-break-after: avoid;
            }
        }

        /* Base Styles (apply to both screen and print) */
        html {
            font-size: 10pt;
        }

        body {
            font-family: Georgia, "Times New Roman", Times, serif;
            font-size: 10pt;
            line-height: 1.4;
            color: #333;
        }

        .cv-container {
            width: 100%;
            padding: 0;
            margin: 0;
        }

        /* Screen Preview Styles (ignored by WeasyPrint) */
        @media screen {
            body {
                background: #e0e0e0;
            }

            .cv-container {
                width: 210mm;
                min-height: 297mm;
                margin: 20px auto;
                padding: 18mm 15mm 15mm 15mm;
                background: white;
                box-shadow: 0 2px 10px rgba(0,0,0,0.15);
            }
        }

        /* Header Styles */
        .cv-header {
            text-align: center;
            margin-bottom: 10pt;
        }

        .cv-header h1 {
            font-size: 14pt;
            font-weight: normal;
            color: #222;
            margin-bottom: 3pt;
            letter-spacing: 0.3px;
        }

        .cv-header .contact {
            font-size: 9.5pt;
            color: #333;
        }

        /* Section Dividers */
        .section-divider {
            border: none;
            border-top: 0.75pt solid #999;
            margin: 10pt 0;
        }

        .section-divider-full {
            border: none;
            border-top: 0.75pt solid #999;
            margin: 12pt 0 10pt 0;
        }

        /* Two-Column Section Layout */
        .cv-section {
            display: table;
            width: 100%;
            margin-bottom: 8pt;
            table-layout: fixed;
        }

        .section-label {
            display: table-cell;
            width: 140px;
            min-width: 140px;
            max-width: 140px;
            padding-right: 18px;
            font-size: 8pt;
            font-weight: normal;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #444;
            padding-top: 1pt;
            line-height: 1.4;
            vertical-align: top;
        }

        .section-content {
            display: table-cell;
            font-size: 8pt;
            color: #333;
            vertical-align: top;
        }

        .section-content p {
            margin-bottom: 0;
            text-align: left;
            line-height: 1.35;
        }

        /* Links */
        a {
            color: #0066cc;
            text-decoration: underline;
        }

        a:hover {
            text-decoration: none;
        }

        /* Skills Section */
        .skill-group {
            margin-bottom: 10pt;
        }

        .skill-group:last-child {
            margin-bottom: 0;
        }

        .skill-title {
            font-weight: bold;
            font-size: 9pt;
            color: #222;
            margin-bottom: 1pt;
        }

        .skill-description {
            font-size: 8pt;
            color: #333;
            line-height: 1.4;
        }

        /* Employment History Section */
        .employment-section {
            display: block;
        }

        .job-entry {
            display: table;
            width: 100%;
            margin-bottom: 10pt;
            table-layout: fixed;
        }

        .job-entry:last-child {
            margin-bottom: 0;
        }

        .job-date {
            display: table-cell;
            width: 140px;
            min-width: 140px;
            max-width: 140px;
            padding-right: 18px;
            font-size: 8pt;
            color: #333;
            vertical-align: top;
        }

        .job-main {
            display: table-cell;
            vertical-align: top;
        }

        .job-header {
            display: table;
            width: 100%;
            margin-bottom: 4pt;
        }

        .job-title-company {
            display: table-cell;
            font-size: 9pt;
            color: #222;
            text-align: left;
        }

        .job-title {
            font-weight: bold;
        }

        .job-company {
            font-weight: normal;
        }

        .job-location {
            display: table-cell;
            font-size: 9pt;
            color: #333;
            text-align: right;
            white-space: nowrap;
            padding-left: 10px;
        }

        .job-bullets {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .job-bullets li {
            position: relative;
            padding-left: 14px;
            margin-bottom: 0;
            font-size: 8pt;
            text-align: left;
            line-height: 1.4;
        }

        .job-bullets li::before {
            content: "•";
            position: absolute;
            left: 0;
            color: #333;
        }

        /* Education Section */
        .education-entry {
            display: table;
            width: 100%;
            table-layout: fixed;
        }

        .education-year {
            display: table-cell;
            width: 140px;
            min-width: 140px;
            max-width: 140px;
            padding-right: 18px;
            font-size: 8pt;
            color: #333;
            vertical-align: top;
        }

        .education-main {
            display: table-cell;
            vertical-align: top;
        }

        .education-header {
            display: table;
            width: 100%;
            margin-bottom: 2pt;
        }

        .education-institution {
            display: table-cell;
            font-size: 9pt;
            font-weight: bold;
            color: #222;
            text-align: left;
        }

        .education-location {
            display: table-cell;
            font-size: 9pt;
            color: #333;
            text-align: right;
            white-space: nowrap;
            padding-left: 10px;
        }

        .education-degree {
            font-size: 8pt;
            color: #333;
        }

        /* Certifications Section */
        .cert-entry {
            display: table;
            width: 100%;
            margin-bottom: 6pt;
            table-layout: fixed;
        }

        .cert-entry:last-child {
            margin-bottom: 0;
        }

        .cert-date {
            display: table-cell;
            width: 140px;
            min-width: 140px;
            max-width: 140px;
            padding-right: 18px;
            font-size: 8pt;
            color: #333;
            vertical-align: top;
        }

        .cert-name {
            display: table-cell;
            font-size: 8pt;
            color: #333;
            vertical-align: top;
        }

        /* Section Headers for Employment/Education/Certifications */
        .section-header {
            display: table;
            width: 100%;
            margin-bottom: 8pt;
            table-layout: fixed;
        }

        .section-header .section-label {
            display: table-cell;
            width: 140px;
            min-width: 140px;
            max-width: 140px;
            padding-right: 18px;
            padding-top: 0;
            vertical-align: top;
        }"""


def escape_html(text: Optional[str]) -> str:
    """Escape HTML special characters in text."""
    if not text:
        return ""
    return html.escape(str(text))


def format_label(text: Optional[str]) -> str:
    """Escape HTML and convert \\n to <br> for section labels."""
    if not text:
        return ""
    escaped = escape_html(text)
    return escaped.replace("\n", "<br>")


def get_str(data: dict, key: str, default: str = "") -> str:
    """Safely get a string value from dict."""
    value = data.get(key)
    if value is None:
        return default
    return str(value)


def get_list(data: dict, key: str) -> list:
    """Safely get a list value from dict."""
    value = data.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise CVGeneratorError(f"'{key}' must be a list, got {type(value).__name__}")
    return value


def get_label(data: dict, key: str) -> str:
    """Get section label with fallback to default."""
    labels = data.get("sectionLabels", {})
    if not isinstance(labels, dict):
        labels = {}
    return labels.get(key, DEFAULT_LABELS.get(key, key))


def validate_with_schema(data: dict, schema_path: Optional[Path] = None) -> None:
    """Validate CV data against JSON Schema (if jsonschema is available)."""
    if not HAS_JSONSCHEMA:
        return  # Skip schema validation if library not installed

    if schema_path is None:
        # Try to find schema in same directory as script
        script_dir = Path(__file__).parent
        schema_path = script_dir / "cv_schema.json"

    if not schema_path.exists():
        return  # Skip if schema file not found

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        raise CVGeneratorError(f"Schema validation failed: {e.message} (path: {'/'.join(str(p) for p in e.absolute_path)})")
    except Exception:
        pass  # Ignore other schema-related errors, fall back to manual validation


def validate_cv_data(data: Any, schema_path: Optional[Path] = None) -> None:
    """Validate CV data structure."""
    if not isinstance(data, dict):
        raise CVGeneratorError("CV data must be a JSON object (dictionary)")

    # Try schema validation first
    validate_with_schema(data, schema_path)

    # Required fields
    if not get_str(data, "name"):
        raise CVGeneratorError("'name' is required and cannot be empty")
    if not get_str(data, "jobTitle"):
        raise CVGeneratorError("'jobTitle' is required and cannot be empty")

    # Validate skills
    skills = get_list(data, "skills")
    for i, skill in enumerate(skills):
        if not isinstance(skill, dict):
            raise CVGeneratorError(f"skills[{i}] must be an object")
        if not get_str(skill, "title"):
            raise CVGeneratorError(f"skills[{i}].title is required")

    # Validate employment
    employment = get_list(data, "employment")
    for i, job in enumerate(employment):
        if not isinstance(job, dict):
            raise CVGeneratorError(f"employment[{i}] must be an object")
        for field in ["dates", "title", "company", "location"]:
            if not get_str(job, field):
                raise CVGeneratorError(f"employment[{i}].{field} is required")
        duties = job.get("duties")
        if duties is not None and not isinstance(duties, list):
            raise CVGeneratorError(f"employment[{i}].duties must be a list")

    # Validate education
    education = get_list(data, "education")
    for i, edu in enumerate(education):
        if not isinstance(edu, dict):
            raise CVGeneratorError(f"education[{i}] must be an object")
        for field in ["year", "institution", "location", "degree"]:
            if not get_str(edu, field):
                raise CVGeneratorError(f"education[{i}].{field} is required")

    # Validate certifications
    certifications = get_list(data, "certifications")
    for i, cert in enumerate(certifications):
        if not isinstance(cert, dict):
            raise CVGeneratorError(f"certifications[{i}] must be an object")
        if not get_str(cert, "date"):
            raise CVGeneratorError(f"certifications[{i}].date is required")
        if not get_str(cert, "name"):
            raise CVGeneratorError(f"certifications[{i}].name is required")


def generate_header(data: dict) -> str:
    """Generate header section HTML."""
    name = escape_html(get_str(data, "name"))
    job_title = escape_html(get_str(data, "jobTitle"))
    phone = escape_html(get_str(data, "phone"))
    email = escape_html(get_str(data, "email"))
    linkedin_url = get_str(data, "linkedinUrl")

    linkedin_html = ""
    if linkedin_url:
        linkedin_html = f' | <a href="{escape_html(linkedin_url)}" target="_blank">LinkedIn</a>'

    return f"""        <!-- Header -->
        <header class="cv-header">
            <h1>{name}, {job_title}</h1>
            <p class="contact">{phone} | {email}{linkedin_html}</p>
        </header>

        <hr class="section-divider">"""


def generate_profile(data: dict) -> str:
    """Generate profile section HTML."""
    profile = get_str(data, "profile")
    if not profile:
        return ""

    label = format_label(get_label(data, "profile"))

    return f"""
        <!-- Profile -->
        <section class="cv-section">
            <div class="section-label">{label}</div>
            <div class="section-content">
                <p>{escape_html(profile)}</p>
            </div>
        </section>

        <hr class="section-divider">"""


def generate_work_rights(data: dict) -> str:
    """Generate work rights section HTML."""
    work_rights = get_str(data, "workRights")
    if not work_rights:
        return ""

    label = format_label(get_label(data, "workRights"))

    return f"""
        <!-- Work Rights -->
        <section class="cv-section">
            <div class="section-label">{label}</div>
            <div class="section-content">
                <p>{escape_html(work_rights)}</p>
            </div>
        </section>

        <hr class="section-divider">"""


def generate_skills(data: dict) -> str:
    """Generate skills section HTML."""
    skills = get_list(data, "skills")
    if not skills:
        return ""

    label = format_label(get_label(data, "coreSkills"))

    skills_html_parts = []
    for skill in skills:
        title = escape_html(get_str(skill, "title"))
        description = escape_html(get_str(skill, "description"))
        skills_html_parts.append(f"""
                <div class="skill-group">
                    <div class="skill-title">{title}</div>
                    <div class="skill-description">{description}</div>
                </div>""")

    skills_html = "\n".join(skills_html_parts)

    return f"""
        <!-- Core Skills & Technologies -->
        <section class="cv-section">
            <div class="section-label">{label}</div>
            <div class="section-content">{skills_html}
            </div>
        </section>

        <!-- Employment History -->
        <hr class="section-divider">"""


def generate_employment(data: dict) -> str:
    """Generate employment section HTML."""
    employment = get_list(data, "employment")
    if not employment:
        return ""

    label = format_label(get_label(data, "employment"))

    jobs_html_parts = []
    for job in employment:
        dates = escape_html(get_str(job, "dates"))
        title = escape_html(get_str(job, "title"))
        company = escape_html(get_str(job, "company"))
        location = escape_html(get_str(job, "location"))

        duties = job.get("duties", [])
        if not isinstance(duties, list):
            duties = []

        duties_html = "\n".join(
            f"                        <li>{escape_html(duty)}</li>"
            for duty in duties if duty
        )

        jobs_html_parts.append(f"""
            <div class="job-entry">
                <div class="job-date">{dates}</div>
                <div class="job-main">
                    <div class="job-header">
                        <div class="job-title-company">
                            <span class="job-title">{title},</span>
                            <span class="job-company"> {company}</span>
                        </div>
                        <div class="job-location">{location}</div>
                    </div>
                    <ul class="job-bullets">
{duties_html}
                    </ul>
                </div>
            </div>""")

    jobs_html = "\n".join(jobs_html_parts)

    return f"""
        <div class="section-header">
            <div class="section-label">{label}</div>
            <div></div>
        </div>

        <div class="employment-section">{jobs_html}
        </div>

        <!-- Certifications -->
        <hr class="section-divider">"""


def generate_education(data: dict) -> str:
    """Generate education section HTML."""
    education = get_list(data, "education")
    if not education:
        return ""

    label = format_label(get_label(data, "education"))

    edu_html_parts = []
    for edu in education:
        year = escape_html(get_str(edu, "year"))
        institution = escape_html(get_str(edu, "institution"))
        location = escape_html(get_str(edu, "location"))
        degree = escape_html(get_str(edu, "degree"))

        edu_html_parts.append(f"""
        <div class="education-entry">
            <div class="education-year">{year}</div>
            <div class="education-main">
                <div class="education-header">
                    <div class="education-institution">{institution}</div>
                    <div class="education-location">{location}</div>
                </div>
                <div class="education-degree">{degree}</div>
            </div>
        </div>""")

    edu_html = "\n".join(edu_html_parts)

    return f"""
        <div class="section-header">
            <div class="section-label">{label}</div>
            <div></div>
        </div>
{edu_html}"""


def generate_certifications(data: dict) -> str:
    """Generate certifications section HTML."""
    certifications = get_list(data, "certifications")
    if not certifications:
        return ""

    label = format_label(get_label(data, "certifications"))

    certs_html_parts = []
    for cert in certifications:
        date = escape_html(get_str(cert, "date"))
        name = escape_html(get_str(cert, "name"))

        certs_html_parts.append(f"""
        <div class="cert-entry">
            <div class="cert-date">{date}</div>
            <div class="cert-name">{name}</div>
        </div>""")

    certs_html = "\n".join(certs_html_parts)

    return f"""
        <div class="section-header">
            <div class="section-label">{label}</div>
            <div></div>
        </div>
{certs_html}

        <!-- Education -->
        <hr class="section-divider">"""


def generate_cv_html(data: dict) -> str:
    """Generate complete CV HTML document."""
    name = escape_html(get_str(data, "name"))
    job_title = escape_html(get_str(data, "jobTitle"))

    header_html = generate_header(data)
    profile_html = generate_profile(data)
    work_rights_html = generate_work_rights(data)
    skills_html = generate_skills(data)
    employment_html = generate_employment(data)
    education_html = generate_education(data)
    certifications_html = generate_certifications(data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} - {job_title}</title>
    <style>
{CSS_TEMPLATE}
    </style>
</head>
<body>
    <div class="cv-container">
{header_html}
{profile_html}{work_rights_html}{skills_html}{employment_html}{certifications_html}{education_html}
    </div>
</body>
</html>"""


def load_cv_data(filepath: Path) -> dict:
    """Load and parse CV data from JSON file."""
    if not filepath.exists():
        raise CVGeneratorError(f"File not found: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise CVGeneratorError(f"Invalid JSON: {e}")
    except UnicodeDecodeError as e:
        raise CVGeneratorError(f"File encoding error (expected UTF-8): {e}")

    return data


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate HTML CV from JSON data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cv_generator.py cv_template.json
  python cv_generator.py cv_template.json -o my_cv.html
  python cv_generator.py cv_template.json --stdout
  python cv_generator.py cv_template.json --validate-only
        """
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to JSON file containing CV data"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output HTML file path (default: {name}_CV.html)"
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print HTML to stdout instead of writing to file"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate JSON, don't generate HTML"
    )

    args = parser.parse_args()

    try:
        # Load data
        data = load_cv_data(args.input_file)

        # Validate
        validate_cv_data(data)

        if args.validate_only:
            print("Validation successful!", file=sys.stderr)
            return 0

        # Generate HTML
        html_content = generate_cv_html(data)

        if args.stdout:
            print(html_content)
        else:
            # Determine output path
            if args.output:
                output_path = args.output
            else:
                name = get_str(data, "name").replace(" ", "_")
                output_path = Path(f"{name}_CV.html")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            print(f"Generated: {output_path}", file=sys.stderr)

        return 0

    except CVGeneratorError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
