from scoring_module.keyword_scoring.keyword_scoring import TfIdfScorer
from utils.ai_keywords import marking_scheme_keywords
import json

company_keywords = [
    "integration", "api", "cloud", "hr data", "saas", "enterprise software",
    "b2b", "automation", "gdpr compliance", "hris", "user provisioning",
    "software development", "no-code platform", "automated provisioning",
    "information technology and services", "user-friendly dashboard",
    "employee data integrations", "data synchronization", "employee data management",
    "cloud marketplace", "custom fields support", "data compliance",
    "data security standards", "api connectors", "real-time data sync",
    "workflow automation", "data enrichment", "hr and it automation",
    "automated employee provisioning", "data governance", "integration platform",
    "hipaa compliance", "data security", "data mapping", "multi-source data consolidation",
    "error management", "data audit trail", "integration error alerts",
    "predictive data mapping", "employee lifecycle data", "predictive analytics",
    "employee records automation", "soc2 compliance", "ai-driven insights",
    "vendor requirement matching", "no-code integration", "error handling",
    "security and compliance", "custom calculated fields", "cloud connectors",
    "human resources", "vendor integration", "hr data integration",
    "vendor data sync", "services", "computer systems design and related services",
    "digital transformation", "business intelligence", "computer software",
    "information technology & services", "enterprises", "computer & network security",
    "analytics"
]

scorer = TfIdfScorer(company_keywords, marking_scheme_keywords)
results = scorer.score()
print(json.dumps(results, indent=2))
