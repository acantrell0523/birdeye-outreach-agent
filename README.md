# BirdEye LinkedIn Outreach Agent

> AI-powered LinkedIn prospecting for BirdEye. Give it your Sales Navigator account list, it finds the right marketing leader at each company, researches them, scores ICP fit, and writes connection requests and messages you can send directly. You click send. The agent does everything else.

Built on **Claude Opus 4.6** with adaptive thinking. No LinkedIn ToS issues since the AI drafts and you execute manually.

---

## What It Does

```
Your Sales Navigator                                     Your Output
  Account List          ──── BirdEye Outreach Agent ───► Action Report + CRM CSV
  (any size)
                         For each company:
                         1. Finds VP/Director Marketing on LinkedIn
                         2. Researches the company (locations, news, reviews)
                         3. Scores ICP fit 1-10
                         4. Writes a connection request (under 300 chars)
                         5. Writes a first message (80-140 words)
                         6. Writes a follow-up (40-70 words)
```

**Input:** Your Sales Navigator account list CSV (company match export)
**Output:**
- `action_report_DATE.md` — Ranked outreach queue, ready to execute
- `crm_import_DATE.csv` — HubSpot/Salesforce-ready import
- `queue_DATE.json` — Raw data for any custom workflow

---

## Sample Output

```
## #1 [HIGH PRIORITY] Director of Local Marketing @ Heartland Dental
ICP Score: 10/10 | 1,700+ offices | Healthcare

CONNECTION REQUEST (241/300 chars)
  "Hey David, noticed you're running marketing for Heartland across 1,700+
   locations. We work with a lot of large DSOs on the reviews/reputation side.
   Looked relevant, worth connecting?"

FIRST MESSAGE
  "Hey David, thanks for connecting. Quick question: what does your current
   process look like for managing Google reviews across all your locations?
   Asking because that tends to be the hardest part for groups your size
   and it's exactly what we work on.

   We work with several large DSOs and the ones getting the most out of their
   reputation programs are usually doing a few specific things differently.
   Happy to share what we're seeing if it would be useful. Worth a quick chat?"

FOLLOW-UP
  "Hey David, wanted to share something relevant. DSOs with consistent 4.5+
   stars across locations are outperforming on new patient acquisition by
   30-50% vs locations under 4.0 in the same market. Thought that might be
   worth a look given your scale. Still happy to connect if the timing works."
```

---

## Requirements

- **Python 3.10+** (3.13 recommended)
- **Anthropic API key** — get one at [console.anthropic.com](https://console.anthropic.com)
- **LinkedIn Sales Navigator** — for exporting your account lists

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/acantrell0523/birdeye-outreach-agent
cd birdeye-outreach-agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your API key

**Windows:**
```
setup_key.bat
```
Follow the prompts. Saves permanently to your user environment variables.

**Mac/Linux:**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
# Add to ~/.zshrc or ~/.bashrc to make it permanent
```

---

## Usage

Export your Sales Navigator account list as CSV, then run it:

```bash
# Windows
run.bat "C:\Users\You\Downloads\my_accounts.csv"

# Mac/Linux
python agent.py ~/Downloads/my_accounts.csv
```

**Test with a small batch first:**
```bash
run.bat "C:\Users\You\Downloads\my_accounts.csv" 5
python agent.py ~/Downloads/my_accounts.csv --limit 5
```

No limit by default. It processes your entire account list.

The agent will:
1. Load all matched companies from your CSV
2. Search the web to find the best ICP contact at each company
3. Research the company
4. Score, draft, and save everything
5. Generate your action report

### Already have a contacts list?

If you exported a **people list** from Sales Navigator instead of an account list:

```bash
python agent.py my_contacts.csv
```

The agent detects the file format automatically.

---

## Input File Format

Standard Sales Navigator account match export. Required columns:

| Column | Description |
|--------|-------------|
| `Account Name` | Your target company |
| `Match Status` | `MATCHED` or `FAILED` — agent skips FAILED rows |
| `Matched Company Name` | Verified company name from LinkedIn |
| `Matched Company Linkedin Url` | Company LinkedIn page |
| `Match Score (0-5/Highest)` | Higher = better match |

Export from Sales Navigator: **Lists > Account Lists > [Your List] > Export**

---

## ICP Targeting

The agent knows BirdEye's ICP and automatically finds the right people.

**Target companies:**
- 3-5,000 locations (sweet spot: 10-500)
- Healthcare (dental, optometry, medical), Automotive, Home Services, Real Estate, Restaurants, Retail, Financial Services

**Target titles (in priority order):**
- CMO, VP of Marketing, Director of Marketing
- Director of Digital Marketing, Director of Local Marketing
- Head of Local SEO, VP Customer Experience
- CEO/President at orgs with 10-100 locations

**High-priority signals:**
- Recent acquisition or new location opening
- Negative Google review patterns
- DSO/MSO structure
- PE-backed growth

**ICP Score (1-10):**
```
9-10  Perfect fit: multi-location, right title, clear pain signal
7-8   Strong fit: right industry + title, likely multi-location
5-6   Moderate fit: adjacent title or single location
3-4   Weak fit: wrong industry or title too far removed
1-2   Skip
```

---

## Configuration

Edit `config.py` to change the model or adjust ICP context:

```python
MODEL = "claude-opus-4-6"   # AI model
MAX_TOKENS = 16000           # Max tokens per API call
DAILY_LIMIT = 0              # 0 = process entire file; set to N to cap
```

You can also edit `BIRDEYE_CONTEXT` and `ICP_SCORING_GUIDE` in `config.py` to update:
- Product descriptions
- Target industries and titles
- Pain points and trigger events

---

## Output Files

All outputs go to the `output/` folder.

### `action_report_DATE.md`
Open this first. Contains:
- Priority-ranked contact list
- ICP score + reasoning per contact
- Company research highlights
- Ready-to-send connection request (with character count)
- Ready-to-send first message
- Ready-to-send follow-up
- Action checklist per contact

### `crm_import_DATE.csv`
Direct import to HubSpot or Salesforce. Fields:
`First Name`, `Last Name`, `Job Title`, `Company`, `LinkedIn URL`, `Email`, `Phone`, `Location`, `Industry`, `ICP Score`, `Connection Request`, `First Message`, `Follow Up`, `ICP Reasoning`, `Company Insights`, `Source`

### `queue_DATE.json`
Raw JSON sorted by ICP score. Use for custom integrations.

---

## How It Works

```
agent.py                     tools.py
┌─────────────────┐          ┌──────────────────────────┐
│  Agentic Loop   │          │  search_web()            │
│                 │◄────────►│  read_companies_csv()    │
│  Claude Opus    │  tools   │  read_contacts_csv()     │
│  Adaptive       │          │  save_contact_to_queue() │
│  Thinking       │          │  generate_action_report()│
└─────────────────┘          └──────────────────────────┘
        │
        ▼
   output/
   ├── action_report_DATE.md
   ├── crm_import_DATE.csv
   └── queue_DATE.json
```

**Search budget:** 4 web searches per company (2 to find the contact, 2 for company research). Keeps costs predictable regardless of list size.

**Contact discovery:** The agent searches DuckDuckGo for LinkedIn profiles matching the company and ICP titles. When profiles come up, names and titles get pulled from the search result titles. When they don't (DuckDuckGo doesn't always index LinkedIn people pages), the agent flags the contact for manual Sales Navigator lookup and still writes company-specific messages.

**Message quality:** No em dashes, no corporate buzzwords, no over-personalized AI-speak. Messages are written to sound like a real person sent them.

---

## Cost

Roughly 4 web searches and 1 API call per company:

| Companies | Approx. Cost |
|-----------|-------------|
| 5         | ~$0.05      |
| 25        | ~$0.25      |
| 100       | ~$1.00      |
| 276       | ~$2.75      |

Based on Claude Opus 4.6 at $5/1M input tokens, $25/1M output tokens.

---

## Project Structure

```
birdeye-outreach-agent/
├── agent.py          # Main agent loop + system prompt
├── config.py         # BirdEye ICP context, model settings
├── tools.py          # Tool implementations (search, CSV, report)
├── requirements.txt  # Python dependencies
├── run.bat           # Windows launcher
├── setup_key.bat     # Windows API key setup
├── sample/
│   └── contacts.csv  # Sample data for testing
└── output/           # Generated reports (gitignored)
```

---

## Notes

**LinkedIn ToS:** This tool does not automate any LinkedIn actions. It drafts messages and you send them manually. Fully compliant.

**API key:** Never commit your API key. `setup_key.bat` stores it in Windows user environment variables, not in any project file.

**DuckDuckGo rate limits:** If searches come back empty, wait a few minutes and re-run. The agent handles empty results gracefully.

---

## License

MIT
