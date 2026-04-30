# 🚀 Deployment Guide

## 📋 Prerequisites
- GitHub account
- Render account (free tier)
- Your API keys ready

## 🔐 API Keys Setup

### 1. Get Your API Keys:
- **Telegram Bot Token**: @BotFather → `/newbot`
- **Groq API Key**: https://console.groq.com/keys
- **Gemini API Key**: https://makersuite.google.com/app/apikey

### 2. In Render:
1. Go to your Web Service → Environment
2. Add these Environment Variables:
   ```
   TELEGRAM_BOT_TOKEN=your_actual_token
   GROQ_API_KEY=your_actual_groq_key
   GEMINI_API_KEY=your_actual_gemini_key
   SAFE_DAY_BUFFER=5
   REMINDER_HOUR=9
   ```

## 📦 Deployment Steps

### Option A: Auto-Deploy (Recommended)
1. **Fork this repo** to your GitHub
2. **Connect Render** → New Web Service
3. **Choose your forked repo**
4. **Set environment variables** (see above)
5. **Deploy** 🚀

### Option B: Manual Deploy
1. **Clone** your forked repo
2. **Create `render.yaml`** (included)
3. **Push** to GitHub
4. **Connect** Render to repo

## 🔧 Runtime Requirements
- **Python 3.9+**
- **Dependencies**: `pip install -r requirements.txt`
- **Port**: Render automatically sets `$PORT`

## ✅ Health Checks
Render will automatically:
- Monitor your bot's health
- Restart if it crashes
- Deploy on git push

## 🌐 Webhook Setup (Optional)
For instant updates vs polling:
1. In Render: Get your app URL
2. In BotFather: `/setwebhook` + URL
3. Update bot.py to use webhook mode

## 📞 Support
- Render docs: https://render.com/docs
- Telegram Bot API: https://core.telegram.org/bots/api

---

**🎉 Your bot will be live 24/7 on Render's free tier!**
