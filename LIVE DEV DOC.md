# Live Development Document

This document is an ever growing embodiment of the project. It contains details about the rationale behind technical decisions, changes made, links to relevant documents, etc.

## Design Choices

### Frontend

### Backend

+ **Event-Driven Architecure** - A signal from funding, events or hiring sites is the trigger for everything else. Queues will be placed in between modules for decoupling purposes, allowing the CPU dependent modules to keep executing even when the slower I/O dependent modules are stil running.

+ **Data Oriented Design** - Of key importance is the data and the transformations being made on said data. Everything else is secondary to that. An example of how that is made manifest in this project is through the use of **Structure of Arrays** over **Array of Structures** i.e.

```
founder_data = {
    "urls": ["www.google.com", "www.facebook.com", "www.twitter.com"],
    "founders": ["sergey brin", "mark zuckerberg", "jack dorsey"]
}
```

over:

```
founder_data = [
    {
        "url": "www.google.com",
        "founder": "sergey brin"
    },
    {
        "url": "www.facebook.com",
        "founder": "mark zuckerberg"
    },
    {
        "url": "www.twitter.com",
        "founder": "jack dorsey"
    }
]
```

That is because:

+ We rarely ,if ever, only need one of anything e.g. just one url or just one founder. Normally we need all of them so we can iterate over them and perform some operation. It therefore makes sense to group them together in the former rather than the latter manner.

+ More importantly, the CPU loves sequential data. Iterating over data that's been linearly arranged is what the CPU's dreams are made of. This is due to the cache system in modern computers. Linearly arranged data, e.g. all founders being placed together in one array, can be fetched from memory and fixed in the cache making the CPU's work much easier as opposed to all founders being in different dictionaries and thus non-linear memory locations.

## Technical Decisions

### Languages Used

+ **Backend** - Python for its wealth of useful libraries and lack of learning curve due to developer knowledge. Flask specifically for how lightweight it is. As it's not a compiled language, Python sacrifices speed but the pros in this scenario outweigh the cons.

+ **Frontend** - Angular. This one was purely down to individual taste.

### Packages Used

+ **asyncio** - This package is the lifeblood of this project. Due to the project's I/O heavy nature, coroutines are of the utmost importance, allowing the program to avoid blocking any and everywhere. Everything must be asynchronous.
+ **lxml** - For parsing of xml and html documents. Preferred over BeautifulSoup due to it's superior performance as it depends on C libraries under the hood as opposed to BeautifulSoup which deals solely with Python.
+ **httpx** - For making network requests. Preferred over the more common requests package due to its support for asynchronous calls.
+ **Tenacity** - Ensuring calls to Gemini's API retry if encountered with a ResourceExhaustedException 

### Technologies Used

+ **Message Queues** - For their ability to decouple modules, allowing asynchronous operations.
+ **Async/Await** - To prevent network requests blocking the program as this code is network intensive
+ **XML Parsing** - As sitemaps are done in XML. Done using lxml as it's faster than BeautifulSoup due to its dependencies on C library's under the hood.
+ **Gemini 2.5 Flash** - AI model used to go through paragraphs and extract meaningful based on the data structures in the utils folder.
+ **Semaphores** - Used while making API calls to Gemini to ensure only 4 concurrent request can be made in an attempt to avoid the ResourceExhaustedException.
    + **PS: FOR THE SECTION BELOW INCLUDE YOUR APIKEY IN THE REQUEST HEADER, NOT THE URL**
+ **Apollo Organization Search API** - Used to get a company's website which we will use to enrich that company's data
+ **Apollo Bulk Organization Enrichment API** - Used to enrich 10 companies at a time. This means less network overhead due to reduced network requests
+ **People Search** - Used to search for people from a particular organization
+ **Apollo Bulk People Enrichment** - Used to get people's emails and phone numbers. **REMEMBER TO USE THE `reveal_personal_emails` and `reveal_phone_number` PARAMETERS**
+ **SendGrid** - Used for email outreach. SendGrid returns webhooks tracking email events. Below is the mapping we'll use between events and the contacted_status_enum we'll be using to store a lead's contacted_status. The events are the keys, the enum values are the values to the 'status' key. Each enum has a precedence, so that if multiple people from the same company get emailed, we only preserve the higher precedence state e.g. If person A opens but person B doesn't, we'll register that the email was opened.

    EVENT_STATUS_MAP = {
        "processed": {"status": "pending", "precedence": 2},
        "delivered": {"status": "contacted", "precedence": 3},
        "open": {"status": "contacted", "precedence": 3},
        "click": {"status": "engaged", "precedence": 4},
        "bounce": {"status": "failed", "precedence": 1},
        "spamreport": {"status": "failed", "precedence": 1},
        "unsubscribe": {"status": "opted_out", "precedence": 5}, # A terminal status
        "dropped": {"status": "failed", "precedence": 1},
        "deferred": {"status": "pending", "precedence": 2},
    }


### Databases Used

_Insert database used here_
+ **Relational DB**: Postgres (version...)

    + **DB Name** - Lead Gen
    + **DB Tables** - Companies, People, (normalized_master, normalized_funding, normalized_events, normalized_hiring => these are to check which companies get fetched and normalized but not enriched)
    + **DB Columns per Table**
        + Companies - 
            + id
            + **From the org search API -** organization_headcount_six_month_growth, organization_headcount_twelve_month_growth
            + **From the bulk enrichment API -** apollo_id, name, website_url, linkedin_url, phone, founded_year, market_cap, industries, estimated_num_employees, keywords, city, state, country, short_description, 
            + **From the single enrichment API -** total_funding, technology_names, annual_revenue
            + **Others -** created_at, updated_at, icp_score, contacted_status, notes

        + People - 
            + id
            + **From the people search API -** apollo_id, first_name, last_name, full_name, linkedin_url, title, email_status, headline, city, state, country, organization_id, seniority, departments, subdepartments, seniority, functions
            + **From the people enrichment API -** email, number 
            + **Others -** created_at, updated_at, contacted_status, notes

+ **Graph DB**: _To Be Determined_

#### Scoring Logic

+ Scoring categorises leads based on how closely they match our ICP on a **0–100 scale** (0 = no fit, 100 = perfect fit).
+ The score is a **weighted average of all available dimensions**. If data for a dimension is missing, that dimension is **excluded** from the calculation — it is never assigned a default value, preventing incomplete data from distorting the result.

#### Dimension Weights

| Dimension      | Weight | Rationale |
|----------------|--------|-----------|
| Geography      | 30%    | Determines outsourcing culture and strategic market priority |
| Funding Stage  | 20%    | Indicates available budget and likelihood of outsourcing |
| Employee Count | 15%    | Smaller teams are more dependent on external partners |
| Company Age    | 15%    | Younger companies are more flexible and outsourcing-ready |
| Industry       | 15%    | Some sectors naturally rely more on outsourcing |
| Keywords       | 5%     | Early indicators of outsourcing or distributed work behaviour |

#### 1. Geography (30%)

| Tier | Countries | Score |
|------|-----------|-------|
| Primary Markets | United Kingdom, Ireland, Netherlands, Germany | 100 |
| Eastern European Wedge | Albania, Bulgaria, Romania, Poland, Croatia, Czech Republic, Hungary, Slovakia, Slovenia, Estonia, Latvia, Lithuania, Bosnia & Herzegovina, Kosovo, Montenegro, North Macedonia, Serbia, Ukraine, Denmark, Norway, Finland, Sweden | 85 |
| North America | United States, Canada | 60 |
| Rest of Western Europe | All other European countries | 50 |
| Outside Target Regions | All other regions | 0 |

Eastern Europe is a critical bridge market — Western Europe outsources to Eastern Europe, which subcontracts further to lower-cost regions. This makes it both a direct client source and a channel into larger Western European deals.

#### 2. Funding Stage (20%)

| Stage | Score | Interpretation |
|-------|-------|----------------|
| Series A | 100 | Strong budget + high outsourcing likelihood |
| Seed | 90 | Actively scaling; frequently outsource |
| Pre-seed | 50 | Early stage; mixed outsourcing behaviour |
| Grant-funded | 40 | Budget exists but constrained |
| Bootstrapped | 30 | Cost-sensitive; lower outsourcing probability |
| Series B | 10 | More likely to build internal teams |

#### 3. Employee Count (15%)

| Employees | Score | Interpretation |
|-----------|-------|----------------|
| 6–15 | 100 | Ideal outsourcing sweet spot |
| 1–5 | 80 | Very early-stage; high dependency on external help |
| 16–20 | 70 | Still lean and outsourcing-friendly |
| 21–50 | 40 | Increasing internal capability |
| 51–100 | 20 | Mostly internalised operations |
| 100+ | 0 | Outside target ICP |

#### 4. Company Age (15%)

| Age | Score | Interpretation |
|-----|-------|----------------|
| 0–2 years | 100 | Highly flexible, actively building vendors |
| 3–5 years | 70 | Growth stage; still open to outsourcing |
| 6–10 years | 50 | Established but selective |
| 11–20 years | 30 | Mature; existing vendor lock-in likely |
| 20+ years | 0 | Low priority |

#### 5. Industry (15%)

| Tier | Industries | Score |
|------|------------|-------|
| Tier 1 | Fintech, E-commerce, SaaS, Information Technology | 100 |
| Tier 2 | Healthtech, Marketplaces, Insurtech | 70 |
| Tier 3 | Education, Government, Manufacturing | 30 |
| Unclassified | Any other industry | 0 |

#### 6. Keywords (5%)

A lightweight signal layer detecting early signs of outsourcing readiness.

| Signal Type | Score | Examples |
|-------------|-------|---------|
| Outsourcing intent | 100 | outsource, vendor, agency, contract |
| Remote/distributed work | 70 | remote team, distributed team, async |
| Generic tech language | 30 | general business or software terminology |

#### How to Read the Final Score

Leads with a score of **60+** are classified as an **MQL (Marketing Qualified Lead)** and prioritised for outreach.

#### Coming Next — Outsourcing Likelihood Signals (Behaviour-Based Layer)

The next phase will move the system from static company profiling to behavioural prediction. Planned signals:

+ **Job Posting Analysis** — detecting companies hiring for roles typically outsourced (e.g. QA, data entry, dev support)
+ **Team Structure Signals** — identifying companies without internal engineering or operations depth
+ **External Platform Usage** — detecting usage of Upwork, Fiverr, or similar outsourcing platforms
+ **Funding Recency** — prioritising companies that have recently raised capital and are under growth pressure
        
### Commit Message Format

Commit messages should have the following format:
+ feat: new feature (minor bump)
+ fix: bug fix (patch bump)
+ feat!: breaking change (major bump)
+ docs: documentation
+ chore: maintenance
+ test: tests
+ refactor: code refactoring
+ perf: performance improvement

## Change History

_Insert change history here_

## Relevant Links 

+ [Github Repo](github.com/adept-it-22/ai-ml-lead-gen)
+ [System Architecture](./SYS-ARCHITECTURE.md)

### To-Do

This section is a to-do list for me as the programmer.

+ See if I can get event attendees on eventbrite
+ Fix keyword scoring to only include services we provide
+ Check if funded company is hiring and if hiring company has been funded
+ Implement drip feeding
+ Migrate from sendgrid to apollo
+ Integrate with odoo

+ Nodesk, working_nomads => Unknown company name

