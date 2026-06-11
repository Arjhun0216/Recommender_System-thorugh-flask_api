# 🎯 RecAPI — Universal Recommendation System

> A plug-and-play recommendation engine as a service. Send user interactions, get personalized recommendations back. Works with any language, any platform, any scale.


## 📖 What Is This?

**RecAPI** is a universal recommendation system that any application can plug into via simple REST APIs. It learns from user interactions and generates personalized recommendations — just like Netflix, Amazon, and Spotify — but as a standalone service that any developer can integrate with in minutes.

```
Your App (E-commerce / Streaming / Food / News)
         ↓
  POST /interact  →  User viewed, liked, carted, or bought something
         ↓
  ML Engine processes and learns from the interaction
         ↓
  GET /recommend  →  Returns personalized items ranked by score
         ↓
  Show recommendations to your user
```

Each developer gets their own **isolated environment** via an API key. A movie app and a food app can both use the same RecAPI — their data never mixes.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔑 **Developer Registration** | Register via web portal or API, get a unique API key instantly |
| 🏢 **Multi-tenant** | Complete data isolation per developer via API key scoping |
| 🧠 **Collaborative Filtering** | Learns from similar users using cosine similarity |
| ⚖️ **Weighted Scoring** | view=2, like=4, cart=8, buy=10 |
| 📊 **4-Source Blending** | History (40%) + Collaborative (30%) + Regional (20%) + Global (10%) |
| ⚡ **DSA Optimized** | LRU Cache, Min Heap, Hash Set, Hash Map for sub-100ms responses |
| 📁 **CSV / Excel / ODS Import** | Upload product catalogs with column mapping |
| 🌐 **Language Agnostic** | Pure REST — works with Python, JS, PHP, Ruby, Java, Go, curl |
| 🎨 **Developer Portal** | Dark Vercel-style web UI for key management and documentation |

---

## 🛠️ Tech Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.10+ | Core language |
| **Flask** | 3.0.0 | Web framework and API server |
| **Flask-SQLAlchemy** | 3.1.1 | ORM — database models and queries |
| **Flask-Login** | 0.6.3 | Session management for web portal |
| **Flask-Bcrypt** | 1.0.1 | Password hashing |

### Machine Learning
| Technology | Version | Purpose |
|---|---|---|
| **scikit-learn** | 1.2.2 | Cosine similarity for collaborative filtering |
| **pandas** | 2.1.3 | User-item matrix construction |
| **numpy** | 1.24.3 | Numerical operations |

### Database
| Technology | Purpose |
|---|---|
| **SQLite** | Local development database (auto-created) |
| **PostgreSQL / MySQL** | Production database |
| **SQLAlchemy ORM** | Database-agnostic queries |

### DSA Layer
| Structure | Implementation | Purpose |
|---|---|---|
| **LRU Cache** | `OrderedDict` | Cache recommendations — O(1) lookup |
| **Min Heap** | `heapq` | Top-N selection — O(n log k) |
| **Hash Set** | `set` | Duplicate interaction detection — O(1) |
| **Hash Map** | `dict` | API key caching — O(1) validation |

### File Import
| Library | Purpose |
|---|---|
| **openpyxl** | Read `.xlsx` Excel files |
| **odfpy** | Read `.ods` LibreOffice files |
| **pandas** | Read `.csv` files and process DataFrames |

### Frontend Portal
| Technology | Purpose |
|---|---|
| **Jinja2** | HTML templating engine (built into Flask) |
| **Vanilla CSS** | Dark Vercel-style theme with CSS variables |
| **Vanilla JS** | Copy key, toggle show/hide, language switcher |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- pip
- Git

---

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/recommendation_system.git
cd recommendation_system
```

---

### 2. Create Virtual Environment

```bash
# Create
python -m venv venv

# Activate — Windows Git Bash
source venv/Scripts/activate

# Activate — Mac / Linux
source venv/bin/activate

# Confirm activation — you should see (venv) in your prompt
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Configure Environment

Create a `.env` file in the project root:

```env
SECRET_KEY=your-super-secret-key-change-this
FLASK_ENV=development
```

> ⚠️ Never commit `.env` to GitHub. It is already in `.gitignore`.

---

### 5. Run the Application

```bash
python run.py
```

On first run, this automatically:
- Creates the SQLite database file `recommendation.db`
- Creates all 5 database tables
- Starts the server on port 5000

---

### 6. Visit the Portal

Open your browser and go to:

```
http://localhost:5000
```

You'll see the dark-themed developer portal landing page.

---

### 7. Register and Get Your API Key

1. Click **Get Started** on the landing page
2. Fill in your name, email, app name, and password
3. Copy your API key — **shown only once**
4. Start making API calls using the key in your `X-API-Key` header

---


## ⚙️ How the ML Engine Works

```
User sends an interaction
         ↓
┌─────────────────────────────────────────────┐
│           Recommendation Engine             │
│                                             │
│  Source 1 — User History        (40%)       │
│  What this specific user did before         │
│                                             │
│  Source 2 — Collaborative (30%)             │
│  What similar users liked (cosine sim)      │
│                                             │
│  Source 3 — Regional Trending   (20%)       │
│  Popular items in user's region             │
│                                             │
│  Source 4 — Global Trending     (10%)       │
│  Popular items everywhere                   │
└─────────────────────────────────────────────┘
         ↓
   Blend all scores
         ↓
   Min Heap → Top N items   (O(n log k))
         ↓
   Normalize to 0.0 - 1.0
         ↓
   Save to DB + LRU Cache
         ↓
   Return ranked recommendations
```

---

## 🧮 DSA Concepts Used

| Concept | Where | Benefit |
|---|---|---|
| **LRU Cache** | Recommendation results | O(1) retrieval — skip ML recalculation |
| **Min Heap** | Top-N selection | O(n log k) vs O(n log n) full sort |
| **Hash Set** | Duplicate detection | O(1) — prevents score inflation |
| **Hash Map** | API key cache | O(1) — avoids DB hit on every request |
| **Batch Queue** | CSV import | 500 rows per write — 500x faster |

---

## 🗄️ Database Schema

```
developers          users               items
──────────────      ──────────────      ──────────────
id (PK)             id (PK)             id (PK)
name                api_key             api_key
email               user_id             item_id
app_name            region              category
password_hash       created_at          region
api_key                                 created_at
created_at

interactions        recommendations
──────────────      ──────────────
id (PK)             id (PK)
api_key             api_key
user_id (FK)        user_id (FK)
item_id (FK)        item_id
action              score
weight              source
region              generated_at
category
created_at
```

---



## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---



## 👨‍💻 Built By

**Arjun** — Built from scratch over multiple sessions, learning Flask, SQLAlchemy, ML, DSA, and full-stack development along the way.

> *"I am just exploring and building something new the world needs."*

---

<div align="center">
  <p>Made with ❤️ — RecAPI</p>
  <p>
    <a href="http://localhost:5000">Portal</a> •
    <a href="http://localhost:5000/docs">Docs</a> •
    <a href="http://localhost:5000/api/v1/health">Health</a>
  </p>
</div>
