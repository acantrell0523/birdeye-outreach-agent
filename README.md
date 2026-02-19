# BirdEye LinkedIn Outreach Agent

Give it your Sales Navigator account list. It finds the right marketing contact at each company, researches them, scores ICP fit, and writes connection requests and messages you can send directly. You click send. The agent does everything else.

Works inside **Claude Desktop**, Cursor, or any AI tool that supports MCP. No command line required. No per-use cost.

---

## How It Works

```
Your Sales Navigator                                    Your Output
  Account List         ─── BirdEye Outreach Agent ───► Action Report + CRM CSV
  (any size)
                        For each company:
                        1. Finds VP/Director Marketing on LinkedIn
                        2. Researches the company (locations, news, reviews)
                        3. Scores ICP fit 1-10
                        4. Writes a connection request (under 300 chars)
                        5. Writes a first message (80-140 words)
                        6. Writes a follow-up (40-70 words)
```

---

## Sample Messages

```
CONNECTION REQUEST (241/300 chars)
  "Hey David, noticed you're running marketing for Heartland across 1,700+
   locations. We work with a lot of large DSOs on the reviews/reputation side.
   Looked relevant, worth connecting?"

FIRST MESSAGE
  "Hey David, thanks for connecting. Quick question: what does your current
   process look like for managing Google reviews across all your locations?
   Asking because that tends to be the hardest part for groups your size
   and it's exactly what we work on.

   We work with several large DSOs and the ones getting the most traction
   are usually doing a few specific things differently. Happy to share what
   we're seeing if it would be useful. Worth a quick chat?"

FOLLOW-UP
  "Hey David, wanted to share something relevant. DSOs with consistent 4.5+
   stars across locations are outperforming on new patient acquisition by
   30-50% vs locations under 4.0 in the same market. Thought that might be
   worth a look. Still happy to connect if the timing works."
```

---

## Setup

### What you need

- **Python 3.10+** — [python.org/downloads](https://python.org/downloads)
- **Claude Desktop** (free download) — [claude.ai/download](https://claude.ai/download)
- **Claude Pro subscription** ($20/month) — no per-use billing, works off your subscription

That's it. No Anthropic API key needed for the Claude Desktop method.

---

### Step 1 — Get the files

```bash
git clone https://github.com/acantrell0523/birdeye-outreach-agent
cd birdeye-outreach-agent
```

Or download the ZIP from GitHub and unzip it.

---

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

---

### Step 3 — Connect to Claude Desktop

**Windows:**
```
setup_claude.bat
```

**Mac:**
```bash
python setup_claude.py
```

This automatically adds the BirdEye tools to your Claude Desktop config. Takes about 5 seconds.

---

### Step 4 — Restart Claude Desktop

Close Claude Desktop completely and reopen it. You'll see a small hammer icon at the bottom of the chat window — that means the tools are connected.

---

### Step 5 — Run it

1. Export your Sales Navigator account list as a CSV
2. Open Claude Desktop
3. Type this (paste in your actual file path):

```
Process my account list at C:\Users\You\Downloads\my_accounts.csv
and build my LinkedIn outreach queue. Find the right marketing contact
at each company, research them, score ICP fit, and write connection
requests and messages. Casual tone, no em dashes, short and human.
Save everything and generate the action report when done.
```

Or use the built-in prompt by typing `/birdeye_outreach` and entering your CSV path.

Claude will handle the rest. When it's done, your output files are in the `output/` folder inside this project.

---

## What Gets Generated

### `output/action_report_DATE.md`
Open this first. Priority-ranked list of every contact with:
- ICP score and reasoning
- Company research highlights
- Ready-to-send connection request (with character count)
- Ready-to-send first message
- Ready-to-send follow-up
- Action checklist

### `output/crm_import_DATE.csv`
Direct import to HubSpot or Salesforce.

### `output/queue_DATE.json`
Raw JSON sorted by ICP score. Use this for any custom workflow.

---

## Input File Format

Standard Sales Navigator account match export. Required columns:

| Column | Description |
|--------|-------------|
| `Account Name` | Your target company |
| `Match Status` | `MATCHED` or `FAILED` — skips FAILED rows automatically |
| `Matched Company Name` | Verified company name from LinkedIn |
| `Matched Company Linkedin Url` | Company LinkedIn page |
| `Match Score (0-5/Highest)` | Higher = better match |

To export: **Sales Navigator > Lists > Account Lists > [Your List] > Export**

---

## Who It Targets

**Target companies:**
- 3-5,000 locations (sweet spot: 10-500)
- Healthcare (dental, optometry, medical), Automotive, Home Services, Real Estate, Restaurants, Retail, Financial Services

**Target titles, in order:**
- CMO, VP of Marketing, Director of Marketing
- Director of Digital Marketing, Director of Local Marketing
- Head of Local SEO, VP Customer Experience
- CEO/President at 10-100 location orgs

**High-priority signals it looks for:**
- Recent acquisition or new location opening
- Negative Google review patterns
- DSO/MSO structure
- PE-backed growth

**ICP Score (1-10):**
```
9-10  Multi-location, right title, clear pain signal
7-8   Right industry + title, likely multi-location
5-6   Adjacent title or single location
3-4   Wrong industry or title too far removed
1-2   Skip
```

---

## Configuration

Edit `config.py` to adjust anything:

```python
MODEL = "claude-opus-4-6"   # Only used by the command-line agent
MAX_TOKENS = 16000
DAILY_LIMIT = 0              # 0 = process entire file; set to N to cap
```

You can also edit `BIRDEYE_CONTEXT` and `ICP_SCORING_GUIDE` to update:
- Product descriptions
- Target industries and titles
- Pain points and trigger events
- Message tone

---

## Other AI Tools (Cursor, Windsurf, etc.)

Any tool that supports MCP can use this. Add the server to your tool's MCP config:

```json
{
  "mcpServers": {
    "birdeye-outreach": {
      "command": "python",
      "args": ["/full/path/to/birdeye_outreach/server.py"]
    }
  }
}
```

On Windows, use double backslashes in the path:
```json
"args": ["C:\\Users\\You\\birdeye_outreach\\server.py"]
```

---

## Command-Line Option (Uses API, Has Cost)

If you prefer running from the command line without Claude Desktop:

```bash
# Set your Anthropic API key first
export ANTHROPIC_API_KEY=sk-ant-...    # Mac/Linux
set ANTHROPIC_API_KEY=sk-ant-...       # Windows

# Run it
python agent.py "C:\Users\You\Downloads\my_accounts.csv"

# Test with a small batch first
python agent.py my_accounts.csv --limit 5
```

---

## Project Structure

```
birdeye-outreach-agent/
├── server.py         # MCP server (Claude Desktop / other AI tools)
├── agent.py          # Command-line agent (uses Anthropic API)
├── config.py         # BirdEye ICP context, settings
├── tools.py          # Tool implementations (search, CSV, report)
├── requirements.txt  # Python dependencies
├── setup_claude.py   # Auto-configure Claude Desktop (cross-platform)
├── setup_claude.bat  # Windows shortcut for setup_claude.py
├── run.bat           # Windows shortcut for command-line agent
├── setup_key.bat     # Windows API key setup (command-line only)
├── sample/
│   └── contacts.csv  # Sample data for testing
└── output/           # Generated reports (gitignored)
```

---

## Notes

**LinkedIn ToS:** This tool drafts messages only. You send them manually. Fully compliant.

**DuckDuckGo:** Web searches are free and don't require an account. If results come back empty, wait a few minutes and try again.

**API key:** Only needed if you use the command-line `agent.py`. Not needed for the Claude Desktop MCP setup.

---

## License

MIT
