"""
agent.py — BirdEye LinkedIn Outreach Agent

Powered by Claude Opus 4.6 with adaptive thinking.
Takes a LinkedIn Sales Navigator CSV export and produces a prioritized,
personalized outreach queue with drafted messages ready to send.

Usage:
    python agent.py <contacts.csv> [--limit N]

Examples:
    python agent.py sample/contacts.csv
    python agent.py exports/sales_nav_2026-02-18.csv --limit 15
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Windows cmd.exe defaults to cp1252 which can't handle emoji in Claude's
# responses. Reconfigure stdout/stderr to UTF-8 before anything is printed.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from config import BIRDEYE_CONTEXT, ICP_SCORING_GUIDE, MODEL, MAX_TOKENS, DAILY_LIMIT
from tools import TOOL_DEFINITIONS, execute_tool

# legacy_windows=False uses ANSI/VT100 mode (works in VS Code, Windows Terminal,
# and any modern terminal) instead of the old cp1252-limited Windows console API.
console = Console(legacy_windows=False)


# ─── System Prompt ────────────────────────────────────────────────────────────

def build_system_prompt(csv_filepath: str, daily_limit: int) -> str:
    return f"""You are BirdEye's elite LinkedIn outreach agent. Your mission is to
turn a Sales Navigator account list into a laser-targeted, personalized
outreach queue — finding the right person at each company, then drafting
messages a human rep can send in under 60 minutes.

{BIRDEYE_CONTEXT}

{ICP_SCORING_GUIDE}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YOUR WORKFLOW — follow this exactly:

STEP 1 — LOAD THE INPUT FILE
  Call read_companies_csv("{csv_filepath}").
  - If it succeeds → you have a COMPANY LIST. Use the workflow below.
  - If it returns an error saying "use read_contacts_csv" → call
    read_contacts_csv("{csv_filepath}") instead and skip to STEP 2B.

STEP 2A — COMPANY LIST WORKFLOW (up to {daily_limit} companies)

  SEARCH BUDGET: EXACTLY 4 searches per company. No more. Ever.
  Choose carefully — a wasted query is unrecoverable.

  For each company, in order:

  A. FIND THE RIGHT CONTACT (2 searches)
     Goal: find the best ICP-matching person at this company on LinkedIn.
     Run these two queries:
     - '"[Company]" CMO OR "VP Marketing" OR "VP of Marketing" OR "Chief Marketing Officer" site:linkedin.com/in'
     - '"[Company]" "Director of Marketing" OR "Director Digital Marketing" OR "Director Local Marketing" site:linkedin.com/in'

     From the search results:
     → Look for URLs like linkedin.com/in/... — those are individual profiles
     → The result TITLE usually reads "Name – Title – Company | LinkedIn"
     → Extract: full name, title, LinkedIn profile URL
     → Pick the MOST SENIOR ICP title found:
        CMO > VP Marketing > Director of Marketing > Director Digital/Local
     → If no LinkedIn profiles appear, note "contact not found via search"
        and still proceed — use the company name + best-guess title for messages

  B. RESEARCH THE COMPANY (2 searches)
     - "[Company] locations how many 2025 expansion" → location count + growth
     - "[Company] Google reviews reputation news acquisition 2025" → pain points

  C. SCORE ICP FIT (1–10)
     Apply the ICP scoring guide. Score primarily on company fit.
     Downgrade if no strong contact was found (+1 if contact is CMO/VP).
     Write 2–4 sentences of specific reasoning tied to what you found.

  D. CRAFT COMPANY INSIGHTS (2–4 sentences)
     Include: location count, recent news, visible pain/opportunity.
     These feed directly into the message drafts.

  E. DRAFT CONNECTION REQUEST
     - Hard limit: 300 characters (COUNT before saving — trim if over)
     - Reference ONE specific thing from your research
     - Include one clear value hook
     - End with a soft open question
     - Human tone — no sales-speak

  F. DRAFT FIRST MESSAGE (send after connection accepted)
     - 100–175 words
     - Lead with an observation about their business (not BirdEye)
     - Tie the observation to a pain point BirdEye solves
     - One clear, low-friction CTA
     - NEVER start with "I wanted to reach out" or "Hope this finds you"

  G. DRAFT FOLLOW-UP MESSAGE (send 5–7 days later if no reply)
     - 60–90 words
     - Add new value (stat, case study, relevant news) — don't just bump
     - Soft CTA

  H. SAVE THE CONTACT
     Call save_contact_to_queue with the complete JSON.
     Use whatever contact data you found; leave fields empty if not found.

  → Repeat for each company sequentially.

STEP 2B — CONTACTS CSV WORKFLOW (fallback if file has pre-identified people)

  SEARCH BUDGET: EXACTLY 4 searches per contact. No more.

  A. RESEARCH THE COMPANY (3 searches)
     - "[Company] locations how many 2025"
     - "[Company] news acquisition expansion 2024 2025"
     - "[Company] Google reviews reputation complaints"

  B. RESEARCH THE CONTACT (1 search)
     - "[Full Name] [Company] marketing"

  C–H. Same as STEP 2A (score, insights, draft all messages, save).

STEP 3 — GENERATE THE REPORT
  After ALL contacts are saved, call generate_action_report() once.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

QUALITY STANDARDS:
  • Connection requests: count characters yourself. If over 300, trim.
    Never truncate mid-word.
  • If a contact is clearly outside ICP (score < 4), still save with low
    score and a brief note — the human rep makes the final call.
  • Messages must feel like they came from a senior person who actually
    researched the company — not a template.
  • Cite specific facts: location counts, news events, review scores.
  • If search returns no LinkedIn profiles for a company, use your
    knowledge of that company + industry to draft strong messages anyway.
"""


# ─── Agent Runner ─────────────────────────────────────────────────────────────

def run_agent(csv_filepath: str, daily_limit: int = DAILY_LIMIT) -> None:
    client = anthropic.Anthropic()

    # ── Header ────────────────────────────────────────────────────────────
    console.print()
    console.print(Panel.fit(
        Text.assemble(
            ("BirdEye LinkedIn Outreach Agent", "bold blue"),
            "\n",
            ("Powered by Claude Opus 4.6 + Adaptive Thinking", "dim"),
        ),
        border_style="blue",
        padding=(1, 4),
    ))
    console.print(f"  Input:       [yellow]{csv_filepath}[/yellow]")
    console.print(f"  Daily limit: [green]{daily_limit} contacts[/green]")
    console.print(f"  Output dir:  [green]output/[/green]")
    console.print()

    system_prompt = build_system_prompt(csv_filepath, daily_limit)

    messages = [
        {
            "role": "user",
            "content": (
                f"Process the LinkedIn contacts from '{csv_filepath}' and build "
                f"today's outreach queue. Work through up to {daily_limit} contacts. "
                "Be thorough in your research and make every message genuinely "
                "personalized — no generic templates. Begin now."
            ),
        }
    ]

    # Clear today's queue file so a fresh run never duplicates contacts
    # from a prior crashed or partial run.
    date_str_now = datetime.now().strftime("%Y-%m-%d")
    queue_file_today = f"output/queue_{date_str_now}.json"
    if os.path.exists(queue_file_today):
        os.remove(queue_file_today)

    contacts_saved = 0
    searches_done = 0
    MAX_SEARCHES = daily_limit * 4  # 4 searches per contact hard cap
    turn = 0

    # ── Agentic Loop ──────────────────────────────────────────────────────
    while True:
        turn += 1

        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                thinking={"type": "adaptive"},
                system=system_prompt,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )
        except anthropic.RateLimitError:
            console.print("[yellow]Rate limited — waiting 60s...[/yellow]")
            import time; time.sleep(60)
            continue
        except anthropic.APIStatusError as e:
            console.print(f"[red]API error (turn {turn}): {e.status_code} — {e.message}[/red]")
            break

        # Append full response content (preserves thinking blocks if any)
        messages.append({"role": "assistant", "content": response.content})

        # ── Display text output ────────────────────────────────────────
        for block in response.content:
            if block.type == "text" and block.text.strip():
                console.print(f"[dim italic]{block.text.strip()[:300]}[/dim italic]")

        # ── Handle tool calls ─────────────────────────────────────────
        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                name  = block.name
                inp   = block.input

                # Pretty-print what's happening
                if name == "search_web":
                    searches_done += 1
                    budget_note = f"[dim]({searches_done}/{MAX_SEARCHES})[/dim]"
                    if searches_done > MAX_SEARCHES:
                        result = "SEARCH BUDGET EXHAUSTED. Stop searching and draft messages using what you have."
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                        console.print(f"  [red]!! search budget hit — forcing draft phase[/red]")
                        continue
                    console.print(
                        f"  [cyan]>> search[/cyan] {budget_note} [dim]\"{inp.get('query', '')}\"[/dim]"
                    )
                elif name == "read_companies_csv":
                    console.print(
                        f"  [cyan]>> read_companies[/cyan] [dim]{inp.get('filepath', '')}[/dim]"
                    )
                elif name == "read_contacts_csv":
                    console.print(
                        f"  [cyan]>> read_contacts[/cyan] [dim]{inp.get('filepath', '')}[/dim]"
                    )
                elif name == "save_contact_to_queue":
                    contacts_saved += 1
                    try:
                        c = json.loads(inp.get("contact_json", "{}"))
                        score = c.get("icp_score", "?")
                        name_str = c.get("full_name", "Unknown")
                        company_str = c.get("company", "")
                        color = "green" if score >= 8 else "yellow" if score >= 5 else "white"
                        console.print(
                            f"  [bold {color}]+ saved #{contacts_saved}[/bold {color}]"
                            f" [white]{name_str} @ {company_str}[/white]"
                            f" [dim](ICP: {score}/10)[/dim]"
                        )
                    except Exception:
                        console.print(f"  [green]+ saved contact #{contacts_saved}[/green]")
                elif name == "generate_action_report":
                    console.print(Rule("[yellow]Generating Final Report[/yellow]"))

                result = execute_tool(name, inp)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            console.print()
            console.print(Panel.fit(
                Text.assemble(
                    ("Done! Agent completed", "bold green"),
                    f"\n{contacts_saved} contacts processed in {turn} turns",
                ),
                border_style="green",
                padding=(0, 2),
            ))
            break

        else:
            console.print(f"[yellow]Stopped: {response.stop_reason}[/yellow]")
            break

    # ── Final output summary ──────────────────────────────────────────────
    date_str = datetime.now().strftime("%Y-%m-%d")
    console.print()
    console.print("[bold]Output files created:[/bold]")

    files = [
        (f"output/action_report_{date_str}.md",  "Action Report (open this first)"),
        (f"output/crm_import_{date_str}.csv",    "CRM Import CSV (HubSpot/Salesforce)"),
        (f"output/queue_{date_str}.json",         "Raw Queue JSON"),
    ]
    for path, label in files:
        exists = "OK" if os.path.exists(path) else "MISSING"
        color  = "green" if os.path.exists(path) else "red"
        console.print(f"  [{color}]{exists}[/{color}] [yellow]{path}[/yellow] - {label}")

    console.print()


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="BirdEye LinkedIn Outreach Agent — powered by Claude Opus 4.6",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python agent.py sample/contacts.csv\n"
            "  python agent.py exports/leads.csv --limit 10\n\n"
            "The agent will:\n"
            "  1. Research each contact and their company via web search\n"
            "  2. Score ICP fit (1–10)\n"
            "  3. Draft personalized connection request + messages\n"
            "  4. Output a ranked action report (MD) + CRM import CSV"
        ),
    )
    parser.add_argument("csv_file", help="Path to Sales Navigator CSV export")
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=DAILY_LIMIT,
        metavar="N",
        help=f"Max contacts to process (default: {DAILY_LIMIT})",
    )

    args = parser.parse_args()

    if not os.path.exists(args.csv_file):
        console.print(f"[red]Error: File not found: {args.csv_file}[/red]")
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print(
            "[red]Error: ANTHROPIC_API_KEY environment variable not set.[/red]\n"
            "Run: [yellow]set ANTHROPIC_API_KEY=your-key-here[/yellow] (Windows)\n"
            "  or [yellow]export ANTHROPIC_API_KEY=your-key-here[/yellow] (Mac/Linux)"
        )
        sys.exit(1)

    run_agent(args.csv_file, args.limit)


if __name__ == "__main__":
    main()
