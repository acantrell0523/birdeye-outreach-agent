"""
server.py — BirdEye Outreach MCP Server

Install this once and use it directly inside Claude Desktop, Cursor,
or any other MCP-compatible AI tool. No API key needed — works off
your Claude Pro subscription or whatever model you're already using.

Run setup_claude.py once to auto-configure Claude Desktop, then restart it.
"""

import os
import sys

# Set working directory to the project folder so output/ paths resolve correctly
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

from config import BIRDEYE_CONTEXT, ICP_SCORING_GUIDE
from tools import (
    search_web,
    read_companies_csv,
    read_contacts_csv,
    save_contact_to_queue,
    generate_action_report,
)

mcp = FastMCP("BirdEye Outreach")


# ─── Tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
def search_web_ddg(query: str) -> str:
    """
    Search the web using DuckDuckGo. Free, no API key needed.

    Use for:
    - Finding LinkedIn contacts: '"[Company]" "VP Marketing" site:linkedin.com/in'
    - Researching companies: '[Company] locations 2025 expansion'
    - Reputation research: '[Company] Google reviews reputation 2025'
    """
    return search_web(query)


@mcp.tool()
def read_account_list(filepath: str) -> str:
    """
    Read a LinkedIn Sales Navigator account list / company match CSV.
    Use this when the file has columns like Account Name, Match Status,
    Matched Company Linkedin Url. Call this first to load your companies.
    """
    return read_companies_csv(filepath)


@mcp.tool()
def read_contact_list(filepath: str) -> str:
    """
    Read a LinkedIn Sales Navigator contacts export CSV.
    Use only when the file already has individual people
    (columns: First Name, Last Name, LinkedIn Profile URL).
    If the file has company/account data, use read_account_list instead.
    """
    return read_contacts_csv(filepath)


@mcp.tool()
def save_contact(contact_json: str) -> str:
    """
    Save a researched and drafted contact to today's outreach queue.
    Call this after you have found the contact, researched the company,
    scored ICP fit, and drafted all three messages.

    The connection_request must be under 300 characters.

    Required JSON fields:
      first_name, last_name, full_name, title, company, linkedin_url,
      location, industry, company_size, email, phone,
      icp_score (1-10), icp_reasoning, company_insights,
      connection_request (under 300 chars), first_message, follow_up_message
    """
    return save_contact_to_queue(contact_json)


@mcp.tool()
def generate_outreach_report() -> str:
    """
    Generate the final Markdown action report and CRM CSV from today's queue.
    Call this once at the very end, after all contacts are saved.
    """
    return generate_action_report()


# ─── Prompt Template ──────────────────────────────────────────────────────────

@mcp.prompt()
def birdeye_outreach(csv_path: str) -> str:
    """
    Full BirdEye LinkedIn outreach workflow.
    Provide the path to your Sales Navigator CSV export.
    """
    return f"""You are running BirdEye's LinkedIn outreach workflow.

{BIRDEYE_CONTEXT}

{ICP_SCORING_GUIDE}

Your CSV file is at: {csv_path}

WORKFLOW — follow this exactly for every company:

1. Call read_account_list("{csv_path}") to load the companies.
   If it says to use read_contact_list, call that instead.

2. For each company (process ALL of them unless told otherwise):

   A. FIND THE CONTACT (2 searches max)
      Search 1: '"[Company]" CMO OR "VP Marketing" OR "Chief Marketing Officer" site:linkedin.com/in'
      Search 2: '"[Company]" "Director of Marketing" OR "Director Digital Marketing" site:linkedin.com/in'
      Pull name, title, and LinkedIn URL from the results.
      Pick the most senior ICP title. If nothing shows up, proceed anyway.

   B. RESEARCH THE COMPANY (2 searches max)
      Search 3: '[Company] locations how many 2025 expansion'
      Search 4: '[Company] Google reviews reputation news acquisition 2025'

   C. SCORE ICP FIT 1-10 using the guide above. Write 2-3 sentences of reasoning.

   D. DRAFT CONNECTION REQUEST (hard limit: 300 characters, count it)
      Casual and direct. No em dashes. No corporate buzzwords.
      Reference one real thing from research. End with a simple question.

   E. DRAFT FIRST MESSAGE (80-140 words)
      Open with a genuine question about their situation, not a compliment.
      Short sentences. Conversational. No em dashes.

   F. DRAFT FOLLOW-UP (40-70 words)
      One new piece of value. Soft ask. No em dashes.

   G. Call save_contact() with all the data.

3. After ALL companies are done, call generate_outreach_report().

Start now.
"""


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
