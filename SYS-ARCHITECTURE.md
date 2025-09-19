# System Architecture

This document outlines the architecture of a lead generation and enrichment system focused on AI/ML companies. The system is **event-driven**, where each newly ingested piece of data (news article, funding update, job post, or event) triggers a **multi-stage data pipeline**. 

The pipeline is implemented using **data-oriented design** principles, ensuring efficient batch processing and cache locality. Core components include ingestion, normalization, enrichment, graph linking, ICP scoring, and automated outreach. The final goal is not just to collect data, but to enable intelligent and timely engagement with high-value leads.

The dictionary will be the primary data structure.

## Architecture Diagram

![image](./photos/Lead%20Gen%20Sys%20Architecture.png "System Architeture Diagram")

## Data Pipeline

Below are the phases through which data will flow through the system:

+ **Ingestion Phase**
    + Here data is fetched via APIs or scraped from various outlets. The input is raw json, html, xml etc and the output is a dictionary with unclean/unformatted data. This output is passed into a queue (Python's asyncio.queue) from where the next phase will fetch the data.  

    + The queue is important as it decouples this module from the next one allowing them to operate asynchronously.

+ **Normalization Phase**
    + Takes the ingestion phase's output as input and converts it into clean/formated data.

    + The data will again be placed into a queue, decoupling this module from the very I/O heavy enrichment module.

    + Standardization will be done in the following way:

        + Dates - ISO 8601 format (YYYY-MM-DD)
        + Countries - ISO 3166-1 country name
        + Cities - Title cased
        + URLs - stripped of whitespace
        + Tags - lowercase and stripped of whitespace
        + Currencies - ISO 4217

+ **Enrichment Phase**
    + Here the data is fetched from the normalization queue as a clean/formatted dictionary and the company name from the dictionary is used to fetch company details from the Apollo Bulk Organization Enrichment API.
    
    + The output of this phase is a dictionary similar to the one from the normalization phase but with more company information.

+ **Storage Phase**
    + After the data has been enriched it's time for it to be stored. This will be done in a:
        + **Relational Database** - Best for structured, tabular data e.g. company name, company size, funding amount etc.
        + **Graph Database** - Best for making connections e.g. "Who are the CEOs of companies that recently got funding?" 

+ **Linking Phase**
    + Here is where we make use of the above graph database. We form links between people, companies, investors, events, news etc that will provide more information, allowing us to make better decisions.

+ **Scoring Phase**
    + Here data is fetched from the relational database and scored based on our ICP which currently is:
        + **Industry** - AI/ML
        + **Company Size** - <20 employees.
        + **Company Age** - <2 years old.
        + **Funding Stage** - Seed/Pre-Seed 

    + The scoring points will be:
        +  **_To be added later_**

    + This scoring data will be stored in the above relational database.

+ **Outreach Phase**
    + Finally, reaching out to the company/decision maker's email is the end goal of this tool, not just lead generation. This will be done via SendGrid's APIs. Templates will be created and chosen based on the context within which the email is being sent.

    

## Glossary

+ **ICP** - Ideal Customer Profile
+ **Asyncio.Queue** - An in-memory queue provided by Python allowing modules to be decoupled.