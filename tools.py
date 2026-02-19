# tools.py — Tool implementations for the BirdEye outreach agent

import contextlib
import csv
import io
import json
import os
import time
import warnings
from datetime import datetime
from typing import Any

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from duckduckgo_search import DDGS


@contextlib.contextmanager
def _quiet():
    """Suppress stderr and Python warnings (used to silence duckduckgo_search rename notice)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        devnull = open(os.devnull, "w")
        old_stderr_fd = os.dup(2)
        try:
            os.dup2(devnull.fileno(), 2)
            yield
        finally:
            os.dup2(old_stderr_fd, 2)
            os.close(old_stderr_fd)
            devnull.close()


# ─── Tool: Web Search ─────────────────────────────────────────────────────────

def search_web(query: str, max_results: int = 3) -> str:
    """
    Search the web using DuckDuckGo. Used to research companies and contacts.
    Returns formatted search results with titles, URLs, and snippets.
    Capped at 3 results and 400 chars per snippet to keep context lean.
    """
    SNIPPET_MAX = 400

    def _format(results: list) -> str:
        parts = []
        for r in results:
            snippet = (r.get("body", "") or "")[:SNIPPET_MAX]
            parts.append(
                f"TITLE: {r.get('title', 'N/A')}\n"
                f"URL:   {r.get('href', 'N/A')}\n"
                f"TEXT:  {snippet}"
            )
        return "\n\n---\n\n".join(parts)

    try:
        time.sleep(0.5)  # Be polite to DDG, avoid rate limiting
        with _quiet():
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"No results found for query: {query}"

        return _format(results)

    except Exception as e:
        # Retry once on failure
        try:
            time.sleep(2)
            with _quiet():
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_results))
            if results:
                return _format(results)
        except Exception:
            pass
        return f"Search error (query: '{query}'): {str(e)}"


# ─── Tool: Read Account/Company List CSV ─────────────────────────────────────

def read_companies_csv(filepath: str) -> str:
    """
    Parse a LinkedIn Sales Navigator account list / company match CSV.
    Handles the standard Sales Navigator export format with Match Status.
    Returns a JSON array of matched companies ready for contact discovery.
    """
    if not os.path.exists(filepath):
        return f"ERROR: File not found: {filepath}"

    try:
        companies = []
        skipped_failed = 0
        skipped_empty = 0

        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            # Detect if this is actually a contacts CSV (wrong tool)
            if any(h in headers for h in ["First Name", "FirstName", "LinkedIn Profile URL"]):
                return (
                    "ERROR: This looks like a contacts CSV, not a company list. "
                    "Use read_contacts_csv instead."
                )

            for row in reader:
                status = (row.get("Match Status", "") or "").strip().upper()

                # Get the best company name available
                company_name = (
                    row.get("Matched Company Name", "").strip()
                    or row.get("Account Name", "").strip()
                )

                if not company_name:
                    skipped_empty += 1
                    continue

                # Skip companies that failed to match in Sales Navigator
                if status == "FAILED":
                    skipped_failed += 1
                    continue

                # Parse match score safely
                try:
                    match_score = float(row.get("Match Score (0-5/Highest)", "0") or "0")
                except ValueError:
                    match_score = 0.0

                companies.append({
                    "company_name":     company_name,
                    "original_name":    row.get("Account Name", "").strip(),
                    "company_linkedin": row.get("Matched Company Linkedin Url", "").strip(),
                    "company_website":  row.get("Matched Company Url", "").strip(),
                    "sales_nav_url":    row.get("Matched Company Sales Nav Url", "").strip(),
                    "match_score":      match_score,
                })

        if not companies:
            return (
                f"ERROR: No matched companies found. "
                f"Skipped {skipped_failed} failed matches and {skipped_empty} empty rows. "
                "Verify this is a Sales Navigator account list export."
            )

        # Sort by match score descending
        companies.sort(key=lambda x: -x["match_score"])

        summary = (
            f"Loaded {len(companies)} matched companies from '{filepath}' "
            f"(skipped {skipped_failed} failed + {skipped_empty} empty rows).\n\n"
        )
        return summary + json.dumps(companies, indent=2)

    except Exception as e:
        return f"ERROR reading CSV '{filepath}': {str(e)}"


# ─── Tool: Read Sales Navigator Contacts CSV ──────────────────────────────────

# Common field name mappings from Sales Navigator exports
_FIELD_MAP = {
    "first_name":    ["First Name", "FirstName", "first_name"],
    "last_name":     ["Last Name", "LastName", "last_name"],
    "title":         ["Title", "Job Title", "Position", "Current Position"],
    "company":       ["Company", "Account Name", "Company Name", "Organization"],
    "linkedin_url":  ["LinkedIn Profile URL", "Profile URL", "LinkedIn URL",
                      "LinkedIn", "Contact LinkedIn URL"],
    "location":      ["Location", "Geography", "City", "Region"],
    "industry":      ["Industry", "Account Industry", "Vertical"],
    "company_size":  ["Company Headcount", "# Employees", "Company Size",
                      "Employees", "Headcount"],
    "email":         ["Email Address", "Email", "Work Email"],
    "phone":         ["Phone", "Mobile Phone", "Direct Phone"],
    "account_url":   ["Account LinkedIn URL", "Company LinkedIn URL"],
}


def _get_field(row: dict, field: str) -> str:
    """Try multiple possible column names for a given logical field."""
    for col in _FIELD_MAP.get(field, [field]):
        val = row.get(col, "").strip()
        if val:
            return val
    return ""


def read_contacts_csv(filepath: str) -> str:
    """
    Parse a LinkedIn Sales Navigator CSV export.
    Handles multiple export formats and normalizes field names.
    Returns a JSON array of contact objects.
    """
    if not os.path.exists(filepath):
        return f"ERROR: File not found: {filepath}"

    try:
        contacts = []
        skipped = 0

        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                first = _get_field(row, "first_name")
                last  = _get_field(row, "last_name")
                comp  = _get_field(row, "company")

                # Skip rows with insufficient data
                if not (first and comp):
                    skipped += 1
                    continue

                contacts.append({
                    "first_name":   first,
                    "last_name":    last,
                    "full_name":    f"{first} {last}".strip(),
                    "title":        _get_field(row, "title"),
                    "company":      comp,
                    "linkedin_url": _get_field(row, "linkedin_url"),
                    "location":     _get_field(row, "location"),
                    "industry":     _get_field(row, "industry"),
                    "company_size": _get_field(row, "company_size"),
                    "email":        _get_field(row, "email"),
                    "phone":        _get_field(row, "phone"),
                    "account_url":  _get_field(row, "account_url"),
                })

        if not contacts:
            return (
                "ERROR: No valid contacts found in CSV. "
                "Check that the file has 'First Name' and 'Company' columns "
                f"(skipped {skipped} rows due to missing data)."
            )

        summary = (
            f"Loaded {len(contacts)} contacts from '{filepath}' "
            f"(skipped {skipped} incomplete rows).\n\n"
        )
        return summary + json.dumps(contacts, indent=2)

    except Exception as e:
        return f"ERROR reading CSV '{filepath}': {str(e)}"


# ─── Tool: Save Contact to Queue ─────────────────────────────────────────────

def save_contact_to_queue(contact_json: str) -> str:
    """
    Save a fully researched and drafted contact to today's output queue.
    Keeps the queue sorted by ICP score descending.
    """
    try:
        contact: dict = json.loads(contact_json)
    except json.JSONDecodeError as e:
        return f"ERROR: Invalid JSON passed to save_contact_to_queue: {e}"

    required = ["full_name", "connection_request", "first_message", "icp_score"]
    missing = [f for f in required if not contact.get(f)]
    if missing:
        return f"ERROR: Missing required fields: {missing}. Contact NOT saved."

    # Enforce the 300-char LinkedIn connection request limit
    conn_req = contact.get("connection_request", "")
    if len(conn_req) > 300:
        contact["connection_request"] = conn_req[:297] + "..."
        contact["connection_request_truncated"] = True

    os.makedirs("output", exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    queue_file = f"output/queue_{date_str}.json"

    # Load existing queue
    queue: list[dict] = []
    if os.path.exists(queue_file):
        try:
            with open(queue_file, "r") as f:
                queue = json.load(f)
        except Exception:
            queue = []

    contact["saved_at"] = datetime.now().isoformat()
    queue.append(contact)

    # Sort by ICP score descending, then by company name
    queue.sort(key=lambda x: (-(x.get("icp_score", 0)), x.get("company", "")))

    with open(queue_file, "w") as f:
        json.dump(queue, f, indent=2)

    score = contact.get("icp_score", "?")
    name  = contact.get("full_name", "Unknown")
    company = contact.get("company", "Unknown")
    return (
        f"✓ Saved: {name} @ {company} (ICP: {score}/10) — "
        f"Queue now has {len(queue)} contacts."
    )


# ─── Tool: Generate Action Report ────────────────────────────────────────────

def generate_action_report() -> str:
    """
    Generate a human-readable Markdown action report and a CRM-importable CSV
    from today's processed queue. Called once at the end of the agent run.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    queue_file = f"output/queue_{date_str}.json"

    if not os.path.exists(queue_file):
        return "No queue found for today — have you saved any contacts yet?"

    try:
        with open(queue_file, "r") as f:
            queue: list[dict] = json.load(f)
    except Exception as e:
        return f"ERROR reading queue: {e}"

    if not queue:
        return "Queue is empty."

    high_count   = sum(1 for c in queue if c.get("icp_score", 0) >= 8)
    medium_count = sum(1 for c in queue if 5 <= c.get("icp_score", 0) < 8)

    # ── Markdown Report ────────────────────────────────────────────────────
    lines = [
        "# BirdEye LinkedIn Outreach Queue",
        f"**Date:** {date_str}  ",
        f"**Total Contacts:** {len(queue)} — "
        f"🔴 High Priority: {high_count} | 🟡 Medium: {medium_count}",
        "",
        "> **Instructions:** Work through this list top-to-bottom. "
        "Open each LinkedIn profile, send the connection request, then "
        "move on. Send first messages only after connections are accepted "
        "(usually 24-48h). Check boxes as you go.",
        "",
        "---",
        "",
    ]

    for i, contact in enumerate(queue, 1):
        score = contact.get("icp_score", 0)
        if score >= 8:
            priority_label = "🔴 HIGH PRIORITY"
        elif score >= 5:
            priority_label = "🟡 MEDIUM PRIORITY"
        else:
            priority_label = "🟢 STANDARD"

        name    = contact.get("full_name", "N/A")
        title   = contact.get("title", "N/A")
        company = contact.get("company", "N/A")
        linkedin = contact.get("linkedin_url", "N/A")
        location = contact.get("location", "N/A")
        industry = contact.get("industry", "N/A")

        conn_req   = contact.get("connection_request", "N/A")
        first_msg  = contact.get("first_message", "N/A")
        follow_up  = contact.get("follow_up_message", "")
        reasoning  = contact.get("icp_reasoning", "N/A")
        insights   = contact.get("company_insights", "N/A")

        char_count = len(conn_req)
        char_note  = f" ⚠️ {char_count} chars — OVER LIMIT" if char_count > 300 else f" ({char_count}/300 chars)"

        lines += [
            f"## #{i} [{priority_label}] {name}",
            f"**{title}** @ **{company}**  ",
            f"📍 {location} | 🏭 {industry} | ICP Score: **{score}/10**  ",
            f"🔗 [LinkedIn Profile]({linkedin})",
            "",
            f"**Why They're a Fit:**  ",
            f"{reasoning}",
            "",
            f"**Company Research Highlights:**  ",
            f"{insights}",
            "",
            f"### CONNECTION REQUEST{char_note}",
            "```",
            conn_req,
            "```",
            "",
            "### FIRST MESSAGE *(send after connection accepted)*",
            "```",
            first_msg,
            "```",
        ]

        if follow_up:
            lines += [
                "",
                "### FOLLOW-UP *(if no reply after 5–7 days)*",
                "```",
                follow_up,
                "```",
            ]

        lines += [
            "",
            "**Action Checklist:**",
            "- [ ] Connection request sent",
            "- [ ] First message sent (after acceptance)",
            "- [ ] Contact added to CRM",
            "- [ ] Follow-up scheduled",
            "",
            "---",
            "",
        ]

    report_md = "\n".join(lines)
    report_file = f"output/action_report_{date_str}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_md)

    # ── CRM Export CSV (HubSpot / Salesforce compatible) ──────────────────
    crm_file = f"output/crm_import_{date_str}.csv"
    crm_fields = [
        "First Name", "Last Name", "Job Title", "Company", "LinkedIn URL",
        "Email", "Phone", "Location", "Industry", "ICP Score",
        "Connection Request", "First Message", "Follow Up",
        "ICP Reasoning", "Company Insights", "Source"
    ]

    with open(crm_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=crm_fields)
        writer.writeheader()
        for c in queue:
            writer.writerow({
                "First Name":        c.get("first_name", ""),
                "Last Name":         c.get("last_name", ""),
                "Job Title":         c.get("title", ""),
                "Company":           c.get("company", ""),
                "LinkedIn URL":      c.get("linkedin_url", ""),
                "Email":             c.get("email", ""),
                "Phone":             c.get("phone", ""),
                "Location":          c.get("location", ""),
                "Industry":          c.get("industry", ""),
                "ICP Score":         c.get("icp_score", ""),
                "Connection Request": c.get("connection_request", ""),
                "First Message":     c.get("first_message", ""),
                "Follow Up":         c.get("follow_up_message", ""),
                "ICP Reasoning":     c.get("icp_reasoning", ""),
                "Company Insights":  c.get("company_insights", ""),
                "Source":            "LinkedIn Sales Navigator",
            })

    return (
        f"Reports generated successfully!\n\n"
        f"📋 Action Report:  output/action_report_{date_str}.md\n"
        f"📊 CRM Import CSV: output/crm_import_{date_str}.csv\n"
        f"💾 Raw Queue JSON: output/queue_{date_str}.json\n\n"
        f"Totals: {len(queue)} contacts — "
        f"{high_count} high priority, {medium_count} medium priority\n\n"
        f"--- REPORT PREVIEW (first 2000 chars) ---\n\n"
        + report_md[:2000]
    )


# ─── Tool Registry (for agent.py) ────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "search_web",
        "description": (
            "Search the web using DuckDuckGo. Use for: (1) finding ICP contacts "
            "at a company via LinkedIn — query like '[Company] VP Marketing linkedin.com/in', "
            "(2) researching companies (news, locations, reviews, acquisitions), "
            "(3) researching specific contacts (background, focus areas). "
            "Inspect result URLs and titles carefully to extract names and LinkedIn URLs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Specific search query. Examples: "
                        "'\"Aspen Dental\" CMO OR \"VP Marketing\" OR \"Director Marketing\" linkedin.com/in', "
                        "'Aspen Dental locations 2025 expansion', "
                        "'Greystar apartments Google reviews reputation 2025'"
                    ),
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_companies_csv",
        "description": (
            "Read a LinkedIn Sales Navigator account list / company match CSV. "
            "Use this when the input file is a list of TARGET COMPANIES "
            "(has columns like 'Account Name', 'Match Status', 'Matched Company Linkedin Url'). "
            "Call this FIRST before processing any companies."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the company list CSV file",
                }
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "read_contacts_csv",
        "description": (
            "Read a LinkedIn Sales Navigator CONTACTS export CSV. "
            "Use this only when the input file already has individual people "
            "(has columns like 'First Name', 'Last Name', 'LinkedIn Profile URL'). "
            "If the file has company/account data instead, use read_companies_csv."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the contacts CSV file",
                }
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "save_contact_to_queue",
        "description": (
            "Save a fully researched and drafted contact to today's outreach queue. "
            "ONLY call this after you have: researched the company, researched the "
            "contact, scored ICP fit, and drafted all messages. "
            "The connection_request MUST be under 300 characters."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_json": {
                    "type": "string",
                    "description": (
                        "JSON string with ALL of the following fields:\n"
                        "{\n"
                        '  "first_name": "Jane",\n'
                        '  "last_name": "Smith",\n'
                        '  "full_name": "Jane Smith",\n'
                        '  "title": "VP of Marketing",\n'
                        '  "company": "Aspen Dental",\n'
                        '  "linkedin_url": "https://linkedin.com/in/...",\n'
                        '  "location": "Chicago, IL",\n'
                        '  "industry": "Healthcare",\n'
                        '  "company_size": "1000-5000",\n'
                        '  "email": "jane@aspendental.com",\n'
                        '  "phone": "",\n'
                        '  "icp_score": 9,\n'
                        '  "icp_reasoning": "Multi-location DSO with 900+ practices. '
                        'VP Marketing owns reputation strategy. Clear pain: their Google '
                        'star ratings vary 3.2–4.8 across locations. Recently hired new '
                        'CMO — leadership change is a buying signal.",\n'
                        '  "company_insights": "900+ dental practices across 44 states. '
                        'Backed by Leonard Green. Q1 2026: acquired SmileCare network '
                        '(120 practices). CEO interview mentions patient experience as '
                        'top strategic priority. Average Google rating: 4.1.",\n'
                        '  "connection_request": "Hi Jane, Aspen just added 120 practices '
                        'via SmileCare — managing patient reviews at 900+ sites is a real '
                        'coordination challenge. I help DSOs solve exactly that. Worth '
                        'connecting?",\n'
                        '  "first_message": "Hi Jane, thanks for connecting! ...",\n'
                        '  "follow_up_message": "Hi Jane, just wanted to resurface this..."\n'
                        "}"
                    ),
                }
            },
            "required": ["contact_json"],
        },
    },
    {
        "name": "generate_action_report",
        "description": (
            "Generate the final Markdown action report and CRM-importable CSV "
            "from today's queue. Call this ONCE at the very end, after all "
            "contacts have been saved."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


def execute_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Dispatch a tool call to its implementation."""
    if tool_name == "search_web":
        return search_web(tool_input["query"])
    elif tool_name == "read_companies_csv":
        return read_companies_csv(tool_input["filepath"])
    elif tool_name == "read_contacts_csv":
        return read_contacts_csv(tool_input["filepath"])
    elif tool_name == "save_contact_to_queue":
        return save_contact_to_queue(tool_input["contact_json"])
    elif tool_name == "generate_action_report":
        return generate_action_report()
    else:
        return f"ERROR: Unknown tool '{tool_name}'"
