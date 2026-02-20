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

### Scoring Logic
+ Scoring will allow us to categorize leads based on how closely they match our ICP. Below is the criteria to be used:
+ Scoring is done on a 0–100 scale with 0 being terrible and 100 being perfect.
+ Keywords are specifically scored based on their alignment to the tasks
we currently offer. Lower level tasks e.g. data labeling, curation, verification and higher level tasks e.g. knowledge management, security and compliance etc, are both ranked. The result is anlayzed based on:

|                              | High Higher-Level Score                                      | Low Higher-Level Score                                                                 |
|------------------------------|-------------------------------------------------------------|---------------------------------------------------------------------------------------|
| **High Lower-Level Score**    | Strategic Partner: An ideal customer today that is also a good fit for future products. | Perfect Fit: An immediate, high-value lead that aligns directly with your current offerings. |
| **Low Lower-Level Score**     | Market Watch: A company you should monitor. They are building complex systems, but not with your foundational approach. | Not a Fit: This company is likely too early-stage or focused on problems outside of your expertise. |

+ Below is the scoring criteria:

    ### Tier 1 Criteria

    **1. Geography (20%)**

    Europe / North America → 100

    Elsewhere → 0.

    **2. Keywords Match (30%)**

    Strong match → 100 

    Medium match → 60 

    Weak match → 20 

    ### Tier 2 Criteria

    **3. Age (15%)**

   Ideal: founded ≤ 1 year ago → 100 points

    Scale down linearly to 0 at >10 years.

    e.g. 1 year → 100, 2 years → 80, 5 years → 60, 8 years → 40, 10 years → 20

    **4. Employee Count (15%)**

    Ideal: ≤ 5 employees → 100 points

    Scale down to 0 at >100

    5 employees → 100, 10 → 80, 20 → 60, 40 → 40, 80 → 20, 100 → 10.

    **5. Funding Stage (10%)**

    This is binary. If the stage is there, 100. If not, 50.

    **6. Contactability (10%)**

    Email - 100

    Linkedin - 80

    **Final Score**

    Score = 0.15(Age) + 0.15(Employees) + 0.1(Funding Stage) + 0.3(Keywords) + 0.1(Contactability) + 0.2(Geography)
        
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


+ **Add to DB**
+ ALTER TABLE mock_companies ADD COLUMN painpoints text[];
+ ALTER TABLE mock_normalized_funding ADD COLUMN painpoints text[];
+ ALTER TABLE mock_normalized_hiring ADD COLUMN painpoints text[];
+ CREATE TYPE company_service AS ENUM ('ai/ml', 'software development international');
+ ALTER TABLE mock_companies ADD COLUMN service company_service;

+ CREATE TABLE mock_company_notes ( 
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id INTEGER REFERENCES mock_companies(id),
    note TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);