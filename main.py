

import re
import sqlite3
import token
from urllib import response
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import feedparser
import requests
def init_db():
    connection = sqlite3.connect("riskwatch.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            project_name TEXT NOT NULL,
            network TEXT DEFAULT 'NEAR'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            headline TEXT NOT NULL,
            summary TEXT,
            source_name TEXT,
            source_url TEXT,
            severity TEXT,
            affected_tokens TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.commit()
    connection.close()


init_db()
app = FastAPI(
    title="NEAR RiskWatch",
    description="Multi-agent risk intelligence for NEAR ecosystem traders",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
# Token information
class Token(BaseModel):
    symbol: str
    project_name: str
    network: str = "NEAR"


# Temporary portfolio storage
portfolio = []


@app.get("/")
def home():
    return {
        "project": "NEAR RiskWatch",
        "status": "running",
        "message": "Risk intelligence system is ready"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Add a token
@app.post("/portfolio")
def add_token(token: Token):
    connection = sqlite3.connect("riskwatch.db")
    cursor = connection.cursor()

    try:
        cursor.execute(
            "INSERT INTO portfolio (symbol, project_name, network) VALUES (?, ?, ?)",
            (token.symbol, token.project_name, token.network)
        )
        connection.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Token already exists in portfolio"
        )
    finally:
        connection.close()

    return {
        "message": "Token added successfully",
        "token": token
    }

# View portfolio
@app.get("/portfolio")
def get_portfolio():
    connection = sqlite3.connect("riskwatch.db")
    cursor = connection.cursor()

    cursor.execute("SELECT symbol, project_name, network FROM portfolio")
    rows = cursor.fetchall()

    tokens = [
        {
            "symbol": row[0],
            "project_name": row[1],
            "network": row[2]
        }
        for row in rows
    ]

    connection.close()

    return {
        "total_tokens": len(tokens),
        "tokens": tokens
    }
    connection.close()

    return {
        "total_tokens": len(tokens),
        "tokens": tokens
    }

# Remove a token
@app.delete("/portfolio/{symbol}")
def remove_token(symbol: str):
    for token in portfolio:
        if token.symbol.lower() == symbol.lower():
            portfolio.remove(token)
            return {
                "message": f"{symbol} removed successfully"
            }

    raise HTTPException(
        status_code=404,
        detail="Token not found"
    )
class EventInput(BaseModel):
    headline: str
    summary: str
    source_name: str
    source_url: str
    published_at: str


@app.post("/events/analyze")
def event_intelligence_agent(event: EventInput):

    text = (event.headline + " " + event.summary).lower()

    risk_keywords = {
        "critical": ["exploit", "hack", "stolen", "security breach"],
        "high": ["lawsuit", "ban", "sanction", "investigation"],
        "medium": ["outage", "regulation", "delay", "suspension"]
    }

    severity = "low"
    matched_keywords = []

    for level, keywords in risk_keywords.items():
        matches = [word for word in keywords if word in text]

        if matches:
            severity = level
            matched_keywords = matches
            break

    return {
        "agent": "Event Intelligence Agent",
        "event": event.headline,
        "severity": severity,
        "matched_keywords": matched_keywords,
        "source": event.source_name,
        "source_url": event.source_url,
        "published_at": event.published_at,
        "status": "screened_not_verified",
        "message": "This is an initial event screening, not a confirmed market impact."
    }
class VerificationSource(BaseModel):
    headline: str
    summary: str
    source_name: str
    source_url: str


class VerificationInput(BaseModel):
    reports: list[VerificationSource]


@app.post("/events/verify")

def verification_agent(data: VerificationInput):
    from urllib.parse import urlparse
    import re

    unique_sources = {}
    reports = []

    stop_words = {
        "the", "a", "an", "and", "or", "to", "of", "in",
        "on", "for", "with", "is", "are", "was", "were",
        "has", "have", "this", "that", "by", "from"
    }

    for report in data.reports:
        domain = urlparse(report.source_url).netloc.lower()
        domain = domain.removeprefix("www.")

        if domain:
            unique_sources[domain] = report

        text = (report.headline + " " + report.summary).lower()
        words = {
            word for word in re.findall(r"\b[a-z0-9]+\b", text)
            if word not in stop_words and len(word) > 2
        }

        reports.append({
            "domain": domain,
            "words": words
        })

    source_count = len(unique_sources)
    matching_pairs = 0

    for i in range(len(reports)):
        for j in range(i + 1, len(reports)):
            first = reports[i]
            second = reports[j]

            if not first["domain"] or not second["domain"]:
                continue

            if first["domain"] == second["domain"]:
                continue

            common_words = first["words"] & second["words"]
            all_words = first["words"] | second["words"]

            if all_words:
                similarity = len(common_words) / len(all_words)

                if similarity >= 0.20:
                    matching_pairs += 1

    if source_count < 2:
        status = "insufficient_sources"
        message = "Not enough independent source domains to compare reports."

    elif matching_pairs > 0:
        status = "potentially_corroborated"
        message = (
            "Independent sources contain overlapping event information. "
            "This is preliminary corroboration, not proof that the event is true."
        )

    else:
        status = "multiple_sources_no_match"
        message = (
            "Multiple source domains were found, but their reports "
            "do not contain enough overlapping information."
        )

    return {
        "agent": "Verification Agent",
        "reports_received": len(data.reports),
        "unique_source_domains": source_count,
        "sources": list(unique_sources.keys()),
        "matching_report_pairs": matching_pairs,
        "verification_status": status,
        "message": message,
        "confirmed": False
    }
class TokenAnalysisInput(BaseModel):
    headline: str
    summary: str


@app.post("/tokens/analyze")
def token_analysis_agent(event: TokenAnalysisInput):

    event_text = (event.headline + " " + event.summary).lower()

    network_keywords = [
        "near protocol",
        "near network",
        "near blockchain",
        "near mainnet"
    ]

    network_event = any(
        keyword in event_text for keyword in network_keywords
    )

    affected_tokens = []

    portfolio_data = get_portfolio()
    for token in portfolio_data["tokens"]:
        symbol = token["symbol"].lower()
        project = token["project_name"].lower()

        if symbol in event_text or project in event_text:
            affected_tokens.append({
                "symbol": token["symbol"],
                "project_name": token["project_name"],
                "reason": "The event directly mentions this token or project.",
                "relevance": "direct_match"
            })

        elif network_event:
            affected_tokens.append({
                "symbol": token["symbol"],
                "project_name": token["project_name"],
                "reason": "The event mentions the NEAR network.",
                "relevance": "network_match"
            })

    return {
        "agent": "Token Analysis Agent",
        "portfolio_tokens_checked": len(portfolio_data["tokens"]),
        "event": event.headline,
        "affected_tokens": affected_tokens,
        "status": "initial_relevance_analysis",
        "message": "These are potential relevance matches, not confirmed market impacts."
    }
@app.post("/risk/analyze")
def coordinate_risk_analysis(event: TokenAnalysisInput):

    # Step 1: Check the reported event
    event_result = event_intelligence_agent(
        EventInput(
            headline=event.headline,
            summary=event.summary,
            source_name="Submitted Report",
            source_url="https://example.com/report",
            published_at="Not provided"
        )
    )

    # Step 2: Check available verification evidence
    verification = verification_agent(
        VerificationInput(
            reports=[
                VerificationSource(
                    headline=event.headline,
                    summary=event.summary,
                    source_name="Submitted Report",
                    source_url="https://example.com/report"
                )
            ]
        )
    )

    # Step 3: Check portfolio relevance
    token_analysis = token_analysis_agent(event)
    risk_assessment = risk_assessment_agent(
    event_result,
    verification,
    token_analysis
)
    return {
        "coordinator": "RiskWatch Agent Coordinator",
        "event_intelligence": event_result,
        "verification": verification,
        "risk_assessment": risk_assessment,
        "message": "Initial coordinated analysis completed."
    }

def risk_assessment_agent(event_result, verification, token_analysis):
    severity = event_result["severity"]
    affected_tokens = token_analysis["affected_tokens"]

    confirmed = verification.get("confirmed", False)
    source_count = verification.get("unique_source_domains", 0)

    if not affected_tokens:
        risk_level = "Informational"
        reason = "No direct match with tokens in the portfolio."
        recommended_action = "No immediate portfolio action suggested."

    elif severity == "critical":
        risk_level = "Critical" if confirmed else "Unverified - Critical"
        reason = "A critical event may affect tokens in the portfolio."
        recommended_action = "Review the report and monitor affected tokens."

    elif severity == "high":
        risk_level = "High" if confirmed else "Unverified - High"
        reason = "A high-severity event may affect portfolio tokens."
        recommended_action = "Investigate the report and monitor affected tokens."

    elif severity == "medium":
        risk_level = "Medium" if confirmed else "Unverified - Medium"
        reason = "A medium-severity event may affect portfolio tokens."
        recommended_action = "Keep monitoring for further developments."

    else:
        risk_level = "Low" if confirmed else "Unverified - Low"
        reason = "No high-severity risk keywords were detected."
        recommended_action = "Continue normal monitoring."

    if not confirmed:
        reason += " This report has not been independently verified."

    return {
        "agent": "Risk Assessment Agent",
        "risk_level": risk_level,
        "affected_tokens": affected_tokens,
        "reason": reason,
        "verification_status": verification["verification_status"],
        "source_count": source_count,
        "recommended_action": recommended_action,
        "status": "preliminary_assessment"
    }

@app.get("/monitor/news")

def fetch_near_news():
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    import re
    articles = []
    seen_urls = set()

    # Only include coverage specifically related to NEAR.
    near_keywords = [
        "near protocol",
        "near blockchain",
        "near ecosystem",
        "near network",
        "near intents",
        "chain signatures",
        "$near"
    ]

    def is_near_related(headline, summary):
        text = (headline + " " + summary).lower()
        return any(keyword in text for keyword in near_keywords)

    # 1. NEAR official blog
    blog_url = "https://www.near.org/blog"

    
    try:
        response = requests.get(blog_url, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        
        
        for a in soup.find_all("a", href=True):
            article_url = urljoin(blog_url, a["href"])

            if "/blog/" not in a["href"] or article_url in seen_urls:
                continue

            headline = ""

            try:
                article_response = requests.get(
                    article_url,
                    timeout=10,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                article_response.raise_for_status()

                article_soup = BeautifulSoup(
                    article_response.text, "html.parser"
                )

                title_tag = article_soup.find(
                    "meta", property="og:title"
                )

                if title_tag:
                    headline = title_tag.get("content", "").strip()

                if not headline:
                    twitter_tag = article_soup.find(
                        "meta", attrs={"name": "twitter:title"}
                    )
                    if twitter_tag:
                        headline = twitter_tag.get("content", "").strip()

            except Exception as error:
                print("Article title extraction error:", error)

            headline = headline.removesuffix(" | NEAR").strip()

            if not headline:
                headline = a.get("aria-label") or a.get("title") or ""

            if headline:
                seen_urls.add(article_url)

                articles.append({
                    "headline": headline,
                    "url": article_url,
                    "published": "Date unavailable",
                    "summary": "",
                    "source": "NEAR Protocol Official Blog"
                })

            if len(articles) >= 10:
                break

    except Exception as error:
        print("NEAR blog error:", error)


    # 2. Independent crypto news RSS feeds
    rss_sources = {
        "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
        "Cointelegraph": "https://cointelegraph.com/rss",
        "The Block": "https://www.theblock.co/rss.xml"
    }

    for source_name, feed_url in rss_sources.items():
        try:
            response = requests.get(
                feed_url,
                timeout=20,
                headers={"User-Agent": "NEARRiskWatch/1.0"}
            )
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            for entry in feed.entries:
                headline = entry.get("title", "").strip()
                article_url = entry.get("link", "").strip()

                raw_summary = entry.get("summary", "")
                summary = BeautifulSoup(
                    raw_summary, "html.parser"
                ).get_text(" ", strip=True)

                if not headline or not article_url:
                    continue

                if not is_near_related(headline, summary):
                    continue

                if article_url in seen_urls:
                    continue

                seen_urls.add(article_url)

                articles.append({
                    "headline": headline,
                    "url": article_url,
                    "published": entry.get(
                        "published", "Date unavailable"
                    ),
                    "summary": summary,
                    "source": source_name
                })

        except Exception as error:
            print(source_name, "RSS error:", error)

    if not articles:
        raise HTTPException(
            status_code=502,
            detail="No NEAR-related news articles found."
        )

    return {
        "source": "Multiple news sources",
        "articles_found": len(articles),
        "articles": articles
    }

        
@app.post("/monitor/run")
def run_risk_monitor():
    news = fetch_near_news()
    processed = 0
    skipped = 0

    connection = sqlite3.connect("riskwatch.db")
    cursor = connection.cursor()

    try:
        for article in news["articles"]:
            headline = article["headline"]
            summary = article.get("summary", "")
            source_url = article["url"]
            source_name = article.get("source", "NEAR Protocol Official Blog")

            cursor.execute(
                "SELECT id FROM alerts WHERE source_url = ?",
                (source_url,)
            )

            if cursor.fetchone():
                skipped += 1
                continue

            event = EventInput(
                headline=headline,
                summary=summary,
                source_name=source_name,
                source_url=source_url,
                published_at=article.get("published", "Unknown")
            )

            event_result = event_intelligence_agent(event)

            verification = verification_agent(
                VerificationInput(
                    reports=[
                        VerificationSource(
                            headline=headline,
                            summary=summary,
                            source_name=source_name,
                            source_url=source_url
                        )
                    ]
                )
            )

            token_analysis = token_analysis_agent(
                TokenAnalysisInput(
                    headline=headline,
                    summary=summary
                )
            )

            risk_assessment = risk_assessment_agent(
                event_result,
                verification,
                token_analysis
            )

            cursor.execute(
                """
                INSERT INTO alerts
                (headline, summary, source_name, source_url,
                 severity, affected_tokens)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    headline,
                    summary,
                    source_name,
                    source_url,
                    risk_assessment["risk_level"],
                    str(risk_assessment["affected_tokens"])
                )
            )

            processed += 1

        connection.commit()

    finally:
        connection.close()

    return {
        "message": "Risk monitoring completed.",
        "articles_processed": processed,
        "duplicates_skipped": skipped
    }


@app.get("/alerts")
def get_alerts():
    connection = sqlite3.connect("riskwatch.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM alerts ORDER BY created_at DESC"
    )

    alerts = [dict(row) for row in cursor.fetchall()]
    connection.close()

    return {
        "total_alerts": len(alerts),
        "alerts": alerts
    }
