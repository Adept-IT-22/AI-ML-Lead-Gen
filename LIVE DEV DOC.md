# Live Development Document

This document is an ever growing embodiment of the project. It contains details about the rationale behind technical decisions, changes made, links to relevant documents, etc.

## Design Choices

_Insert design choices here_

## Technical Decisions

### Languages Used

+ **Backend** - Python for its wealth of useful libraries and lack of learning curve due to developer knowledge. Flask for how lightweight it is.
+ **Frontend** - Angular.

### Packages Used

### Technologies Used

+ **Message Queues** - For their ability to decouple modules, allowing asynchronous operations.
+ **Async/Await** - To prevent network requests blocking the program as this code is network intensive
+ **XML Parsing** - As sitemaps are done in XML. Done using lxml as it's faster than BeautifulSoup due to its dependencies on C library's under the hood.
+ 

### Databases Used

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