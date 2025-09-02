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


### Databases Used

_Insert database used here_
+ **Relational DB**: Postgres (version...)

    + **DB Name** - Lead Gen
    + **DB Tables** - Companies, People
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

        + Funding - 
            + **From the single enrichment API -** company_id, funding_event_id, date, type, investors, amount, currency, news_url, created_at, updated_at

        + Metadata - 
            + Source (where the data was fetched i.e. TechCrunch)
            + Type of data i.e. funding, hiring or event

+ **Graph DB**: _To Be Determined_

+**[BACKLOG ITEM] Normalized data before enrichment**: Add normalized data but not enriched just to track any failures in enrichment 

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

+ Cache results so that the next round of sitemap traversal doesn't start from the top but from the most recent one.

+ See if I can get event attendees on eventbrite

+ Create queue and push ingestion data

+ Fetch from google news

+ Normalize data