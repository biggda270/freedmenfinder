# 🌳 FREEDMENFINDER

An AI-powered genealogy research assistant built specifically to help Black Americans trace their family lineage — including back through the era of slavery.

Most genealogy tools are built around records that only start naming people consistently from the mid-1800s onward. For African American research, that's a problem: the **1870 U.S. Census** was the first federal record to list formerly enslaved people by their own full name as free citizens. Records from before that date almost never name an enslaved person directly — they're indexed under the name of the person who enslaved them instead. Genealogists call this the **"1870 brick wall."**

FREEDMENFINDER plans a research strategy that accounts for that shift on both sides of 1870 — Freedmen's Bureau records, Freedman's Bank records, Reconstruction-era cohabitation/marriage registers, and enslaver-indexed slave schedules and plantation/probate records, alongside standard vital and census records — and helps you carry a search across it using the last known enslaver's name, when that's what family history has passed down.

## ✨ Features

- **AI Research Planning**: Claude plans an era-aware search strategy, prioritizing enslaver-indexed records (slave schedules, plantation/probate records) when an ancestor was likely born before emancipation
- **Record Search**: Searches historically appropriate record types — Freedmen's Bureau records, Freedman's Bank records, slave schedules, cohabitation registers, and standard vital/census records (with realistic mock data in demo mode)
- **Evidence Scoring**: AI evaluates match confidence, aware that pre-1866 records name no one directly and that surnames often changed after emancipation, and flags genuine conflicts
- **Narrative Generation**: Creates a warm, dignified, factually-grounded family history narrative
- **Plain-English Record Summary**: Translates the result into a readable summary of the person, their family, and the supporting evidence — no GEDCOM syntax required
- **GEDCOM Export**: Download results in standard genealogical data format for import into Ancestry, MyHeritage, or Gramps

## 🚀 Quick Start

### 1. Install Requirements

```bash
# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux

# Install dependencies
uv pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` with your settings:
```
ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE
DEMO_MODE=True              # Set to False when you have API credits
FAMILYSEARCH_ACCESS_TOKEN=your-token-here
```

### 3. Run the App

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## 📋 Configuration

### Environment Variables

Create a `.env` file in the project root:

```
# Anthropic API Key (get from https://console.anthropic.com)
ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE

# Use mock data (True) or real APIs (False)
DEMO_MODE=True

# FamilySearch credentials (optional, for live mode)
FAMILYSEARCH_USERNAME=your-email@example.com
FAMILYSEARCH_PASSWORD=your-password
FAMILYSEARCH_ACCESS_TOKEN=your-token
```

### Streamlit Configuration

Edit `.streamlit/config.toml` to customize:
- Theme colors
- Port and server settings
- Logging level

## 🔒 Security

**IMPORTANT**: Never commit `.env` or `.streamlit/secrets.toml` to version control!

These files contain sensitive API keys and are in `.gitignore`.

For production/Streamlit Cloud, use the Secrets management interface:
- Streamlit Cloud: Settings → Secrets
- Local: `.streamlit/secrets.toml`

## 📦 Project Structure

```
FREEDMENFINDER/
├── app.py                    # Main Streamlit application
├── config.py                 # Configuration management
├── familysearch_client.py   # FamilySearch API client
├── gedcom_export.py         # GEDCOM export functionality
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
├── .gitignore               # Git ignore rules
├── .streamlit/
│   ├── config.toml          # Streamlit configuration
│   └── secrets.toml.template # Secrets template
└── README.md                # This file
```

## 🧪 Demo Mode

Demo mode uses realistic mock data so you can test the full pipeline without API costs:

```
DEMO_MODE=True  # Uses mock Claude responses + mock FamilySearch records
```

This is perfect for development and testing!

## 💳 Production Mode

To enable real APIs:

1. Get an Anthropic API key: https://console.anthropic.com/account/billing/overview
2. Add credits to your account
3. Update `.env`:
   ```
   DEMO_MODE=False
   ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE
   ```

## 🚢 Deployment

### Streamlit Cloud (Recommended)

1. Push your code to GitHub (make sure `.env` and `.streamlit/secrets.toml` are in `.gitignore`)
2. Go to https://share.streamlit.io/
3. Deploy by connecting your GitHub repo
4. Add secrets in Settings → Secrets

### Docker

```dockerfile
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["streamlit", "run", "app.py"]
```

Run:
```bash
docker build -t freedmenfinder .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=your-key freedmenfinder
```

### Heroku

```bash
heroku create your-app-name
git push heroku main
```

Add environment variables:
```bash
heroku config:set ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE
```

## 🔧 Development

### Adding Features

The pipeline has 4 main steps (in `app.py`):

1. `step1_research_plan()` - AI decides which records to search
2. `step2_search_records()` - Search for records
3. `step3_score_evidence()` - AI scores matches
4. `step4_write_narrative()` - AI writes family history

Each step is independent, so you can modify, test, or replace individual steps.

### Testing

To test with mock data:
```
DEMO_MODE=True streamlit run app.py
```

To test with real APIs:
```
DEMO_MODE=False streamlit run app.py
```

## 📚 API Reference

### Claude API

Using `claude-3-5-sonnet-20241022` (current fastest model).

Cached calls reduce API costs:
- Research planning: ~500 tokens
- Evidence scoring: ~1000 tokens
- Narrative: ~500 tokens

**Total per person**: ~2000 tokens (~$0.01 with caching)

### FamilySearch

Currently using mock data in demo mode.

To implement live FamilySearch:
1. Get developer account: https://developers.familysearch.org
2. Update `familysearch_client.py` with real API calls

## 🐛 Troubleshooting

### "Your credit balance is too low"
→ Add credits at https://console.anthropic.com/account/billing/overview

### "ANTHROPIC_API_KEY not configured"
→ Create `.env` file with your API key

### Streamlit not starting
→ Check Python version: `python --version` (need 3.8+)
→ Reinstall: `uv pip install --force-reinstall streamlit`

### Port 8501 already in use
→ Use different port: `streamlit run app.py --server.port 8502`

## 📖 Resources

- [Streamlit Docs](https://docs.streamlit.io/)
- [Anthropic API Docs](https://docs.anthropic.com/)
- [FamilySearch API](https://developers.familysearch.org/)
- [GEDCOM Format](https://www.gedcom.org/)

## 📝 License

MIT

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repo
2. Create a feature branch
3. Add tests
4. Submit a PR

## 💬 Support

Issues or questions? Open a GitHub issue or check the docs above.

---

**Built with ❤️ using Claude, Streamlit, and FamilySearch data**
