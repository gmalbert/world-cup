# World Cup 2026 Site — Features, UX & Tech Stack

> Part of a 3-document series. See also:
> - [`worldcup-site-overview.md`](worldcup-site-overview.md) — Data landscape, APIs, legal framework
> - [`worldcup-prediction-models.md`](worldcup-prediction-models.md) — Prediction models and ML

---

## 1. Core Philosophy

Build a **data-forward** site that makes you the most useful destination for someone who wants to understand a World Cup match before betting on it. The goal is to be the tool a sharp bettor or data enthusiast opens first — not a generic scores app. Differentiation comes from:

1. Showing model probabilities alongside bookmaker odds (implied probability comparison)
2. Surfacing edges (where your model disagrees with the market)
3. Rich historical context that TV coverage doesn't provide
4. Clean, fast, mobile-first UX — most traffic will be on phones

---

## 2. Feature Map

### 2.1 Core Features (MVP — launch before a match week)

#### Match Hub
- Live scoreboard with real-time goal/card/substitution events
- Group standings table (updates live during matches)
- Knockout bracket tracker (auto-advances teams)
- Match schedule with timezone auto-detection (key for a 3-host-country tournament)
- Venue info and city guides (useful SEO content; 16 stadiums across 3 countries)

#### Pre-Match Analysis Page (the most important page)
For each upcoming match, display:
- **Win/Draw/Loss probabilities** from your model vs. bookmaker implied probabilities
- **Betting edge indicator** — where your model finds value vs. the market
- Head-to-head history (all-time and last 10 meetings)
- Current form (last 5–10 matches for each team)
- Elo rating comparison and trend
- xG for/against over last N matches
- Key player availability (injuries, suspensions)
- Predicted lineup (where API data allows)
- Odds comparison table across 5–10 bookmakers

#### Odds Comparison
- 1X2 (match result) odds from 10–20 bookmakers side by side
- Best odds highlight for each outcome
- Implied probability vs. model probability for each outcome
- Odds movement chart (opening line vs. current line)
- Affiliate links to each bookmaker (CPA revenue driver)

#### Tournament Predictor / Simulator
- Monte Carlo simulation of remaining tournament (runs 10,000+ scenarios)
- Shows each team's probability of: advancing from group, reaching Round of 16/QF/SF/Final/winning
- Updates after every result
- Shareable result cards for social media ("my model says Brazil has a 28% chance of winning")

#### Statistics Dashboard
- Top scorers, top assists, most cards
- Team stats: possession, shots, xG, pass accuracy per match and cumulative
- Player heatmaps (if shot map data available from BALLDONTLIE)
- xG vs. actual goals chart — which teams are "lucky" or "unlucky"

### 2.2 Differentiation Features (launch in first week)

#### Value Bet Tracker
- Highlights matches where your model's implied probability is >5% different from bookmaker odds
- Explains the reasoning in plain English: "Our model gives France a 72% win probability; Bet365 is offering odds that imply only 65% — that's a potential edge."
- Historical backtest results shown to build trust ("this signal has had X% ROI over 2022 World Cup")

#### Team Deep-Dive Pages
- Nation profile: FIFA ranking, Elo rating, WC history, squad market value (Transfermarkt), top players
- Playing style radar chart: attack vs. defense, tempo, pressing, aerial ability
- Historical WC results going back to first appearance
- Manager profile

#### Player Pages
- Tournament stats: goals, assists, shots, xG, minutes played
- Club season form (from Understat / API-Football) as context
- Prop bet odds where available (Golden Boot market, etc.)

#### Betting Performance Tracker (user feature)
- Users can log bets and track P&L
- Compare their performance to the model's recommendations
- Encourage responsible gambling — show stats like "you've bet X times this week"
- This feature drives return visits and time-on-site

#### Group Stage Permutations Tool
- Interactive: user picks results for remaining group games, site instantly shows what combinations qualify which teams
- Very shareable and high engagement during final group-stage matchday (when all 4 teams play simultaneously)
<!-- 
#### Live Match Dashboard
- Live xG tracker (updating after each shot if API supports)
- Real-time odds movement during matches
- In-play stats: possession, shots, cards, dangerous attacks
- Chat/comment section (optional — adds moderation burden) -->

### 2.3 Content Features (SEO + return visits)

#### Match Previews (automated + editorial)
- Auto-generate base stats preview using your data pipeline
<!-- - Optionally use Claude API to generate readable match preview text from structured data -->
- Publish 24–48 hours before each match for SEO traffic

#### Post-Match Reports
- Auto-generated after final whistle: goals, key moments, xG analysis, "was the result fair?"
- How did the model do? Show the prediction vs. actual result

#### World Cup News Feed
- Aggregate from reputable sources (BBC Sport, ESPN FC, The Athletic RSS)
- Filter by team for personalized experience

<!-- #### Pick 'em Prediction Pool (community feature)
- Free-to-play prediction game: users predict every match result
- Leaderboard, social sharing, prizes (optional)
- Extremely high engagement driver, especially for casual fans -->

<!-- ---

## 3. Monetization Strategy

### Primary: Affiliate Referrals (CPA)
- Place bookmaker links on every odds table, value bet alert, and pre-match page
- Target: DraftKings, FanDuel, BetMGM, Caesars for US users; Bet365, Unibet, William Hill for UK/EU
- Expected CPA: $50–$200 per new depositing customer
- Display 21+ responsible gambling messaging on all affiliate content

### Secondary: Premium Subscription
- Free: match previews, basic stats, predictions
- Premium ($9–15/month or $25 for full tournament): value bet tracker, full historical data, betting tracker, advanced model outputs, no ads
- The WC timing creates urgency — "cancel after the tournament" reduces friction

### Tertiary: Display Advertising
- Google AdSense or direct deals with sports/betting advertisers
- Low CPM but zero marginal effort after setup
- Keep ad density low to preserve UX quality

### Optional: Data API Access
- Sell API access to your model's probability outputs to smaller sites
- Interesting if you build something uniquely accurate -->

---

## 4. Tech Stack Recommendations

### Frontend
- **Streamlit**

### Backend / API
- **Node.js or Python (FastAPI)** — API layer that aggregates data sources
- **PostgreSQL (Supabase)** — match data, historical stats, user accounts
- **Redis (Upstash)** — live odds cache, live score cache (TTL = 15s during matches)
- **Background jobs (cron):** pull odds every 15–60s during live matches, daily for pre-match

### Data Pipeline
- Python scripts for bulk historical load (football-data.co.uk CSVs, Understat scrape)
- API wrappers for: BALLDONTLIE, API-Football, OddsPapi, The Odds API
- Model inference: FastAPI endpoint serving predictions as JSON

<!-- ### Auth & User Features
- **Clerk or Supabase Auth** — user accounts for betting tracker, pick 'em game
- **Posthog** — analytics (free tier) — understand which features users actually use

### Infrastructure
- MVP: Vercel (frontend) + Supabase (DB + auth) + Railway or Render (background jobs)
- Total cost: ~$0–50/month for early traffic; scales economically -->

---

<!-- ## 5. SEO Strategy

The tournament produces massive search traffic. Capture it with:

1. **Individual match pages** for all 104 games, pre-optimized with fixture titles like "USA vs Portugal World Cup 2026 Prediction and Odds" — these rank well because they're time-specific
2. **Team pages** — "Brazil World Cup 2026: Squad, Predictions, Odds, History"
3. **Bracket tracker** — people search "World Cup 2026 bracket" hundreds of thousands of times per day during knockout rounds
4. **Group standings** — same high-volume search
5. **Value bet / prediction content** — targets the sharper audience

Use **automated page generation** from your database — 104 match pages, 48 team pages, plus daily updated content pages, can all be generated from templates. Focus editorial effort on the biggest matches (USA games especially, given host nation status).

--- -->

## 6. Launch Timeline

| Week | Milestone |
|---|---|
| Now (May 2026) | MVP: live scores, group standings, basic match pages, odds table |
| June 11 (Tournament starts) | Pre-match analysis pages live for Day 1 matches; affiliate links active |
| June 13–20 (Group Stage Week 1) | Model predictions live; value bet tracker; automated match previews |
| June 26 (Final group matches) | Group permutations tool; pick 'em game with leaderboard |
| June 29 (Round of 16) | Tournament simulator; refined model (trained on group stage results) |
| July 4–19 (Quarterfinals – Final) | Full premium tier; betting tracker; post-match reports; social sharing |

Even an MVP launched June 11 can capture meaningful traffic and affiliate conversions during the tournament.
