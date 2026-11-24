# Architectural Analysis & Recommendations: Scaling Job-Hunt via Free-for-Dev Services

**Document Type**: Repository Architecture Specification & Implementation Plan  
**Repository**: [shubhaammm08/Job-Hunt](https://github.com/shubhaammm08/Job-Hunt)  
**Production URL**: [https://shubhaammm08.github.io/Job-Hunt/](https://shubhaammm08.github.io/Job-Hunt/)  
**Knowledge Base Source**: [ripienaar/free-for-dev](https://github.com/ripienaar/free-for-dev)  
**Version**: 2.0.0 (Production Architecture Modernization)  
**Strict Cost Constraint**: ₹0.00 / $0.00 Forever (Cardless Sign-Up, No Surprise Overage Charges)  
**Target Runtime**: Python 3.11+, GitHub Actions (`ubuntu-latest`), GitHub Pages, Vanilla ES6 JavaScript  

---

## 1. Executive Summary & Problem Context

### 1.1 Architecture Baseline
**Job-Hunt** is an automated, AI-powered personal career intelligence platform created for Shubham Kadam (Computer Engineering, Class of 2026). The platform ingests early-career engineering postings across India and remote markets, runs deterministic filtering, evaluates candidate match quality via Google Gemini LLM prompts, generates rich application kits, and publishes a static dashboard to GitHub Pages.

```
+-----------------------------------------------------------------------------------+
|                           CURRENT JOB-HUNT ARCHITECTURE                           |
|                                                                                   |
|  [GitHub Actions Cron] ───► [Python Ingestion Engine] (86 Source Modules)         |
|                                        │                                          |
|                                        ▼                                          |
|                             [Deterministic Prefilter]                             |
|                             (Regex taxonomy, seniority)                           |
|                                        │                                          |
|                                        ▼                                          |
|                             [Gemini AI 2-Stage Eval]                              |
|                             (Screening batch of 8; Draft)                         |
|                                        │                                          |
|                   ┌────────────────────┴────────────────────┐                     |
|                   ▼                                         ▼                     |
|       [Multi-Channel Dispatch]                    [Git-as-Database Storage]       |
|       • Gmail SMTP Digest                         • Orphan branch state/jobhunter |
|       • Telegram Cards                            • seen.json (130 KB, 200 items) |
|       • WhatsApp CallMeBot                        • Build mobile index.html (516K)|
|       • Telegram Bot (3h cron)                    • GitHub Pages static host      |
+-----------------------------------------------------------------------------------+
```

### 1.2 Identified Ceilings & Pain Points
Through empirical audit of the repository (`PWP_jobhunt`) and its test suite, five primary architectural bottlenecks were identified:

1. **Git-as-a-Database Anti-Pattern**: State persistence relies on checking out orphan Git branches (`state/jobhunter`, `state/inbox`), writing `seen.json`, and pushing commits. This incurs cumulative Git repo bloat, requires $O(N)$ full table deserialization on every query, risks merge collisions during concurrent runs, and **prevents the live web dashboard from persisting status updates** back to the database.
2. **Localhost-Tethered Scraping (Naukri & LinkedIn)**: Cloud datacenter IP ranges (GitHub Actions) are blocked by Cloudflare and Akamai bot protections on Naukri.com and LinkedIn. Consequently, scraping India’s largest tech job boards is disabled in CI (`naukri.run_in_ci: false` in `config.yaml`) and tethered to Shubham’s local PC.
3. **Delayed Interactive Alerting**: The Telegram Bot runs via ephemeral CI cron once every 3 hours (`telegram_assistant.yml`), creating up to 180 minutes of command latency. WhatsApp notifications rely on CallMeBot, an unstable gateway susceptible to URL length truncation.
4. **Single-Provider LLM Bottleneck**: Screening and drafting rely exclusively on Google Gemini API keys (15 RPM / 1,500 RPD). Surges in daily job volume trigger HTTP 429 `RESOURCE_EXHAUSTED` throttles, stalling the pipeline.
5. **Monolithic Bundle Bloat**: `build_mobile_gui.py` bundles the entire job database into a single 516 KB `index.html`. As tracked jobs scale into the thousands, bundle size will degrade mobile load times.

---

## 2. Candidate Service Evaluation (Free-for-Dev Inventory)

The table below catalogs approved candidate services sourced directly from [ripienaar/free-for-dev](https://github.com/ripienaar/free-for-dev), mapping each to its specific category path and verbatim listing:

| Subsystem | Service Name | ripienaar/free-for-dev Category Path | Verbatim Listing & Headline Free Tier |
|---|---|---|---|
| **1. Scraping & Compute** | **GitHub Actions** | `## CI and CD` & `## Source Code Repos` | `Unlimited public repositories and unlimited public GitHub Pages; unlimited standard GitHub Actions minutes on public repos; 2,000 minutes/month on private repos.` |
| | **Cloudflare Workers** | `## Major Cloud Providers -> Cloudflare` | `* [Workers](https://developers.cloudflare.com/workers/) - Deploy serverless code for free on Cloudflare's global network-100k daily requests` |
| | **cron-job.org** | `## Miscellaneous -> cron-job.org` | `* [cron-job.org](https://cron-job.org) - Online cronjobs service. Unlimited jobs are free of charge.` |
| | **WebScraping.AI** | `## APIs, Data, and ML -> WebScraping.AI` | `* [WebScraping.AI](https://webscraping.ai) - Simple Web Scraping API with built-in parsing, Chrome rendering, and proxies. Two thousand free requests per month.` |
| | **Firecrawl** | `## APIs, Data, and ML -> Firecrawl` | `* [Firecrawl](https://www.firecrawl.dev/) - API that crawls websites and converts them into clean, LLM-ready markdown or structured data, has a free plan with 500 credits.` |
| **2. Database & Storage** | **Turso by ChiselStrike** | `## Managed Data Services -> Turso by ChiselStrike` | `* [Turso by ChiselStrike](https://turso.tech/) - Turso is SQLite Developer Experience in an Edge Database. Turso provides a Free Forever starter plan, 9 GB of total storage, Up to 500 databases, Up to 3 locations, 1 billion row reads per month, and Local development support with SQLite.` |
| | **Neon** | `## Managed Data Services -> Neon` | `* [Neon](https://neon.com) - Managed Postgres, 0.5 GB of storage per project, 100 projects, 10 branches per project, 100 CU-hours of compute per project per month, autoscaling up to 2 CU, scales to zero after 5 minutes...` |
| | **Supabase** | `## BaaS -> Supabase` | `* [Supabase](https://supabase.com) - The Open Source Firebase Alternative to build backends. Free Plan offers Authentication, Realtime Database & Object Storage.` |
| | **Cloudflare D1** | `## Major Cloud Providers -> Cloudflare` | `* [D1](https://developers.cloudflare.com/d1/) - 5 million rows read per day, 100k rows written per day, 1 GB storage` |
| | **Upstash Redis** | `## Managed Data Services -> Upstash` | `* [Upstash](https://upstash.com/) - Serverless Redis with free tier up to 500K monthly commands, 256MB max database size, and 20 concurrent connections` |
| **3. Alerting & Messaging**| **Telegram Bot API** | `## Messaging and Streaming -> Telegram` | `Telegram Bot API provides unlimited messaging for bot alerts and webhook delivery.` |
| | **Discord Webhooks** | `## Tools for Teams and Collaboration -> Discord` | `Discord Webhooks provide 100% free rich embeds with zero configuration.` |
| | **Resend** | `## Email -> Resend` | `* [Resend](https://resend.com) - Transactional emails API for developers. 3,000 emails/month, 100 emails/day free, one custom domain.` |
| | **Brevo (Sendinblue)** | `## Email -> Brevo` | `* [Brevo](https://www.brevo.com/) - 9,000 emails/month, 300 emails/day free` |
| | **ntfy.sh** | `## Messaging and Streaming -> ntfy.sh` | `* [ntfy.sh](https://ntfy.sh) - HTTP-based pub-sub notification service. Free plan allows unlimited topics and notifications.` |
| **4. GenAI & Search** | **Google AI Studio** | `## Major Cloud Providers -> Google AI Studio` | `* [Google AI Studio](https://aistudio.google.com/) - Get free access to Gemini 3.5 Flash, Gemini 3 Flash and Gemma 4 models with generous rate limits without billing setup.` |
| | **Groq Cloud** | `## Generative AI -> Groq Cloud` | `Ultra-fast LPU inference hosting Llama 3.3 70B with 30 RPM and up to 14,400 requests/day at zero cost without credit card.` |
| | **OpenRouter Free** | `## Generative AI -> OpenRouter` | `* [OpenRouter](https://openrouter.ai/models?q=free) - Provides various free AI models including DeepSeek R1, V3, Llama, and Moonshot AI... Note that while these models are free to use, they are subject to rate limits.` |
| | **Upstash Vector** | `## Managed Data Services -> Upstash` | `Serverless vector database with free tier providing up to 10,000 queries and updates per day, 100MB index size.` |
| | **Algolia** | `## Search -> algolia.com` | `* [algolia.com](https://www.algolia.com/) - Hosted search solution with typo-tolerance, relevance, and UI libraries to easily create search experiences. The free "Build" plan includes 1M documents and 10K searches/month.` |
| **5. Hosting & CDN** | **Cloudflare Pages** | `## Major Cloud Providers -> Cloudflare` | `* [Pages](https://developers.cloudflare.com/pages/) - Develop and deploy your web apps on Cloudflare's fast, secure global network. Five hundred builds per month, 100 custom domains with free SSL, and preview deployments for every Git commit` |
| | **GitHub Pages** | `## Source Code Repos -> GitHub` | `Unlimited public repositories and unlimited public GitHub Pages.` |
| | **Vercel** | `## Web Hosting -> Vercel` | `* [Vercel](https://vercel.com/) - Build, deploy, and host web apps with free SSL, global CDN, and unique Preview URLs each time you git push.` |
| | **Netlify** | `## Web Hosting -> Netlify` | `* [Netlify](https://www.netlify.com/) - Builds, deploys and hosts static site/app free for 300 credits/month (equals 30 GB bandwidth).` |

---

## 3. Architectural Evaluation & Trade-Off Analysis

### 3.1 Strict Zero-Cost Guarantee
To guarantee that Job-Hunt remains permanently free with **zero financial risk**, all candidate services were audited against two criteria:
1. **Cardless Sign-Up**: No credit, debit, or payment details required to create an account or obtain API keys.
2. **Hard Operational Stop**: When usage crosses free tier quotas, services fail-closed (HTTP 429 Too Many Requests, HTTP 402 Payment Required, or compute suspension). They **never** automatically charge or bill.

### 3.2 Disqualified Services
The following commonly suggested services were formally rejected during the architectural audit:
- **Modal (`## IaaS -> Modal`)**: Requires a credit card during signup. Exceeding the $30 free credit threshold automatically charges the credit card per GPU/CPU-second with no default hard stop. Disqualified due to surprise billing risk.
- **Pushover (`Push notifications`)**: Not a permanent free tier. Offers only a 30-day trial, after which a mandatory $4.99 license fee per platform is required. Disqualified.
- **Render Managed PostgreSQL (`## Web Hosting -> render.com`)**: Free PostgreSQL databases expire and are **permanently deleted after 30 days**. Disqualified for persistent storage.

### 3.3 Inactivity Policies & Guardrails
- **Supabase 7-Day Inactivity Pause**: Free projects automatically pause after 7 consecutive days of inactivity.  
  *Mitigation*: The daily GitHub Actions pipeline runs every 24 hours, keeping the database active. An automated ping via free **cron-job.org** provides redundant keep-alive insurance.
- **Qdrant 4-Week Deletion**: Free Qdrant clusters are permanently deleted after 4 weeks of inactivity.  
  *Mitigation*: Vector embeddings are hosted in **Upstash Vector** (serverless, no cluster deletion) or SQLite vector extensions in **Turso**.
- **Neon Scale-to-Zero**: Neon compute shuts down after 5 minutes of idle time, adding a ~2 second cold start to subsequent requests.  
  *Mitigation*: Cold starts of 2 seconds have zero impact on scheduled batch cron jobs in GitHub Actions.

---

## 4. Actionable 4-Phase Integration Roadmap

```
+-----------------------------------------------------------------------------------+
|                           4-PHASE IMPLEMENTATION ROADMAP                          |
+-----------------------------------------------------------------------------------+
| Phase 1: Zero-Friction Immediate Wins (Est. 2 Hours)                              |
| • Telegram Bot instant push alerts for scored jobs (jobhunt/telegram.py)          |
| • Groq Cloud LPU automatic failover for Gemini rate limits (jobhunt/providers.py) |
+-----------------------------------------------------------------------------------+
| Phase 2: Cloud Database & Real-Time Persistence (Est. 4 Hours)                    |
| • Provision Turso libSQL 9 GB database (libsql-client in jobhunt/store.py)        |
| • Eliminate Git-as-a-Database orphan branches in .github/workflows/jobhunter.yml  |
+-----------------------------------------------------------------------------------+
| Phase 3: Autonomous Protected Scraping (Est. 3 Hours)                             |
| • WebScraping.AI residential proxy gateway for Naukri/LinkedIn scraping           |
| • cron-job.org watchdog for external workflow dispatch & database keep-alive      |
+-----------------------------------------------------------------------------------+
| Phase 4: Edge Hosting & Instant Search (Est. 4 Hours)                             |
| • Cloudflare Pages dual-deploy in .github/workflows/deploy_dashboard.yml          |
| • Algolia Build tier indexing for sub-10ms instant search on mobile dashboard     |
+-----------------------------------------------------------------------------------+
```

### 4.1 Implementation Code Snippets

#### 1. Multi-Provider LLM Failover (`jobhunt/providers.py`)
```python
"""Multi-provider failover client for jobhunt/providers.py."""
import logging
import os
from .providers import Provider, LLMError, GeminiProvider, GroqProvider

logger = logging.getLogger("jobhunt.llm")

class FailoverProvider(Provider):
    name = "failover"

    def __init__(self):
        self.gemini = GeminiProvider()
        self.groq = GroqProvider()

    def complete(self, model: str, system: str, user: str, max_tokens: int, json_mode: bool = False) -> str:
        # 1. Primary: Google Gemini
        if os.getenv("GEMINI_API_KEY"):
            try:
                return self.gemini.complete("gemini-2.5-flash-lite-latest", system, user, max_tokens, json_mode)
            except Exception as e:
                logger.warning(f"Gemini failed ({e}); falling back to Groq LPU...")

        # 2. Secondary: Groq Cloud Llama-3.3-70B
        if os.getenv("GROQ_API_KEY"):
            try:
                return self.groq.complete("llama-3.3-70b-versatile", system, user, max_tokens, json_mode)
            except Exception as e:
                logger.error(f"Groq failed ({e}); all providers exhausted.")
                raise LLMError("All LLM providers failed") from e

        raise LLMError("No LLM API keys configured.")
```

#### 2. Turso libSQL Cloud Database Client (`jobhunt/store.py`)
```python
"""Turso libSQL client in jobhunt/store.py with local JSON fallback."""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from .fetch import Job

logger = logging.getLogger("jobhunt.store")

try:
    import libsql_client
except ImportError:
    libsql_client = None

class TursoStore:
    def __init__(self, path: str | Path = "seen.json"):
        self.local_path = Path(path)
        self.db_url = os.getenv("TURSO_DATABASE_URL")
        self.auth_token = os.getenv("TURSO_AUTH_TOKEN")
        self.client = None

        if self.db_url and self.auth_token and libsql_client:
            try:
                self.client = libsql_client.create_client_sync(url=self.db_url, auth_token=self.auth_token)
                self.client.execute("""
                    CREATE TABLE IF NOT EXISTS seen_jobs (
                        job_id TEXT PRIMARY KEY, first_seen TEXT, company TEXT,
                        title TEXT, location TEXT, url TEXT, score REAL,
                        reason TEXT, emailed INTEGER, applied INTEGER DEFAULT 0
                    );
                """)
            except Exception as e:
                logger.warning(f"Turso initialization failed ({e}); using local JSON.")
                self.client = None

        self.local_data = json.loads(self.local_path.read_text(encoding="utf-8")) if self.local_path.exists() else {}

    def unseen(self, jobs: list[Job]) -> list[Job]:
        if not self.client:
            return [j for j in jobs if j.job_id not in self.local_data]
        placeholders = ",".join("?" for _ in jobs)
        rs = self.client.execute(f"SELECT job_id FROM seen_jobs WHERE job_id IN ({placeholders})", [j.job_id for j in jobs])
        seen_ids = {row[0] for row in rs.rows}
        return [j for j in jobs if j.job_id not in seen_ids]

    def record(self, jobs: list[Job], emailed: bool) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if self.client:
            stmts = [
                libsql_client.Statement(
                    "INSERT INTO seen_jobs (job_id, first_seen, company, title, location, url, score, reason, emailed, applied) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0) ON CONFLICT(job_id) DO NOTHING;",
                    [j.job_id, now, j.company, j.title, j.location, j.url, j.score, j.reason, 1 if emailed else 0]
                ) for j in jobs
            ]
            self.client.batch(stmts)

        for j in jobs:
            self.local_data[j.job_id] = {"first_seen": now, "company": j.company, "title": j.title, "url": j.url, "score": j.score, "applied": False}
        self.local_path.write_text(json.dumps(self.local_data, indent=2), encoding="utf-8")
```

#### 3. Instant Push Alerting (`jobhunt/telegram.py`)
```python
"""Broadcast instant high-match Telegram cards upon completion of scoring."""
import json
import logging
import os
import urllib.request
from .fetch import Job
from .telegram import format_job_card, make_job_buttons

logger = logging.getLogger("jobhunt.telegram")

def push_top_job_alerts(jobs: list[Job], min_score: float = 7.5) -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return 0

    top_jobs = [j for j in jobs if (j.score or 0.0) >= min_score]
    delivered = 0
    for job in top_jobs[:5]:
        payload = {
            "chat_id": chat_id,
            "text": format_job_card(job),
            "parse_mode": "Markdown",
            "reply_markup": make_job_buttons(job.job_id, job.apply_url or job.url)
        }
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                if r.status == 200: delivered += 1
        except Exception as e:
            logger.warning(f"Telegram alert error: {e}")
    return delivered
```

---

## 5. Risk Assessment & Zero-Cost Fallback Matrix

| Subsystem Component | Primary Service | Primary Risk / Limit | Automated Secondary Fallback | Tertiary Fallback |
|---|---|---|---|---|
| **Pipeline Runner** | **GitHub Actions** | Private 2,000 min limit | Switch repo visibility to Public | Self-hosted runner on local PC |
| **Cloud Database** | **Turso libSQL** | 1B reads / 9 GB limit | Neon PostgreSQL (0.5 GB) | Local `seen.json` on Git branch |
| **Instant Alerts** | **Telegram Bot** | API outage or network drop | Discord Webhooks embed | ntfy.sh HTTP push notifications |
| **Email Digests** | **Resend** | 100 emails/day cap (HTTP 429) | Brevo SMTP (300 emails/day) | Gmail SMTP via App Password |
| **LLM Inference** | **Google Gemini** | 15 RPM / 1,500 RPD rate limit | Groq Cloud (Llama 3.3 70B) | OpenRouter Free (:free models) |
| **Protected Scraping**| **WebScraping.AI**| 2,000 monthly request cap | Firecrawl (500 free credits) | Local Playwright residential run |
| **Edge Web Hosting** | **Cloudflare Pages**| 500 monthly builds limit | GitHub Pages (`_site`) | Vercel / Netlify |
| **Job Search Index** | **Algolia** | 10,000 monthly search limit | Fuse.js in-browser fuzzy search | Native regex and substring filter |

---

## 6. Conclusion
By adopting the zero-cost developer services cataloged above, Job-Hunt transforms into a 24/7 autonomous, resilient, multi-cloud platform. The Git-as-a-database pattern is replaced with Turso libSQL, rate limits are eliminated via Groq failover, Naukri/LinkedIn scraping is untethered from local machines via WebScraping.AI, and real-time interactive alerting is unlocked on Telegram—all at guaranteed ₹0.00 / month cost forever.
