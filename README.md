# Signal Forge, Robert Kraus Early-Opportunity Intelligence

**Free personal research tool. No Google Sheets, paid APIs, credentials, or paid subscriptions.**

This project contains:

- `index.html`: complete browser app, including a private leads queue, 33 curated interactive signal families, social/forum search lab, evidence vault, status and incumbent checks, and local JSON backups.
- `scripts/discover.py`: public news and social-index discovery scanner, with pre-set queries for SMERF, nonprofits, regional associations, and suitable recurring-event buyers.
- `.github/workflows/scan-and-publish.yml`: is configured to run the scanner **four times per day after you deploy it** and publishes the updated public feed to GitHub Pages.
- `data/signals.json`: initial empty discovery feed, populated by the scheduled scanner after deployment.

## Step A: Use immediately, completely locally

1. Open `index.html` in Chrome or Edge (double-click it).
2. Click **Search lab**, pick a signal and target segment, then click **Generate exact searches**.
3. Launch a browser search on Facebook, LinkedIn, Reddit, or Google. Those networks have restricted public access and cannot reliably be auto-scraped for free.
4. Save potential organizations to **Review queue** and direct source passages to **Evidence vault**.
5. Open **Verify & qualify** and work through eight sourced checks. The app generates search links and requires a source URL for each supported gate.
6. Export a JSON backup after each research session.

Your private review notes remain only in that browser profile. They do not sync automatically across devices and can be lost if browser storage is cleared. Export backups regularly.

## Step B: Make the public-source feed run twice each day for free

GitHub's free public-repo Pages and Actions are a reasonable way to host this **personal internal research utility**. Its *public scanner output* and code will be viewable by other people. **Never put proprietary research, private contact lists, or client notes into the GitHub repository**. Those stay local in the browser.

1. Create a free GitHub account if you don't already have one.
2. Create a new **public** repository named `robert-signal-forge` and select **no** README or starter template.
3. Upload the contents of this ZIP to the repository, keeping the `.github/workflows/` folders intact. Upload `index.html` at the repository root, not inside an extra folder. Use GitHub's **Add file → Upload files**. For hidden `.github` paths, opening the extracted files via the web upload flow may preserve folders; alternatively use GitHub Desktop (free) to commit the extracted folder.
4. Go to **Settings → Pages → Build and deployment → Source: GitHub Actions**.
5. Go to **Actions → Scan public signals and publish Signal Forge → Run workflow** to start the first scan, or wait for the schedule.
6. Once the workflow has succeeded, use **Settings → Pages → Visit site** to open your link.

The scheduled workflow runs at **00:15, 06:15, 12:15, and 18:15 UTC**, approximately every six hours. Daylight saving time shifts those by one hour. GitHub may delay scheduled jobs. GitHub can also disable scheduled workflows in inactive public repositories, so occasionally confirm it is still enabled.

A public-feed scanner is **not** capable of unrestricted 24/7 monitoring. It checks public news feeds and web-indexed social pages four times per day after deployment and you can trigger additional runs manually. Social networks restrict indexing and API access, and some feed requests can fail or be rate-limited. Social index timestamps are not verified original post dates. The app displays the last generated feed timestamp and scanner state. Never assume silence means no prospects exist.

## How results should be interpreted

**The scanner does not qualify anyone.** A discovery is a publicly indexed article or announcement that matches a signal phrase. It might be unrelated, mention a large organization, describe a contracted event, or have no relevance to Robert.

For each discovery, independently verify:

1. Exact legal entity and event organizer, including national vs regional chapter.
2. Latest available annual revenue, ideally **$500,000–$7,000,000**, from a dated tax filing or audited statement. No revenue is guessed by this app.
3. Specific recurring conference and onsite scope, ideally **75–500 attendees** with lodging, vendor contracts, food and beverage, and/or full-service planning needs. Larger events can be considered with support.
4. Genuine early purchasing decision or substantial attendee-experience need, ideally **before** procurement or contract signing.
5. Incumbent event planner, meeting-management firm, host hotel, room block and supplier contracts. Existing planners aren't an automatic disqualifier, but they change Robert's entry strategy.
6. Who controls the budget and decision, and whether outside full-service or independent cost-assessment assistance is possible.
7. Conflicting evidence and missing facts. Only you can mark a record "Research-ready" for Robert.

### Unique signal families

Budget strain; post-event feedback; planning-chair turnover; hotel/venue reconsideration; room-block attrition; sponsor and exhibitor friction; host-hotel renovation; loss of internal event staff; event date/format changes; younger-member disengagement; local-community vendor changes; late registration extensions; new overnight lodging requirements.

### Three plays

- **Safe:** Directly stated contractor/planner need; strong demand signal, but usually later in cycle.
- **Smart:** Multiple early planning-change clues before a formal RFP, verified decision owner.
- **Bold:** Financial or attendee-experience friction where Robert could proactively prove improvement despite no posted procurement need.

## Costs and limitations

- HTML/browser app: **$0**.
- Python scanner: **$0**, uses only Python's standard library.
- GitHub Actions on public repo: generally free subject to GitHub policies, limits, availability, rate restrictions, and usage rules. GitHub Pages is not intended for a paid software service. This is a personal internal research app, not a SaaS platform.
- No paid social API or automated private Facebook/LinkedIn scraping. Social monitoring is via PUBLIC web-index search results only and therefore incomplete.
- Public feed JSON stored in a public repo is not confidential; your local notes are private *to your browser profile*, not encrypted cloud storage.
- After deploying, GitHub Actions provides hosting and scheduled refreshes without keeping your personal computer running.

## Troubleshooting

- **The app opens but no discoveries appear:** In local file mode, the public feed cannot be fetched reliably. Publish the site or use manual Search Lab.
- **Hosted app shows zero discoveries:** Check Actions logs. Some public RSS sources block automated requests or had no matches. Expand queries deliberately rather than adding generic news.
- **Pages action says not configured:** Confirm Pages source is GitHub Actions and repository is public on GitHub Free.
- **Data disappeared:** Restore your most recent exported JSON from Setup & backup.
- **Missing social posts:** Public social indexing is incomplete. Search Lab opens first-party social search pages for manual review.

## Version 1.0 | November 2026


## Version 2.0: guided discovery-to-verification workflow

- Scanner has 41 targeted public-news queries plus approximately 50 rotating targeted public-social-index searches per run, including board debriefs, venue disruptions, sponsor friction, conference staff turnover, social mentions indexed by news/search, and unusual association planning signals.
- Scanner auto-tags a suggested **Safe**, **Smart**, or **Bold** research play and flags hints of already-booked venues or room blocks. These tags are preliminary; the source itself must be examined.
- Every saved candidate now has an **8-step qualification workbench**, with one-click web research links, evidence URLs, limitations, and a next research question. Manually marking a record *Research-ready* is blocked until every step has a supplied source URL. This does NOT automatically qualify a lead.
- When the app is hosted, it automatically refreshes the latest scanner feed every 30 minutes while the tab remains open. The actual scan only happens during scheduled GitHub Actions runs.
- The local file can also connect to a published feed URL under **Setup & backup**, if that public feed permits browser access.
- The ChatGPT twice-daily Robert watch is a **separate notification system**. It does not write results into this app.

**Crucial limitation:** social media sites often block or restrict automated indexing. The scanner runs as often as scheduled but cannot guarantee it discovers all Facebook, LinkedIn, Threads, X, or forum content. The interactive Search Lab remains the fallback.

**Getting live updates:** you must still publish the package to a free GitHub repository and enable its Actions/Pages deployment. Downloading the HTML alone does not create a running web server or scheduled scanner.

## Social Radar upgrade (November 6, 2026)

**What's actually automated:**

- 41 public-news/association search patterns, plus a rotating set of around 50 public web-index searches per scan, focused on **Facebook public pages, LinkedIn public posts, Threads, X, and indexed Reddit discussions**. This is not direct API or logged-in monitoring. The scan source, matching signal family, potential prior commitment and original URL are displayed in Discover.
- **Discover → Social radar (indexed)** isolates indexed social mentions. The timestamp shown is explicitly an *index date*, not verified proof of when someone posted.
- **Search lab** includes 33 hand-curated social/hidden-signal searches and direct inspection links for manual follow-up. These include event committee burnout, sponsor churn, registration stalls, member affordability, venue disruptions, new host cities, leadership resets and post-event feedback.
- **Verify & qualify** has eight evidence-backed gates. The original organization name, revenue, event cycle, incumbent, and decision date must be verified before a recommendation.

**Critical platform restriction:** Reddit officially plans to turn off its RSS feeds **November 13, 2026**. This scanner does not depend on Reddit RSS. It only checks Reddit content visible through a public web search index. Facebook/LinkedIn/Threads/X may hide or delay indexing, so the scanner cannot catch all public mentions. Private groups or restricted posts cannot be monitored without legitimate access.

**Activation is still required:** Neither opening the local HTML nor receiving ChatGPT's separate scheduled notifications activates the GitHub-hosted app's scanner. You must create/upload the repository and enable the GitHub Actions + Pages workflow described in Step B. The scanner's scheduled output is public, while your saved review notes are only in your local browser.

**Accuracy guarantee:** No social indexed snippet is automatically a qualified opportunity. Do not use an RSS `pubDate` or a search-engine crawl time as the original post date.

## Version 2.2: Free automated research assistance (November 6, 2026)

**Added to the scheduled GitHub scanner:** `scripts/enrich.py` runs after `discover.py` and enriches up to six *new* clear-name discoveries per scan, using public ProPublica Nonprofit Explorer API and targeted public-source index queries. It does not require keys or a paid service. The batch limit prevents excessive API requests and reduces source blocking.

- **Revenue/EIN:** Finds an exact and unique legal name match and retrieves the latest available Form 990/990-EZ total revenue. Includes source and fiscal year. This is a preliminary *entity match*, not proof that the nonprofit organized the conference. Any ambiguous chapter/legal name remains unknown. Revenue is not event expenditure.
- **Conference history:** Looks for current and prior years in public indexed event references, with original URLs. The words “2027 annual conference” alone do NOT prove that event occurred, will recur, or has a signed agreement; verify the official event archive and its dates.
- **Existing planner or venue:** Generates source-linked counterchecks for hotel blocks, planner roles, association management companies and named venues. No matches mean “unknown”, not “not contracted”. A source mention is a *clue*, not proof of commitment.
- **Buyer and decision timing:** Searches committee leadership, site selection and contract-deadline language. Any dates or roles in snippets are *unverified* and must be checked in the original announcement; the actual purchasing date stays unknown until verified.
- **Browser:** On discoveries enriched by the latest scan, select **View auto-research** to see available revenue data, earlier/later event references, contract counterchecks and leadership clues in one place. Save the discovery to the private queue for manual verification.

**Activation:** GitHub repository, Actions and Pages still must be deployed and enabled. These files are the working source, not a live hosted or continuously running app. Automatic scanner results are public if hosted in a public repo; personal notes remain stored locally in each browser. The separate ChatGPT 8 AM/6 PM watch is independent and does not feed directly into Signal Forge.

**Coverage is limited:** Search-indexed posts are incomplete; the API does not provide guaranteed current revenue for all non-profits, church congregations are often exempt from filing, and private companies generally do not file Form 990. Those stay manually researched rather than falsely rejected.

## Version 3.1: two automation layers

- **Broad discovery scan:** `scripts/discover.py` searches for overlooked public conference signals. `scripts/enrich_discoveries.py` then performs a limited free nonprofit/EIN lookup and public event-history, planner/hotel and decision-path search for discoveries whose source title starts with a full, explicit association name. In Discover, select **View auto-research** when available. Most social or ambiguous headlines still require manual organizer identification.
- **Focused watchlist scan:** `scripts/enrich.py` reads `watchlist.json`, which is prefilled with three provisional target organization names. It gathers current revenue filing information and indexed source leads for two historical conference-year searches, future event searches, venue/planner counterchecks and leadership/decision-language queries. The **Auto investigations** area in the app shows this feed. Search-result dates are not event dates.
- **Add more watchlist targets:** In the app, add their legal organization name and state in **Auto investigations**, then click **Export watchlist.json**. Replace `watchlist.json` in the GitHub repo with your exported version. The next scheduled scan will investigate them. Adding a record locally **does not** update the public GitHub watchlist automatically. Never include confidential names, notes or client data in this public watchlist.
- **Frequency:** GitHub workflow has four scheduled UTC runs per day, after GitHub Pages/Actions have been deployed. User's separate ChatGPT Robert watch runs 8 AM and 6 PM Central, and does not feed the app.
- **What still requires your judgment:** legal organizer and chapter, accuracy/recurrence of events, whether an incumbent contract is exclusive, decision-maker authority, actual decision date, and whether Robert's fee-based service has a plausible buyer. Any missing source remains **unknown**, never a negative finding or a qualified lead.
- **No live verification performed during packaging:** The current session can run syntax and mock tests, but it cannot reach ProPublica / public RSS endpoints from the local runtime. The first real scan must run in your deployed GitHub Actions account and you should check its log for failures or rate limits.

## Buyer-evidence filtering (v3.1)

The discovery scanner uses three evidence gates before adding anything to the public feed: (1) a recognizable, named association/nonprofit/SMERF organizer; (2) a relevant annual or recurring event; and (3) an explicit event-planning, venue, committee, financial, staffing, attendance, or attendee-feedback **change**. A blog discussing a conference as a topic, a simple event listing, a generic call for speakers, or a dictionary page cannot qualify as a discovery.

Each discovery displays the matching evidence excerpt and a precise next verification question. A review priority is not a purchase probability. The scheduled scanner also removes older false positives from the **public feed** on its next successful scan. Locally saved private leads and evidence are not automatically deleted.

Social coverage is limited to publicly indexed pages. A result is only marked Facebook/LinkedIn/Threads/X/Reddit if the original URL hostname or a Google News source supports that platform. Bing's `site:` query is not always respected; mismatching results are rejected.

What to prioritize: conference-site searches before RFP; annual-event budget and revenue reviews; committee chair or planner changes; attendee complaints about hotel price/format; room-block attrition and F&B minimum pressure; sponsor/exhibitor dissatisfaction; new overnight events; multi-year hotel contract cycles. Always verify venue/planner incumbents and official source dates before contacting anyone.