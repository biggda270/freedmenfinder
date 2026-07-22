# 🔒 Security Guide — FREEDMENFINDER

This guide explains how to safely manage API keys and secrets in FREEDMENFINDER.

## 🚨 Critical: Never Expose API Keys

Your API keys are **private credentials** that grant access to your accounts and billing.

### ❌ DO NOT:
- Commit `.env` to git/GitHub
- Commit `.streamlit/secrets.toml` to git/GitHub
- Share your `.env` file with others
- Post error messages containing API keys to forums/issues
- Log API keys anywhere
- Add keys to version control history (even if deleted later, they're still in git history)

### ✅ DO:
- Keep API keys in `.env` (local, not committed)
- Use `.streamlit/secrets.toml` for Streamlit Cloud
- Rotate keys if accidentally exposed
- Use environment variables for production
- Treat API keys like passwords

## 📁 File Structure & Security

### Protected Files (in `.gitignore`)

```
.env                           # Local environment variables
.streamlit/secrets.toml        # Streamlit secrets (never committed)
__pycache__/                   # Python cache
*.pyc                          # Compiled Python
.vscode/                       # Editor secrets
```

These files are in `.gitignore` and should NEVER be committed.

### Safe Files (CAN be committed)

```
.env.example                   # Template only, no real keys
.streamlit/secrets.toml.template  # Template only
.gitignore                     # Ignore rules
requirements.txt               # Dependencies
config.py                      # Configuration code
```

## 🔑 Managing API Keys

### 1. Local Development

Create `.env` from template:
```bash
cp .env.example .env
```

Edit `.env` with YOUR credentials:
```
ANTHROPIC_API_KEY=sk-ant-api03-YOUR-REAL-KEY-HERE
DEMO_MODE=False
```

Never commit this file.

### 2. Streamlit Cloud Deployment

Use Streamlit's built-in secrets management:

1. Deploy your repo (make sure `.env` is in `.gitignore`)
2. Go to app dashboard → Settings → Secrets
3. Add your secrets:
   ```
   ANTHROPIC_API_KEY = "sk-ant-api03-YOUR-REAL-KEY-HERE"
   DEMO_MODE = "False"
   ```

Streamlit automatically encrypts and manages these.

### 3. Docker Deployment

Pass secrets via environment variables:

```bash
docker run \
  -e ANTHROPIC_API_KEY="sk-ant-api03-YOUR-KEY" \
  -e DEMO_MODE="False" \
  -p 8501:8501 \
  freedmenfinder
```

Or use a `.env` file:
```bash
docker run --env-file .env -p 8501:8501 freedmenfinder
```

### 4. Production Servers

Use your server's secret management:

**AWS:**
```bash
aws secrets create-secret --name freedmenfinder/api-key --secret-string "sk-ant-..."
```

**Heroku:**
```bash
heroku config:set ANTHROPIC_API_KEY="sk-ant-..."
```

**Environment variables:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## 🛡️ Security Features in Code

### Automatic Key Masking

All logs automatically mask API keys:

```python
from config import mask_sensitive_data

# Logs never show actual keys
logger.info(f"Error: {mask_sensitive_data(error)}")
# Output: "Error: ***REDACTED***"
```

### Error Message Safety

Error messages never contain API keys:

```python
# Safe error handling
try:
    api_response = client.messages.create(...)
except APIError as e:
    masked_error = mask_sensitive_data(str(e))
    st.error(f"API Error: {masked_error}")
    # Shows safe message, never the actual key
```

## 🔄 Rotating Compromised Keys

If you accidentally expose an API key:

### Anthropic Keys
1. Go to https://console.anthropic.com/account/billing/overview
2. Delete the compromised key
3. Create a new key
4. Update `.env` with new key
5. Delete old key from all deployments

### FamilySearch Tokens
1. Go to FamilySearch developer account
2. Revoke the token
3. Generate a new token
4. Update `.env` with new token

## 🚨 Common Mistakes

### ❌ Mistake 1: Committing .env
```bash
git add .env  # WRONG!
```
**Fix:** Add to `.gitignore` and remove from history:
```bash
git rm --cached .env
git commit --amend
```

### ❌ Mistake 2: Hardcoding keys
```python
client = Anthropic(api_key="sk-ant-api03-ACTUAL-KEY")  # WRONG!
```
**Fix:** Use environment variables:
```python
api_key = os.environ.get("ANTHROPIC_API_KEY")
client = Anthropic(api_key=api_key)
```

### ❌ Mistake 3: Logging errors with keys
```python
logger.error(f"Failed: {exception}")  # WRONG if exception contains key!
```
**Fix:** Mask sensitive data:
```python
logger.error(f"Failed: {mask_sensitive_data(str(exception))}")
```

### ❌ Mistake 4: Exposing keys in error messages
```python
st.error(f"API Error: {str(error)}")  # WRONG!
```
**Fix:** Use masked version:
```python
st.error(f"API Error: {mask_sensitive_data(str(error))}")
```

## 🔐 Checking Git History

To verify your `.env` was never committed:

```bash
# Check if .env appears in git history
git log --all -- .env

# View what was in that file
git show <commit-hash>:.env

# Remove from history if found (careful - rewrites history!)
git filter-branch --tree-filter 'rm -f .env' HEAD
```

## 📋 Checklist Before Deploying

- [ ] `.env` is in `.gitignore`
- [ ] `.streamlit/secrets.toml` is in `.gitignore`
- [ ] No API keys in Python code (hardcoded)
- [ ] `.env.example` has no real keys (template only)
- [ ] Created `.streamlit/secrets.toml` locally (not committed)
- [ ] Tested with `DEMO_MODE=True` first
- [ ] For production, used Streamlit Cloud Secrets or server env vars
- [ ] Never ran `git add .env` or committed any secrets
- [ ] Sensitive data is masked in logs and error messages

## 🆘 If You Accidentally Exposed a Key

1. **STOP** - Don't commit again
2. **ROTATE** - Delete and recreate the key immediately
3. **REMOVE** - Remove from git history using `git filter-branch`
4. **CHECK** - Search your commit history to make sure it's gone
5. **AUDIT** - Check Anthropic/FamilySearch account for unauthorized activity

## 📚 Further Reading

- [Anthropic API Security](https://docs.anthropic.com/en/docs/about-claude/authentication)
- [Streamlit Secrets Management](https://docs.streamlit.io/streamlit-cloud/get-started/deploy-an-app/connect-to-data-sources/secrets-management)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

---

**Remember: Treat API keys like passwords. Never share them.** 🔒
