# AI/ML Lead Generation System — User Manual

## Table of Contents

1. [Overview](#1-overview)
2. [What the System Does Automatically](#2-what-the-system-does-automatically)
3. [What You Do Manually](#3-what-you-do-manually)
4. [The Dashboard (Frontend)](#4-the-dashboard-frontend)
   - [Home](#41-home)
   - [Leads](#42-leads)
   - [Company Details](#43-company-details)
   - [Analytics](#44-analytics)
   - [Engagement](#45-engagement)
   - [Events](#46-events)
   - [Settings](#47-settings)
5. [The Pipeline & Outreach Schedule](#5-the-pipeline--outreach-schedule)
6. [Outreach](#6-outreach)
7. [Importing & Exporting Leads](#7-importing--exporting-leads)
8. [Understanding ICP Scores](#8-understanding-icp-scores)
9. [Email Tracking & Statuses](#9-email-tracking--statuses)
10. [Glossary](#10-glossary)

---

## 1. Overview

This system is a lead generation and outreach tool targeting **recently funded and/or actively hiring AI/ML companies**, primarily in **Europe and North America**.

The core idea is simple: signals from the outside world (a startup getting funded, a company posting an AI job, an industry event) are automatically detected and converted into qualified, scored leads. The entire process — from discovery through to personalised outreach — runs on a scheduled basis with no manual intervention required.

**Stack at a glance:**

| Layer    | Technology                          |
| -------- | ----------------------------------- |
| Backend  | Python (Flask), asyncio, asyncpg    |
| Frontend | Angular                             |
| Database | PostgreSQL                          |
| Outreach | SendGrid                            |
| AI/LLM   | Google Gemini 2.5 Flash             |
| Data     | Apollo.io (org & people enrichment) |

---

## 2. What the System Does Automatically

The pipeline and outreach both run on a **scheduled cron job** — no manual triggering is needed. The following stages run end-to-end without any input from you:

### Stage 1 — Ingestion

The system scrapes and fetches data from **25+ funding news sources** and **19+ job board sources** simultaneously.

**Funding sources include:** TechCrunch, VentureBeat, EU-Startups, Sifted, TechEU, BetaKit, GeekWire, CB Insights, PR Newswire, and many more.

**Hiring sources include:** Hacker News (Who's Hiring), RemoteOK, Remotive, We Work Remotely, Himalayas, Jobicy, Berlin Startup Jobs, Arc.dev, and others.

**Events sources include:** Eventbrite.

Raw data (JSON, HTML, XML) is placed into an in-memory queue for the next stage.

### Stage 2 — Normalization

Raw data is cleaned and standardised:

- Dates → ISO 8601 (`YYYY-MM-DD`)
- Countries → ISO 3166-1 standard names
- Cities → Title cased
- Currencies → ISO 4217 codes
- Tags and URLs → stripped, lowercased

A second queue passes clean data on to enrichment, decoupling the two stages so neither blocks the other.

### Stage 3 — Enrichment

The system uses the **Apollo.io API** to enrich each company:

- **Bulk Organisation Enrichment** — fetches 10 companies at a time to minimise API overhead (website, LinkedIn, headcount, funding, industry, keywords, description, etc.)
- **Organisation Search** — used when only a company name is known, to find its website URL first
- **People Search** — finds the key decision-makers (founders, C-suite, VPs) at each company
- **People Enrichment** — retrieves verified email addresses and phone numbers for those people

Gemini 2.5 Flash is used during ingestion to extract structured data (company names, funding amounts, hiring roles, pain points) from unstructured article text.

### Stage 4 — Storage

Enriched data is written to **PostgreSQL** across two tables:

- **Companies** — all organisational data plus ICP score and outreach status
- **People** — individual contacts linked to their company

### Stage 5 — Scoring

Every company is automatically scored against your **Ideal Customer Profile (ICP)** on a 0–100 scale. See [Section 8](#8-understanding-icp-scores) for the full scoring breakdown.

### Stage 6 — Outreach

After the pipeline completes, a separate scheduled job handles outreach automatically. For each eligible contact it generates a personalised email using Gemini 2.5 Flash (adapting content based on funding or hiring context), stores the email in the database, and sends it via SendGrid. See [Section 6](#6-outreach) for full details.

### Stage 7 — Email Tracking (Passive, Always On)

Once emails are sent, **SendGrid webhooks** automatically update each lead's `contacted_status` in the database as events come in (delivered, opened, clicked, bounced, unsubscribed, etc.). You do not need to do anything for this to work.

---

## 3. What You Do Manually

The pipeline and outreach run automatically — your role is to **review results, manage leads and handle replies** through the dashboard. The actions below are the only things that require input from you:

| Action                                 | How                                    |
| -------------------------------------- | -------------------------------------- |
| **Import leads from Excel**            | Use the Import button on the dashboard |
| **Export leads to Excel**              | Use the Export button on the dashboard |
| **Add or delete notes** on a company   | Company Details page                   |
| **Mark a lead as replied**             | Company Details page                   |
| **Mark a lead as a positive response** | Company Details page                   |

---

## 4. The Dashboard (Frontend)

### 4.1 Home

The home page displays the full list of discovered companies. Each card shows:

- Company name, location, and industry
- ICP score (colour-coded)
- Current outreach/contact status
- Source of discovery (funding or hiring signal)

You can **search**, **filter** by status or score, and **paginate** through the list. Clicking the "VIEW" button on a lead opens its [Company Details](#43-company-details) page.

### 4.2 Leads

A dedicated full-page leads table with richer filtering options. Useful for bulk review of your pipeline output.

### 4.3 Company Details

Accessed via clicking the **"VIEW"** button on any lead. Shows the full profile of a single company:

- All enriched company data (size, funding round, LinkedIn, website, keywords, etc.)
- List of associated **people** (contacts) with their titles, emails, and contact status
- **Emails** sent to this company (linked to the Emails page)
- **Notes** — you can add, view, and delete freeform notes here

**PS** - Buttons to **mark as replied** or **mark as positive** can be accessed by clicking the **"ACTION"** button

### 4.4 Analytics

Charts and summary statistics about the lead pipeline:

- Score distribution across all companies
- Breakdown by geography, funding stage, and employee size
- Outreach funnel (pending → contacted → engaged → replied → positive)

### 4.5 Engagement

Tracks email outreach performance at an aggregate level:

- Open rates, click rates, bounce rates
- Per-company engagement status
- Ability to manually unsubscribe a contact

### 4.6 Settings

Application-level configuration (pipeline and outreach settings).

---

## 5. The Pipeline & Outreach Schedule

Both the pipeline and outreach run on a **daily automated schedules** — you do not need to trigger either manually.

### Pipeline Schedule

The pipeline runs on its configured schedule and executes the full sequence:

1. All configured funding, hiring, and event sources are scraped concurrently.
2. Raw data flows through normalization.
3. Companies are enriched via Apollo.io.
4. Everything is stored in PostgreSQL.
5. All companies are scored against the ICP.

### Outreach Schedule

Outreach runs **after** the pipeline has completed. It:

1. Fetches all eligible people from the database (those with a verified email address and not yet contacted or opted out).
2. Generates a **personalised email** for each person using Gemini 2.5 Flash. The email content adapts based on:
   - Whether the trigger was a **funding event** or a **hiring signal**
   - The company's description, hiring area (for hiring-sourced leads), and inferred pain points
   - The sequence number (1st contact, 2nd contact, etc.)
3. Stores the drafted email in the database (linked to the company and person).
4. Sends the email via **SendGrid**.

Outreach is kept on a separate schedule from the pipeline deliberately — this ensures companies are fully scored and enriched before any contact is attempted.

### Email Status Lifecycle

| SendGrid Event                      | Status in System                              |
| ----------------------------------- | --------------------------------------------- |
| `processed` / `deferred`            | `pending`                                     |
| `delivered`                         | `contacted`                                   |
| `open`                              | `opened`                                      |
| `click`                             | `engaged`                                     |
| `bounce` / `spamreport` / `dropped` | `failed`                                      |
| `unsubscribe`                       | `opted_out` _(terminal — never re-contacted)_ |

When multiple people at the same company receive emails, the **highest-precedence status** wins for the company-level status.

---

## 7. Importing & Exporting Leads

### Export to Excel

Use the **Export** button in the dashboard. Downloads an `.xlsx` file of all companies currently in the database.

### Import to Excel

Upload a formatted `.xlsx` file to bulk-import leads into the database. Use the **Import** button in the dashboard to do this through the UI. The file format should match the columns in the Companies table (see the architecture document for column definitions).

**NB** - You cannot just import any file as the database has very specific columns. If you'd like to import a file let me know so I can make it possible. Better yet, I can create a template excel file that you can fill data into before importing.

---

## 8. Understanding ICP Scores

Every company is automatically scored on a **0–100 scale** across six dimensions. The higher the score, the stronger the fit and the higher the outreach priority.

> **Important:** If data for a dimension is missing (e.g. funding stage is unknown), that dimension is **excluded** from the calculation rather than assigned a default value. This prevents incomplete data from distorting scores.

### Dimension Weights

| Dimension          | Weight | Why It Matters                                                |
| ------------------ | ------ | ------------------------------------------------------------- |
| **Geography**      | 30%    | Determines outsourcing culture and strategic market priority  |
| **Funding Stage**  | 20%    | Indicates available budget and likelihood of outsourcing      |
| **Employee Count** | 15%    | Smaller teams are more dependent on external partners         |
| **Company Age**    | 15%    | Younger companies are more flexible and outsourcing-ready     |
| **Industry**       | 15%    | Some sectors naturally rely more on outsourcing               |
| **Keywords**       | 5%     | Early indicators of outsourcing or distributed work behaviour |

### Geography (30%)

Geography is the most important factor. It reflects both market strategy and outsourcing ecosystem dynamics.

| Tier                       | Countries                                                                                                                                                                                                                          | Score |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| **Primary Markets**        | United Kingdom, Ireland, Netherlands, Germany                                                                                                                                                                                      | 100   |
| **Eastern European Wedge** | Albania, Bulgaria, Romania, Poland, Croatia, Czech Republic, Hungary, Slovakia, Slovenia, Estonia, Latvia, Lithuania, Bosnia & Herzegovina, Kosovo, Montenegro, North Macedonia, Serbia, Ukraine, Denmark, Norway, Finland, Sweden | 85    |
| **North America**          | United States, Canada                                                                                                                                                                                                              | 60    |
| **Rest of Western Europe** | All other European countries                                                                                                                                                                                                       | 50    |
| **Outside Target Regions** | All other regions                                                                                                                                                                                                                  | 0     |

> **Why Eastern Europe?** Eastern Europe acts as a critical bridge market — Western Europe frequently outsources to Eastern Europe, which in turn subcontracts further to lower-cost regions. This makes it both a direct client source and a channel into larger Western European deals.

### Funding Stage (20%)

| Stage        | Score | Interpretation                                |
| ------------ | ----- | --------------------------------------------- |
| Series A     | 100   | Strong budget + high outsourcing likelihood   |
| Seed         | 90    | Actively scaling; frequently outsource        |
| Pre-seed     | 50    | Early stage; mixed outsourcing behaviour      |
| Grant-funded | 40    | Budget exists but constrained                 |
| Bootstrapped | 30    | Cost-sensitive; lower outsourcing probability |
| Series B     | 10    | More likely to build internal teams           |

### Employee Count (15%)

| Employees | Score | Interpretation                                     |
| --------- | ----- | -------------------------------------------------- |
| 6–15      | 100   | Ideal outsourcing sweet spot                       |
| 1–5       | 80    | Very early-stage; high dependency on external help |
| 16–20     | 70    | Still lean and outsourcing-friendly                |
| 21–50     | 40    | Increasing internal capability                     |
| 51–100    | 20    | Mostly internalised operations                     |
| 100+      | 0     | Outside target ICP                                 |

### Company Age (15%)

| Age         | Score | Interpretation                             |
| ----------- | ----- | ------------------------------------------ |
| 0–2 years   | 100   | Highly flexible, actively building vendors |
| 3–5 years   | 70    | Growth stage; still open to outsourcing    |
| 6–10 years  | 50    | Established but selective                  |
| 11–20 years | 30    | Mature; existing vendor lock-in likely     |
| 20+ years   | 0     | Low priority                               |

### Industry (15%)

| Tier         | Industries                                        | Score |
| ------------ | ------------------------------------------------- | ----- |
| Tier 1       | Fintech, E-commerce, SaaS, Information Technology | 100   |
| Tier 2       | Healthtech, Marketplaces, Insurtech               | 70    |
| Tier 3       | Education, Government, Manufacturing              | 30    |
| Unclassified | Any other industry                                | 0     |

### Keywords (5%)

A lightweight signal layer that detects early signs of outsourcing readiness.

| Signal Type             | Score | Examples                                 |
| ----------------------- | ----- | ---------------------------------------- |
| Outsourcing intent      | 100   | outsource, vendor, agency, contract      |
| Remote/distributed work | 70    | remote team, distributed team, async     |
| Generic tech language   | 30    | general business or software terminology |

### How to Read the Final Score

Leads with a score of **60+** are classified as an **MQL (Marketing Qualified Lead)** and prioritised for outreach.

---

## 9. Email Tracking & Statuses

The `contacted_status` field on each **company** and **person** record tells you exactly where they are in the outreach funnel:

| Status           | Meaning                                           |
| ---------------- | ------------------------------------------------- |
| `null` / not set | Not yet contacted; no email attempted             |
| `pending`        | Email processed or deferred by SendGrid           |
| `contacted`      | Email delivered successfully                      |
| `opened`         | Recipient opened the email                        |
| `engaged`        | Recipient clicked a link in the email             |
| `failed`         | Email bounced, was dropped, or reported as spam   |
| `opted_out`      | Recipient unsubscribed — **do not contact again** |

You can also manually mark leads on the Company Details page:

- **Replied** — the person replied to the email
- **Positive** — the reply was a positive/interested response

---

## 10. Glossary

| Term                 | Definition                                                                  |
| -------------------- | --------------------------------------------------------------------------- |
| **ICP**              | Ideal Customer Profile — the criteria defining your best-fit lead           |
| **Ingestion**        | The process of fetching raw data from external sources                      |
| **Normalization**    | Cleaning and standardising raw data into a consistent format                |
| **Enrichment**       | Augmenting basic company/person data with detailed info from Apollo.io      |
| **asyncio.Queue**    | Python's in-memory queue used to decouple pipeline stages                   |
| **Apollo.io**        | Third-party API used for company and people data enrichment                 |
| **SendGrid**         | Email delivery service used for outreach; provides event webhooks           |
| **Webhook**          | An HTTP callback from SendGrid that notifies the system of email events     |
| **Gemini 2.5 Flash** | Google's AI model used for data extraction and email generation             |
| **Semaphore**        | A concurrency control mechanism limiting simultaneous Gemini API calls to 4 |
| **Drip feeding**     | Sending outreach emails in spaced sequences over time (planned feature)     |
| **Data Source**      | Whether a lead was discovered via a `funding` event or a `hiring` signal    |
