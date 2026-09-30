# SourceMap - Semantic RAG Intelligence for Code

<div align="center">

![SourceMap](https://img.shields.io/badge/SourceMap-Semantic%20Code%20Search-FF6B35?style=for-the-badge)

**Understand any codebase in seconds using AI-powered semantic search , https://sourcemap-self.vercel.app/.**

[![Website](https://img.shields.io/badge/Website-sourcemap--self.vercel.app-FF6B35)](https://sourcemap-self.vercel.app/)
[![Twitter](https://img.shields.io/badge/Twitter-@chirrr2606-1DA1F2)](https://twitter.com/chirrr2606)
[![Email](https://img.shields.io/badge/Email-chiragbn091@gmail.com-EA4335)](mailto:chiragbn091@gmail.com)
[![GitHub](https://img.shields.io/badge/GitHub-chirrrag17-000000)](https://github.com/chirrrag17)

**[🌐 Live Demo](https://sourcemap-self.vercel.app/)** • **[📧 Contact](mailto:chiragbn091@gmail.com)** • **[🐦 Twitter](https://twitter.com/chirrr2606)**

</div>

---

## 🚀 What is SourceMap?

SourceMap solves the biggest problem developers face: **understanding large codebases takes too long**. Instead of spending 30+ minutes searching through 15,000+ lines of code, just ask a question and get instant answers.

**Without SourceMap:** "Show me login code" → Manual search through 500+ files → 30+ minutes ❌

**With SourceMap:** "Show me login code" → Semantic search → Exact files + context → 3 seconds ✅

---

## 🎯 How It Works

1. **Connect GitHub** → OAuth integration
2. **Index Code** → tree-sitter parsing + embeddings
3. **Ask Questions** → Natural language queries
4.  **Get Answers** → File locations + code snippets in seconds
5. **Get Answers** → File locations + code snippets in seconds


---

## ✨ Key Features

- 🔍 **Semantic Search** — Understands code meaning, not just keywords
- ⚡ **Lightning Fast** — 2-3 seconds vs 30+ minutes
- 🧠 **AI-Powered** — Advanced embeddings + LangGraph orchestration
- 🔗 **GitHub Native** — One-click OAuth setup
- 🔐 **Secure** — Your code never used for training

---

## 🛠️ Tech Stack

**Backend:** FastAPI | PostgreSQL | Redis | Celery

**AI/ML:** tree-sitter | OpenAI/Claude Embeddings | Pinecone | LangGraph

**Frontend:** Next.js | TypeScript | Tailwind CSS | Vercel

---

## 📦 Quick Start

### Backend
```bash
git clone https://github.com/chirrrag17/sourcemap.git
cd sourcemap/backend

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

uvicorn main:app --reload
```

### Frontend
```bash
cd ../frontend
npm install
cp .env.example .env.local
npm run dev
```

Visit: `http://localhost:3000`

---

## 🔗 API Example

```bash
POST https://api.sourcemap-self.vercel.app/v1/query
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "repo_id": "user/repo",
  "query": "Show me the login code"
}
```

---

## 📊 Performance

- Indexing: 10,000+ files in < 5 minutes
- Query Response: < 2-3 seconds
- Accuracy: > 85% relevance
- Uptime: 99.5%

---

## 🔐 Security

- 🔒 HTTPS encrypted
- 🚫 Code never used for model training
- 🔑 GitHub OAuth authentication
- ✅ GDPR compliant

---

## 📞 Support

- **Website:** [https://sourcemap-self.vercel.app/](https://sourcemap-self.vercel.app/)
- **Email:** chiragbn091@gmail.com
- **Twitter:** [@chirrr2606](https://twitter.com/chirrr2606)
- **GitHub:** [chirrrag17](https://github.com/chirrrag17)

---

## 🤝 Contributing

```bash
git checkout -b feature/your-feature
git commit -m 'Add feature'
git push origin feature/your-feature
```

---

## 📄 License

MIT License

---

## 🙏 Built With

- [LangGraph](https://github.com/langchain-ai/langgraph)
- [tree-sitter](https://tree-sitter.github.io/)
- [Pinecone](https://www.pinecone.io/)
- [OpenAI](https://openai.com) & [Anthropic](https://www.anthropic.com)
- [Next.js](https://nextjs.org/) & [Tailwind CSS](https://tailwindcss.com/)

---

<div align="center">

Made with ❤️ by [Chirag](https://twitter.com/chirrr2606)

⭐ Star this repo if you find it useful!

</div>
