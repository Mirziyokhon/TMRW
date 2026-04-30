# 🤖 DeadlineBot - Free API Version

A smart Telegram bot that helps you never miss opportunities. Powered by **100% free APIs** - Groq Whisper, Google Gemini, and DuckDuckGo scraping.

## ✨ Features

- 🎙️ **Voice to text** - Send voice notes, bot transcribes them
- 🧠 **AI analysis** - Extracts opportunities from your descriptions  
- 🔍 **Web verification** - Searches official sources for deadlines
- 📅 **Step generation** - Creates actionable mini-deadlines
- ⏰ **Daily reminders** - Morning notifications for due tasks
- ✏️ **Full CRUD** - Edit, update, delete opportunities
- 📋 **List management** - View and manage all opportunities

## 🛠️ Tech Stack

**All FREE APIs:**
- **Groq Whisper** - Voice transcription (free tier)
- **Google Gemini** - AI analysis (1500 req/day free)
- **DuckDuckGo** - Web scraping (no API key needed)
- **python-telegram-bot** - Telegram integration

## 🚀 Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/yourusername/deadlinebot.git
cd deadlinebot
cp .env.template .env
```

### 2. Add API Keys
Edit `.env` with your keys:
```env
TELEGRAM_BOT_TOKEN=your_token_here
GROQ_API_KEY=your_groq_key_here  
GEMINI_API_KEY=your_gemini_key_here
```

### 3. Install & Run
```bash
pip install -r requirements.txt
python bot.py
```

## 🔐 Security & Deployment

### 📁 Repository Structure
```
.env.template    # Template for environment variables
.env            # Your actual keys (never committed!)
.gitignore      # Protects your secrets
render.yaml     # Auto-deployment config
DEPLOYMENT.md   # Full deployment guide
```

### 🚀 Deploy to Render (Free)
1. **Fork this repo** to your GitHub
2. **Connect Render** → New Web Service  
3. **Set environment variables** in Render dashboard
4. **Deploy** 🎉

**Full guide:** See [DEPLOYMENT.md](DEPLOYMENT.md)

## 📖 Usage

### Adding Opportunities
- Send **voice note** or **text** describing any opportunity
- Include name and deadline if known
- Bot will extract details and create a step-by-step plan

### Managing Opportunities  
- `/list` - View all opportunities with edit/delete buttons
- Click any opportunity to **edit name, description, URL, deadline**
- **Delete** opportunities you no longer need

### Example Messages
- *"Stanford summer program, deadline June 15"*
- *"Harvard scholarship for international students"*  
- *"MIT competition, register by May 1st"*

## 🛡️ Security Features

- ✅ **Environment variables** - No hardcoded secrets
- ✅ **Git protection** - `.gitignore` prevents leaks
- ✅ **Template files** - Safe to share publicly
- ✅ **Render encryption** - Production keys encrypted

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - feel free to use and modify!

---

**🎯 Never miss a deadline again with DeadlineBot!**
