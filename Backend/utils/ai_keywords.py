# This dictionary structures keywords into categories with a single score per category.
# The scores reflect the priority: higher scores for lower-level, core tasks.

marking_scheme_keywords = {
    "lower": {
        "data_labeling_and_annotation": {
            "keywords": [
                "ai training data", "data tagging", "semantic segmentation",
                "object detection", "image annotation", "video annotation",
                "text classification", "sentiment analysis labeling",
                "lidar data annotation", "audio transcription and labeling",
                "medical record categorization", "medical image annotation"
            ],
            "score": 100
        },
        "data_verification_and_validation": {
            "keywords": [
                "data coverage", "automated validation workflows", "automated testing",
                "automated design review", "documentation discrepancy detection",
                "regulatory compliance checks", "ai model validation",
                "documentation analysis", "medical record review software",
                "regulatory audit readiness", "regulatory audit trail automation",
                "automated risk assessment for ai", "ai-driven risk analysis"
            ],
            "score": 95
        },
        "data_curation_and_management": {
            "keywords": [
                "data management", "client record organization", "knowledge management",
                "knowledge base automation", "engineering knowledge management",
                "engineering knowledge centralization", "ai knowledge base",
                "knowledge hydration", "data curation", "case load management",
                "client data management", "knowledge discovery"
            ],
            "score": 90
        },
        "data_processing": {
            "keywords": [
                "data enrichment", "data unification", "data silos consolidation",
                "data integration", "data foundation", "data analysis",
                "real-time data", "real-world data", "multimodal input processing",
                "multimodal inputs", "contextual ai", "medical data processing",
                "medical data summaries", "structured data assets",
                "legacy data utilization", "data pipelines",
                "scalable data platforms", "data assessment"
            ],
            "score": 80
        },
        "transcription_and_reporting": {
            "keywords": [
                "meeting transcription", "real-time transcription",
                "meeting transcription accuracy", "video and audio streams",
                "on-the-fly transcription", "multilingual transcription",
                "speaker diarization", "automated report generation",
                "meeting notes", "case summary generation", "case timeline creation",
                "medical record timeline", "automated compliance reporting",
                "transcription"
            ],
            "score": 75
        },
        "workflow_and_task_automation": {
            "keywords": [
                "workflow automation", "business process automation",
                "operational efficiency", "task automation", "automated calculations",
                "automated design suggestions", "repetitive task automation",
                "process optimization", "case management automation", "sales automation",
                "support automation", "ai automation", "customer support automation",
                "automated data entry", "automated video editing",
                "automated script and video production", "automated property prospectus",
                "ai backoffice", "compliance automation"
            ],
            "score": 70
        }
    },
    "higher": {
        "advanced_ai_and_robotics": {
            "keywords": [
                "ai robotics platform", "embodied ai", "transformer models",
                "foundation models in robotics", "agent orchestration",
                "real-time skill acquisition", "ai agents", "agentic systems",
                "llm deployment", "llm engineering", "multi-agent systems",
                "multi-agent orchestration", "ai orchestration",
                "ai blueprint analysis", "computer vision models",
                "natural language interface", "ai video generation",
                "ai sharding", "ai hybrid consensus", "ai for cross-chain bridges",
                "ai models for dapps", "ai model tuning", "ai model training",
                "explainable ai", "generative ai for design",
                "digital twin simulation", "reinforcement learning"
            ],
            "score": 25
        },
        "domain_specific_applications": {
            "keywords": [
                "ai in law", "ai for life sciences", "ai for pharma",
                "ai for drug safety", "drug discovery", "clinical trial review",
                "ai in healthcare", "ai for patient data",
                "ai for personal injury law", "legal technology", "ai in hospitality",
                "ai for customer service", "ai in automotive", "ai in retail",
                "ai in insurance", "ai in education", "ai in finance",
                "ai in government", "ai in iot", "ai-powered asset management",
                "ai for hedge funds", "ai for product development", "ai in cad",
                "ai for engineering standards compliance",
                "ai for complex structural analysis", "ai for remote training",
                "ai for sales enablement", "ai for customer support",
                "clinical decision support", "personalized medicine",
                "algorithmic trading", "ai for urban planning"
            ],
            "score": 20
        },
        "strategic_decision_making": {
            "keywords": [
                "decision-making acceleration", "strategic decision-making",
                "decision support", "decision support systems", "decision-grade analysis",
                "ai-enhanced strategic planning", "market thesis validation",
                "market intelligence", "competitive intelligence", "real-time insights",
                "insight generation", "insight synthesis", "actionable intelligence",
                "business intelligence", "analytics", "quantitative analytics",
                "portfolio analytics", "financial services", "asset management",
                "fintech", "risk management", "compliance", "regulatory compliance",
                "securities and commodity contracts intermediation and brokerage",
                "fraud detection", "ai fraud detection", "predictive analytics",
                "market forecasting", "supply chain optimization"
            ],
            "score": 15
        },
        "security_and_compliance": {
            "keywords": [
                "data security", "data privacy", "compliance in ai",
                "security frameworks", "secure workflows", "institutional-grade compliance",
                "hipaa compliance", "ai-powered security", "regulatory compliance",
                "regulatory standards", "regulatory process integration",
                "regulatory approval for samd", "ai governance in healthcare",
                "ai/ml lifecycle compliance", "automated regulatory documentation",
                "regulatory risk assessment"
            ],
            "score": 10
        },
        "knowledge_management_and_research": {
            "keywords": [
                "ai for medical literature", "ai-powered research tools",
                "ai + expert hybrid workflows", "ai-enhanced expert calls",
                "ai for primary research"
            ],
            "score": 5
        }
    }
}
