# 🚀 Deployment Guide — FREEDMENFINDER

This guide shows how to deploy your genealogy research app to Streamlit Community Cloud.

## ✅ What's Ready

Your code is now:
- ✅ Initialized with Git
- ✅ First commit created
- ✅ `.env` and secrets are in `.gitignore` (safe to push)
- ✅ Production-ready with security hardening
- ✅ Configured for Streamlit Cloud

## 📋 Deployment Steps

### Step 1: Create a GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. **Repository name**: `freedmenfinder` (or your choice)
3. **Description**: "AI-powered genealogy research using Claude and FamilySearch"
4. **Visibility**: Public (required for Streamlit Cloud free tier)
5. **DO NOT** initialize with README, .gitignore, or license (you already have them)
6. Click **Create repository**

### Step 2: Push Your Code to GitHub

Copy and run these commands (replace `YOUR_USERNAME`):

```bash
cd "C:\Users\mackb\OneDrive\Desktop\FREEDMENFINDER"

# Add GitHub as remote
git remote add origin https://github.com/YOUR_USERNAME/freedmenfinder.git

# Rename branch to main (if needed)
git branch -M main

# Push code
git push -u origin main
```

**Replace `YOUR_USERNAME` with your actual GitHub username.**

### Step 3: Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **Deploy an app**
3. Sign in with GitHub
4. Select your repository: `YOUR_USERNAME/freedmenfinder`
5. Select branch: `main`
6. Set main file path: `app.py`
7. Click **Deploy!**

### Step 4: Configure Secrets

**IMPORTANT**: Never commit `.env` file!

Your `.env` file is in `.gitignore` and won't be pushed to GitHub.

For Streamlit Cloud, add secrets in the app settings:

1. Go to your deployed app on Streamlit Cloud
2. Click **⋮ (menu)** → **Settings**
3. Click **Secrets** 
4. Paste your secrets:

```toml
ANTHROPIC_API_KEY = "sk-ant-api03-YOUR-KEY-HERE"
DEMO_MODE = "False"
FAMILYSEARCH_USERNAME = "your-email@example.com"
FAMILYSEARCH_PASSWORD = "your-password"
FAMILYSEARCH_ACCESS_TOKEN = "your-token"
```

5. Click **Save**

Your app will restart with the secrets configured.

## 🔐 Security Checklist Before Deploying

- [ ] `.env` is NOT committed (verify with `git log --all -- .env`)
- [ ] `.streamlit/secrets.toml` is NOT committed
- [ ] GitHub repo is public (required for free Streamlit Cloud)
- [ ] Secrets are added via Streamlit Cloud interface (not in code)
- [ ] API keys are never in `.py` files (hardcoded)
- [ ] `.gitignore` includes all sensitive files

## 📊 Live URL

Once deployed, your app will be live at:
```
https://share.streamlit.io/YOUR_USERNAME/freedmenfinder
```

Anyone with the link can access it! (But can't see your API keys — they're server-side)

## 🔄 Updating Your App

After making changes:

```bash
git add .
git commit -m "Your changes here"
git push origin main
```

Streamlit Cloud will automatically redeploy within seconds!

## 💡 Tips

### Local Development
```bash
DEMO_MODE=True streamlit run app.py
```

### Production Mode (with real APIs)
Set secrets in Streamlit Cloud, then set:
```
DEMO_MODE = "False"
```

### Monitor Deployment
- View logs: App menu → **Manage app** → **View logs**
- See errors: Check logs if app doesn't start
- Debug: Streamlit auto-reloads on code changes

## 🐛 Troubleshooting

### "App failed to deploy"
- Check that `app.py` is in the root directory
- Verify all dependencies are in `requirements.txt`
- Check logs for error messages

### "Module not found error"
- Make sure all imports are in `requirements.txt`
- Test locally: `pip install -r requirements.txt`

### "API key not found"
- Secrets not added to Streamlit Cloud
- Go to app menu → Settings → Secrets
- Add `ANTHROPIC_API_KEY` and other secrets
- Restart the app

### "Demo mode showing, but I want real APIs"
- Go to Streamlit Cloud Settings → Secrets
- Change `DEMO_MODE = "False"`
- Make sure you have API credentials added
- Restart the app

## 🚀 Optional: Deploy to Other Platforms

### Heroku
```bash
heroku login
heroku create your-app-name
git push heroku main
heroku config:set ANTHROPIC_API_KEY="sk-ant-..."
```

### Docker
```bash
docker build -t freedmenfinder .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY="sk-ant-..." freedmenfinder
```

### AWS, Azure, GCP
- Use their container deployment services
- Set environment variables for secrets
- Expose port 8501

## 📚 Resources

- [Streamlit Cloud Documentation](https://docs.streamlit.io/streamlit-cloud)
- [GitHub Quick Start](https://docs.github.com/en/get-started/quickstart)
- [Streamlit Deployment Best Practices](https://docs.streamlit.io/streamlit-cloud/get-started/deploy-an-app)

## ✨ That's It!

Your genealogy research app is now live on the internet! 🎉

Share the link with family members to help research your ancestry together.

---

**Questions?** Check SECURITY.md for secret management questions or see the Streamlit docs above.
