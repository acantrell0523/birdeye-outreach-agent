"""
agent.py — BirdEye LinkedIn Outreach Agent

Powered by Claude Opus 4.6 with adaptive thinking.
Takes a LinkedIn Sales Navigator CSV export and produces a prioritized
outreach queue with drafted messages ready to send.

Usage:
    python agent.py <accounts.csv>
    python agent.py <accounts.csv> --limit 10   # test with a subset first

Examples:
    python agent.py "C:\\Users\\You\\Downloads\\my_accounts.csv"
    python agent.py sample/contacts.csv --limit 5
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
    limit_note = "ALL companies in the file" if daily_limit == 0 else f"up to {daily_limit} companies"
    return f"""You are BirdEye's LinkedIn outreach agent. Your job is to take a
Sales Navigator account list, find the right marketing contact at each
company, research them, and write messages that actually get replies.

{BIRDEYE_CONTEXT}

{ICP_SCORING_GUIDE}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YOUR WORKFLOW — follow this exactly:

STEP 1 — LOAD THE INPUT FILE
  Call read_companies_csv("{csv_filepath}").
  - If it succeeds → you have a COMPANY LIST. Use the workflow below.
  - If it returns an error saying "use read_contacts_csv" → call
    read_contacts_csv("{csv_filepath}") instead and skip to STEP 2B.

STEP 2A — COMPANY LIST WORKFLOW ({limit_note})

  SEARCH BUDGET: EXACTLY 4 searches per company. No more. Ever.
  Pick your queries carefully.

  For each company, in order:

  A. FIND THE RIGHT CONTACT (2 searches)
     Goal: find the best ICP-matching person at this company on LinkedIn.
     Run these two queries:
     - '"[Company]" CMO OR "VP Marketing" OR "VP of Marketing" OR "Chief Marketing Officer" site:linkedin.com/in'
     - '"[Company]" "Director of Marketing" OR "Director Digital Marketing" OR "Director Local Marketing" site:linkedin.com/in'

     From the search results:
     → Look for URLs like linkedin.com/in/... — those are individual profiles
     → The result TITLE usually reads "Name - Title - Company | LinkedIn"
     → Extract: full name, title, LinkedIn profile URL
     → Pick the MOST SENIOR ICP title found:
        CMO > VP Marketing > Director of Marketing > Director Digital/Local
     → If no LinkedIn profiles appear, note "contact not found via search"
        and still proceed — use the company name + best-guess title for messages

  B. RESEARCH THE COMPANY (2 searches)
     - "[Company] locations how many 2025 expansion" → location count + growth
     - "[Company] Google reviews reputation news acquisition 2025" → pain points

  C. SCORE ICP FIT (1-10)
     Apply the ICP scoring guide. Score primarily on company fit.
     Downgrade if no strong contact was found (+1 if contact is CMO/VP).
     Write 2-3 sentences of specific reasoning tied to what you found.

  D. CRAFT COMPANY INSIGHTS (2-3 sentences)
     Include: location count, recent news, visible pain/opportunity.
     These feed directly into the message drafts.

  E. DRAFT CONNECTION REQUEST
     - Hard limit: 300 characters (COUNT before saving, trim if over)
     - Casual and direct — like messaging someone you met at an event
     - Reference ONE real thing from research (location count, industry, news)
     - End with a simple, low-pressure question
     - NO em dashes (—) anywhere
     - NO corporate language, no over-personalization

     Good example:
       "Hey [Name], noticed you're running marketing for [Company] — a big
       multi-location operation. We work with a lot of [industry] brands on
       the reviews/reputation side. Worth connecting?"

     Wait, that example has an em dash. Here is the correct version:
       "Hey [Name], noticed you're handling marketing for [Company]. We work
       with a lot of [industry] brands on the reviews/reputation side and it
       looked relevant. Worth connecting?"

  F. DRAFT FIRST MESSAGE (send after connection accepted)
     - 80-140 words
     - Open with a genuine question about their situation, not a statement
       about how impressive their company is
     - Tie the question naturally to something BirdEye solves
     - One simple ask at the end (15-minute call, quick question, etc.)
     - NO em dashes (—) anywhere
     - NO filler phrases like "given your experience" or "as someone in your role"
     - Short sentences. Conversational.

     Good example opening:
       "Hey [Name], thanks for connecting. Quick question for you: what does your
       current process look like for managing Google reviews across all your
       [Company] locations? Asking because that tends to be the biggest headache
       for groups your size and we work on exactly that."

  G. DRAFT FOLLOW-UP MESSAGE (send 5-7 days later if no reply)
     - 40-70 words
     - Add one new piece of value (a stat, something relevant in their industry)
     - Do NOT just say "following up" with nothing new
     - Soft ask
     - NO em dashes (—) anywhere

     Good example:
       "Hey [Name], wanted to share something relevant — [relevant stat or news].
       Thought it might be useful given what you're managing at [Company].
       Still happy to chat if the timing works."

     Wait, that has an em dash. Correct version:
       "Hey [Name], wanted to share something relevant. [Relevant stat or news].
       Thought it might be useful given what you're managing at [Company].
       Still happy to chat if the timing works."

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

  C-H. Same as STEP 2A (score, insights, draft all messages, save).

STEP 3 — GENERATE THE REPORT
  After ALL contacts are saved, call generate_action_report() once.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

QUALITY STANDARDS:
  • Connection requests: count characters. If over 300, trim. Never cut mid-word.
  • ZERO em dashes (—) in any message. Use a period or nothing instead.
  • Messages should read like a real person typed them, not a sales template.
  • Reference specific facts (location counts, news, industry) but keep it light.
    One data point is enough. Don't stuff the message with research.
  • If search returns no LinkedIn profiles, use your knowledge of the company
    and industry to draft strong messages anyway.
  • If a contact is outside ICP (score < 4), still save with low score and a
    brief note. The human makes the final call on who to send.
"""


# ─── Agent Runner ─────────────────────────────────────────────────────────────

def run_agent(csv_filepath: str, daily_limit: int = DAILY_LIMIT) -> None:
    client = anthropic.Anthropic()

    unlimited = (daily_limit == 0)
    limit_display = "All companies" if unlimited else f"{daily_limit} companies max"

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
    console.print(f"  Input:    [yellow]{csv_filepath}[/yellow]")
    console.print(f"  Mode:     [green]{limit_display}[/green]")
    console.print(f"  Output:   [green]output/[/green]")
    console.print()

    system_prompt = build_system_prompt(csv_filepath, daily_limit)

    limit_instruction = (
        "Process ALL companies in the file."
        if unlimited
        else f"Work through up to {daily_limit} companies."
    )

    messages = [
        {
            "role": "user",
            "content": (
                f"Process the account list from '{csv_filepath}'. "
                f"{limit_instruction} "
                "Find the right contact at each company, research them, score ICP fit, "
                "and write casual, human-sounding messages. No em dashes anywhere. "
                "Keep messages short and conversational. Begin now."
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
    # 4 searches per company; unlimited = no cap (very large number)
    MAX_SEARCHES = 999999 if unlimited else daily_limit * 4
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
                    budget_note = f"[dim]({searches_done})[/dim]" if unlimited else f"[dim]({searches_done}/{MAX_SEARCHES})[/dim]"
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
                    ("Done!", "bold green"),
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
    console.print("[bold]Output files:[/bold]")

    files = [
        (f"output/action_report_{date_str}.md",  "Action Report (open this first)"),
        (f"output/crm_import_{date_str}.csv",    "CRM Import CSV"),
        (f"output/queue_{date_str}.json",         "Raw JSON"),
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
            "  python agent.py \"C:\\Users\\You\\Downloads\\my_accounts.csv\"\n"
            "  python agent.py my_accounts.csv --limit 5   (test with 5 first)\n\n"
            "The agent will:\n"
            "  1. Find the right marketing contact at each company\n"
            "  2. Research the company via web search\n"
            "  3. Score ICP fit (1-10)\n"
            "  4. Draft connection request + first message + follow-up\n"
            "  5. Output a ranked action report + CRM import CSV"
        ),
    )
    parser.add_argument("csv_file", help="Path to Sales Navigator account list CSV")
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=DAILY_LIMIT,
        metavar="N",
        help="Max companies to process (default: 0 = all). Use --limit 5 to test first.",
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
