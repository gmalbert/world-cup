# World Cup 2026 Data Analysis & Betting Site — Full Research Report

> **Documents in this series:**
> 1. **This file** — Executive summary, data landscape, API catalog, legal framework
> 2. [`worldcup-site-features.md`](worldcup-site-features.md) — Site features, UX, and tech stack
> 3. [`worldcup-prediction-models.md`](worldcup-prediction-models.md) — Prediction models, ML approaches, and backtesting

---

## 1. Executive Summary

The 2026 FIFA World Cup (June 11 – July 19, USA/Canada/Mexico) is the biggest edition ever: 48 teams, 104 matches, 16 stadiums across 3 countries. It runs for 39 consecutive days, creating an extended window of high-intent sports traffic — a uniquely favorable environment for a data/betting site.

The timing is excellent. The tournament has just started, which means:
- APIs already have 2026 fixture and team data live
- Odds markets are open and moving
- There is still ~5 weeks of group-stage and knockout-round coverage ahead
- Historical data (2018, 2022) is clean and available for model training

The primary business model should be **data + analysis + affiliate referrals** (not operating a sportsbook), which is far simpler legally and faster to launch.

---

## 2. The Data Landscape

### 2.1 What Data Exists

| Data Type | Availability | Quality |
|---|---|---|
| Match schedules / results | Excellent — multiple free sources | ★★★★★ |
| Live scores & events | Good — requires paid tier for real-time | ★★★★☆ |
| Team & player stats | Good — varies by API | ★★★★☆ |
| Head-to-head history | Good — back to 1930 in some sources | ★★★★☆ |
| Lineups & formations | Good — available match-day | ★★★★☆ |
| xG (expected goals) | Moderate — 2022/2026 only for WC | ★★★☆☆ |
| Pre-match odds | Good — 20+ bookmakers available | ★★★★☆ |
| Live/in-play odds | Available — requires paid tier | ★★★☆☆ |
| Historical odds (2018/2022 WC) | Limited — general league data goes back to 2000 | ★★★☆☆ |
| Shot maps | Available via BALLDONTLIE for 2022/2026 | ★★★☆☆ |
| Player injury/availability | Patchy — no fully free source | ★★☆☆☆ |
| Weather / pitch conditions | Available via weather APIs | ★★★☆☆ |
| FIFA rankings / Elo ratings | Freely available via eloratings.net | ★★★★★ |

### 2.2 Historical Depth

- **Match results:** 1930–present (all World Cups)
- **Betting odds:** ~2000–present for major leagues; 2018/2022 for WC specifically via The Odds API (back to 2020) and football-data.co.uk CSVs
- **xG data:** 2017–present (Understat for leagues); 2022/2026 for World Cup (BALLDONTLIE API)
- **Player-level stats:** 2018–present for WC (BALLDONTLIE, API-Football)

The key gap is that World Cup data is sparse compared to domestic leagues — only ~64–104 matches every 4 years. This means models must supplement with qualifying matches, friendlies, and major tournaments (Copa América, AFCON, Euros) to have adequate training data.

---

## 3. API & Data Source Catalog

### 3.1 Free / Freemium APIs

#### **openfootball/worldcup.json** ⭐ Best for: schedules, results
- Fully free, no API key, public domain
- JSON files on GitHub for all World Cups including 2026 fixtures
- No live data, no stats — pure schedule/result layer
- URL: `https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json`

#### **BALLDONTLIE FIFA World Cup API** ⭐ Best for: rich stats + odds
- Covers 2018, 2022, and 2026 World Cups
- Endpoints: teams, players, rosters, matches, standings, lineups, events, per-match player/team stats, shot maps (with xG), attack momentum, moneyline odds, futures odds
- xG and xGOT available for 2022 and 2026; shot coordinates for all three tournaments
- Free tier with API key; cursor-based pagination
- URL: `https://fifa.balldontlie.io`

#### **API-Football (api-sports.io)** ⭐ Best for: comprehensive live data
- Covers 1,200+ leagues; World Cup at `league=1, season=2026`
- Free tier: 100 calls/day
- Endpoints: fixtures, live scores (15-second updates), lineups, events, player stats, standings, top scorers/assisters/cards, injuries, predictions, odds
- Multi-year historical data available
- URL: `https://www.api-football.com`

#### **TheSportsDB** ⭐ Best for: free media assets
- Free API with artwork, team logos, stadium images, league data
- Good for enriching UI without paying for image licenses
- URL: `https://www.thesportsdb.com/league/4429-fifa-world-cup`

#### **football-data.org**
- Free tier covers top leagues (Premier League, Bundesliga, etc.) with match results and basic stats
- Does NOT directly cover World Cup — useful for training data on European national team players' club form

#### **eloratings.net**
- Free CSV/JSON downloads of international Elo ratings for every national team
- Updated after every match — critical input for prediction models

<!-- ### 3.2 Paid APIs (with Free Tiers)

#### **Sportmonks World Cup API**
- All-In plan: real-time xG, Pressure Index (proprietary), odds from 50+ bookmakers across 150+ markets
- Free trial available; fixture/squad data accessible now
- Good for commercial/betting apps

#### **Statorium World Cup API**
- Human-scouted data collected live during matches
- Covers lineups, player numbers, team events, player events
- Also offers editorial content (match previews, squad announcements) — useful for SEO content layer
- Competitive pricing vs. Sportmonks

#### **Livescore API (live-score-api.com)**
- Covers 2026 specifically; group standings, fixtures, live scores, odds (1X2), head-to-head, match events
- Demo key available for testing

#### **Worldcupapi.com**
- Built specifically for FIFA WC 2026
- Live scores, lineups, pre-match stats, historical data, real-time betting odds + market movements -->

### 3.3 Odds-Specific APIs

#### **The Odds API** ⭐ Best for: multi-bookmaker odds comparison
- Live and upcoming odds from 20+ bookmakers
- Historical odds snapshots back to 2020 (5-minute intervals)
- Soccer supported: EPL, La Liga, Champions League, and World Cup
- Free tier: 500 requests/month; paid from ~$79/month
- URL: `https://the-odds-api.com`

#### **OddsPapi** ⭐ Best for: sharp/Asian market odds
- 140+ bookmakers including Pinnacle, Singbet, Betfair Exchange
- 460+ markets: 1X2, Asian Handicaps (every line), BTTS, Over/Under, corners
- Historical odds on free tier — rare among competitors
- 1,372 football tournaments covered
- URL: `https://oddspapi.io`

#### **OddAlerts API**
- Pre-built value bet signals, probability model, live odds, accumulator generation
- Targets bettors/model builders rather than raw data consumers
- Good for a "value bet of the day" feature without building the model from scratch

### 3.4 Scraping / Bulk Data

#### **football-data.co.uk**
- Free CSVs: match results + odds (Bet365, Pinnacle, William Hill, etc.) for 25+ leagues
- Seasons from 2000/01 to present; ~25 years of odds data
- Does not cover World Cup directly but covers all qualifying nations' leagues
- Legally scrape-able; explicitly public domain

#### **Understat**
- Free xG data for top 6 leagues (EPL, La Liga, Bundesliga, Serie A, Ligue 1, RFPL)
- Per-shot xG, player xG, team xG timelines
- Scrapeable; Apify has a ready-made actor for it
- Critical for building player quality features for the model

#### **Transfermarkt**
- Player market values, squad depth, injury history, age profiles
- Scrapeable with care; no official API
- Market value is a strong proxy for squad quality in prediction models

#### **FBref (StatsBomb open data)**
- StatsBomb provides free data through FBref for select competitions
- Advanced metrics: progressive passes, pressure success rate, PPDA, etc.
- StatsBomb also has an open-data GitHub repo (2018 WC fully available)

---
<!-- 
## 4. Legal & Compliance Framework

### 4.1 Business Model Options (Ranked by Legal Complexity)

| Model | Legal Risk | Revenue Potential | Launch Speed |
|---|---|---|---|
| Pure data/analysis site (no betting) | Very Low | Moderate (ads, subscriptions) | Fast |
| Affiliate referrals (CPA) | Low–Medium | High | Medium |
| Affiliate referrals (Revenue Share) | Medium–High | Very High | Slow |
| Operating a sportsbook | Very High | Potentially massive | Very Slow / Impractical |

**Recommendation: Start as a data/analysis site with CPA affiliate links.** This is the fastest path to launch, generates meaningful revenue during the tournament, and avoids the most complex regulatory overhead.

### 4.2 US Affiliate Licensing

Sports betting is regulated at the state level. Eight states currently require affiliate licensing: **Arizona, Colorado, Indiana, Louisiana, Michigan, New Jersey, Pennsylvania, and West Virginia**. Maryland and Arkansas are expected to follow.

Key rules for operating legally as a US-based affiliate:
- CPA (cost-per-acquisition) model is significantly simpler to license than revenue share
- Revenue share licensing involves background checks, fingerprinting, and financial disclosures — similar in depth to operator licensing
- FTC advertising disclosures are required in all states (disclose affiliate relationships)
- All ads must display responsible gambling disclosures and 21+ age requirements
- Never use phrases like "guaranteed win," "risk-free bet," or language targeting minors
- For states without legal sports betting (California, Texas, Florida, New York), you can still operate a data/analysis site — just cannot include affiliate links for sportsbooks

### 4.3 Affiliate Revenue Expectations

- CPA deals typically pay **$50–$200 per new depositing customer** depending on the sportsbook
- Revenue share typically ranges **25–40% of Net Gaming Revenue** generated by referred players
- Top programs (DraftKings, FanDuel, BetMGM, Caesars, Unibet, Betway) all have affiliate programs
- During a World Cup, conversion rates spike significantly — an analysis site with good traffic can earn tens of thousands in CPA during the 39-day tournament

### 4.4 Data Usage Rights

- Public/open-source data (openfootball, eloratings.net, football-data.co.uk, StatsBomb open data): freely usable
- Scraped data: generally legal for personal/research use; commercial use varies — review ToS for each site
- Purchased API data: check licensing terms; most allow display but not resale of raw data
- FIFA's official data is heavily licensed — do not attempt to scrape fifa.com for commercial use

--- -->

## 5. Data Pipeline Architecture

```
┌─────────────────────────────────────────────────────┐
│                   DATA SOURCES                       │
│                                                     │
│  openfootball  BALLDONTLIE  API-Football  OddsPapi  │
│  Understat     football-data.co.uk  Transfermarkt   │
│  eloratings.net  StatsBomb open data                 │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│              INGESTION LAYER                         │
│  - Scheduled cron jobs (match-day: every 15s live)   │
│  - Historical bulk load (one-time, training data)    │
│  - Nightly updates (standings, odds, Elo)            │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│              DATA STORE                              │
│  - PostgreSQL: structured match/team/player data     │
│  - Redis: live odds cache, live score cache          │
│  - S3/object store: historical CSVs, model artifacts │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│              PREDICTION ENGINE                       │
│  (see worldcup-prediction-models.md)                 │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│              FRONTEND SITE                           │
│  (see worldcup-site-features.md)                     │
└─────────────────────────────────────────────────────┘
```

---

## 6. Cost Estimates (Monthly, During Tournament)

| Item | Free Tier Enough? | Estimated Paid Cost |
|---|---|---|
| API-Football | Borderline (100 calls/day) | ~$15–30/month |
| BALLDONTLIE | Yes for stats | Free |
| The Odds API | No (500 req/month too low) | ~$79–199/month |
| OddsPapi | Free tier generous | Free to ~$50/month |
| Statorium/Sportmonks | No — paid required for live | ~$100–300/month |
| Hosting (Vercel/Railway) | Yes for MVP | $0–20/month |
| Database (Supabase) | Yes for MVP | $0–25/month |
| **Total (lean MVP)** | | **~$200–600/month** |

During a 39-day tournament generating affiliate revenue, this budget is easily recouped by a handful of CPA conversions per day.
