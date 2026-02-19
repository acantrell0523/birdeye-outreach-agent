# BirdEye LinkedIn Outreach Agent

> **AI-powered LinkedIn prospecting for BirdEye** — give it your Sales Navigator account list, it finds the right marketing leader at each company, researches them, scores ICP fit, and drafts personalized connection requests and messages. Human sends. AI does everything else.

Built on **Claude Opus 4.6** with adaptive thinking. Zero LinkedIn ToS violations — the AI drafts, you execute.

---

## What It Does

```
Your Sales Navigator             BirdEye Outreach Agent            Your Output
  Account List          ──────────────────────────────►   Action Report + CRM CSV
  (276 companies)                                          (ranked, ready to send)

                         For each company:
                         1. Finds VP/Director Marketing on LinkedIn
                         2. Researches company (locations, news, reviews)
                         3. Scores ICP fit 1–10
                         4. Drafts connection request (≤300 chars)
                         5. Drafts first message (100–175 words)
                         6. Drafts follow-up (60–90 words)
```

**Input:** LinkedIn Sales Navigator account list CSV (company match export)
**Output:**
- `action_report_DATE.md` — Ranked outreach queue, ready to execute
- `crm_import_DATE.csv` — HubSpot/Salesforce-ready import file
- `queue_DATE.json` — Raw data for any custom workflow

---

## Sample Output

```
## #1 [🔴 HIGH PRIORITY] Director of Local Marketing @ Heartland Dental
ICP Score: 10/10 | 1,700+ offices | Healthcare

CONNECTION REQUEST (226/300 chars)
  "Hi David, managing local marketing across 1,700+ supported dental offices
   is no small feat — especially when each practice has its own Google profile
   and brand identity. I help DSOs solve this exact puzzle. Open to connecting?"

FIRST MESSAGE
  "Your role is one I find endlessly interesting — local marketing for a
   supported network of 1,700+ offices, where each practice maintains its own
   brand identity. That makes reputation management fundamentally different
   from a single-brand franchise.

   Here's what I've seen working with large DSOs: practices that generate
   consistent 4.5+ star reviews outperform on new patient acquisition by
   30–50% vs sub-4.0 locations in the same market..."
```

---

## Requirements

- **Python 3.10+** (3.13 recommended)
- **Anthropic API key** — get one at [console.anthropic.com](https://console.anthropic.com)
- **LinkedIn Sales Navigator** — for exporting your account lists

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/birdeye-outreach-agent
cd birdeye-outreach-agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your API key

**Windows:**
```
setup_key.bat
```
Follow the prompts. The key is saved permanently to your user environment.

**Mac/Linux:**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
# Add to ~/.zshrc or ~/.bashrc to make it permanent
```

---

## Usage

### With a company/account list (primary workflow)

Export your Sales Navigator account list as CSV, then:

```bash
# Windows
run.bat "C:\Users\You\Downloads\my_accounts.csv" --limit 10

# Mac/Linux
python agent.py ~/Downloads/my_accounts.csv --limit 10
```

The agent will:
1. Load all matched companies from your CSV
2. Search the web to find the best ICP contact at each company
3. Research the company + contact
4. Score, draft, and save everything
5. Generate your action report

### With a contacts CSV (if you've already identified people)

If you export a **people list** from Sales Navigator instead:

```bash
python agent.py my_contacts.csv --limit 10
```

The agent detects the file format automatically and adjusts its workflow.

### Test with sample data

```bash
python agent.py sample/contacts.csv --limit 2
```

---

## Input File Formats

### Company/Account List (recommended)
Standard Sales Navigator account match export. Must have these columns:

| Column | Description |
|--------|-------------|
| `Account Name` | Your target company name |
| `Match Status` | `MATCHED` or `FAILED` — agent skips FAILED rows |
| `Matched Company Name` | Verified company name from LinkedIn |
| `Matched Company Linkedin Url` | Company LinkedIn page URL |
| `Match Score (0-5/Highest)` | Higher scores = better matches |

Export from Sales Navigator: **Lists → Account Lists → [Your List] → Export**

### Contacts CSV (fallback)
Standard Sales Navigator people export. Must have:
`First Name`, `Last Name`, `Title`, `Company`, `LinkedIn Profile URL`

---

## ICP Targeting

The agent knows BirdEye's ideal customer profile and automatically:

**Target companies:**
- 3–5,000 locations (sweet spot: 10–500)
- Healthcare (dental, optometry, medical), Automotive, Home Services, Real Estate, Restaurants, Retail, Financial Services

**Target titles (in priority order):**
- CMO, VP of Marketing, Director of Marketing
- Director of Digital Marketing, Director of Local Marketing
- Head of Local SEO, VP Customer Experience
- CEO/President at orgs with 10–100 locations

**High-priority signals the agent looks for:**
- Recent acquisition or new location opening
- Negative Google review patterns
- DSO/MSO structure
- PE-backed growth mandates

**ICP Score (1–10):**
```
9–10  Perfect fit: Multi-location, right title, clear pain signal
7–8   Strong fit: Right industry + title, likely multi-location
5–6   Moderate fit: Adjacent title or single location
3–4   Weak fit: Wrong industry or title too far removed
1–2   Skip
```

---

## Configuration

Edit `config.py` to customize:

```python
MODEL = "claude-opus-4-6"   # AI model
MAX_TOKENS = 16000           # Max tokens per API call
DAILY_LIMIT = 20             # Default contacts per run
```

You can also edit `BIRDEYE_CONTEXT` and `ICP_SCORING_GUIDE` in `config.py` to update:
- BirdEye product descriptions
- Target industries
- Target titles
- Pain points and trigger events
- Message tone/persona

---

## Output Files

All outputs are saved to the `output/` folder:

### `action_report_DATE.md`
Open this first. Contains:
- Priority-ranked contact list
- ICP score + reasoning for each contact
- Company research highlights
- Ready-to-send connection request (with character count)
- Ready-to-send first message
- Ready-to-send follow-up message
- Action checklist per contact

### `crm_import_DATE.csv`
Direct import to HubSpot or Salesforce. Fields:
`First Name`, `Last Name`, `Job Title`, `Company`, `LinkedIn URL`, `Email`, `Phone`, `Location`, `Industry`, `ICP Score`, `Connection Request`, `First Message`, `Follow Up`, `ICP Reasoning`, `Company Insights`, `Source`

### `queue_DATE.json`
Raw JSON — all contact data, sorted by ICP score. Use for custom integrations or reporting.

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

**Search budget:** The agent is limited to **4 web searches per company** (2 for contact discovery, 2 for company research). This prevents runaway API costs and keeps each run focused.

**LinkedIn contact discovery:** The agent searches DuckDuckGo for LinkedIn profile URLs matching the company + ICP titles. When profiles are found, names and titles are extracted from search result titles. When not found (DuckDuckGo doesn't always surface LinkedIn people pages), the agent flags the contact for manual Sales Navigator lookup and still drafts strong, company-specific messages.

**Message quality:** The system prompt instructs Claude to never use generic openers ("I wanted to reach out", "Hope this finds you well"), always reference a specific company fact, and write at a senior AE level — not a junior SDR template.

---

## Cost

Typical API usage per run:

| Contacts | Searches | Approx. Cost |
|----------|----------|--------------|
| 2        | ~8       | ~$0.15       |
| 10       | ~40      | ~$0.75       |
| 20       | ~80      | ~$1.50       |

Pricing based on Claude Opus 4.6 at $5/1M input tokens, $25/1M output tokens.

---

## Project Structure

```
birdeye-outreach-agent/
├── agent.py          # Main agent loop + system prompt
├── config.py         # BirdEye ICP context, model settings
├── tools.py          # Tool implementations (search, CSV, report)
├── requirements.txt  # Python dependencies
├── run.bat           # Windows quick launcher
├── setup_key.bat     # Windows API key setup
├── sample/
│   └── contacts.csv  # Sample data for testing
└── output/           # Generated reports (gitignored)
    ├── action_report_DATE.md
    ├── crm_import_DATE.csv
    └── queue_DATE.json
```

---

## Requirements File

```
anthropic>=0.45.0
duckduckgo-search>=7.0.0
rich>=13.0.0
```

---

## Important Notes

**LinkedIn ToS compliance:** This tool does NOT automate any LinkedIn actions. It only drafts messages. You send them manually. This keeps the workflow fully compliant with LinkedIn's Terms of Service.

**API key security:** Never commit your API key to git. The `setup_key.bat` stores it in your Windows user environment variables, not in any project file.

**Search availability:** DuckDuckGo rate-limits heavy usage. If searches return empty results, wait a few minutes and re-run. The agent handles empty results gracefully and falls back to its training knowledge for well-known companies.

---

## License

MIT — use freely, modify as needed.
