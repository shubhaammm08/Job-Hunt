"""Intelligent Role Classification & Taxonomy Layer for Shubham's JobHunt.

Provides multi-family classification, skill matching, negative-match guardrails,
and experience extraction.
"""
from __future__ import annotations

import re
from typing import Any

# -----------------------------------------------------------------------------
# Complete 12-Family Target Role Taxonomy (Additive & Comprehensive)
# -----------------------------------------------------------------------------
ROLE_TAXONOMY: dict[str, list[str]] = {
    "AI_CORE": [
        "AI Engineer", "Applied AI Engineer", "AI/ML Engineer", "ML Engineer",
        "Machine Learning Engineer", "Applied Machine Learning Engineer",
        "AI Research Engineer", "AI Research Scientist", "AI Scientist",
        "Machine Learning Scientist", "AI Software Engineer", "AI Product Engineer",
        "AI Systems Engineer", "AI Developer", "Machine Learning Developer",
        "ML Developer", "Artificial Intelligence Engineer", "Artificial Intelligence Developer"
    ],
    "GENAI_AGENTIC": [
        "GenAI Engineer", "Generative AI Engineer", "Generative AI Developer",
        "GenAI Developer", "LLM Engineer", "Large Language Model Engineer",
        "LLM Developer", "LLM Application Engineer", "LLM Application Developer",
        "Agentic AI Engineer", "Agentic AI Developer", "AI Agent Engineer",
        "AI Agent Developer", "Agent Engineer", "Agent Developer",
        "AI Agents Engineer", "AI Workflow Engineer", "Agentic Workflow Engineer",
        "RAG Engineer", "RAG Developer", "Retrieval Engineer", "MCP Engineer",
        "MCP Developer", "Model Context Protocol Engineer", "AI Automation Engineer",
        "AI Automation Developer", "Intelligent Automation Engineer",
        "AI Application Engineer", "GenAI Application Engineer",
        "Conversational AI Engineer", "Conversational AI Developer", "Prompt Engineer",
        "AI Evaluation Engineer", "LLM Evaluation Engineer", "AI Quality Engineer",
        "AI Safety Engineer"
    ],
    "DEPLOYMENT": [
        "Forward Deployed Engineer", "FDE", "AI FDE", "Forward Deployed AI Engineer",
        "Forward Deployed Software Engineer", "AI Deployment Engineer",
        "AI Deployment Developer", "Deployment Engineer", "Strategic Deployment Engineer",
        "Deployment Strategist", "AI Deployment Strategist", "AI Implementation Engineer",
        "AI Implementation Specialist", "AI Deployment Specialist", "AI Integration Engineer",
        "AI Integration Specialist", "AI Solutions Engineer", "AI Solutions Architect",
        "Applied AI Architect", "AI Implementation Consultant", "AI Technical Consultant",
        "Technical Solutions Engineer", "Solutions Engineer", "Solutions Architect",
        "Customer AI Engineer", "Customer Solutions Engineer", "AI Customer Engineer",
        "Technical Implementation Engineer"
    ],
    "DATA": [
        "Data Engineer", "Data Engineering", "Junior Data Engineer", "Associate Data Engineer",
        "Analytics Engineer", "Data Analytics Engineer", "Analytics Developer",
        "Data Analyst", "Junior Data Analyst", "Associate Data Analyst",
        "Business Intelligence Analyst", "BI Analyst", "BI Developer",
        "Business Intelligence Developer", "Data Scientist", "Junior Data Scientist",
        "Associate Data Scientist", "Applied Data Scientist", "Machine Learning Data Scientist",
        "Product Analyst", "Product Data Analyst", "Business Analyst", "Data Business Analyst",
        "Decision Scientist", "Decision Analyst", "Data Visualization Analyst",
        "Reporting Analyst", "Quantitative Analyst", "Analytics Consultant", "Data Consultant"
    ],
    "SOFTWARE": [
        "Software Engineer", "Software Developer", "Software Development Engineer",
        "SDE", "SDE I", "SDE 1", "Junior Software Engineer", "Associate Software Engineer",
        "Graduate Software Engineer", "Entry Level Software Engineer", "Backend Engineer",
        "Backend Developer", "Backend Software Engineer", "Python Developer",
        "Python Engineer", "Python Backend Developer", "Python Backend Engineer",
        "AI Backend Engineer", "AI Backend Developer", "AI Software Engineer",
        "Application Engineer", "Application Developer", "Software Application Engineer",
        "Full Stack Developer", "Full Stack Engineer", "Web Application Engineer",
        "API Engineer", "API Developer", "Integration Engineer", "Integration Developer",
        "Platform Software Engineer"
    ],
    "PLATFORM": [
        "AI Platform Engineer", "AI Platform Developer", "AI Systems Engineer",
        "AI Infrastructure Engineer", "AI Infrastructure Developer",
        "Machine Learning Platform Engineer", "ML Platform Engineer",
        "ML Infrastructure Engineer", "ML Infrastructure Developer", "MLOps Engineer",
        "MLOps Developer", "Machine Learning Operations Engineer", "Platform Engineer",
        "Platform Developer", "Infrastructure Engineer", "Infrastructure Developer",
        "Cloud Engineer", "Cloud Developer", "Cloud Infrastructure Engineer"
    ],
    "CLOUD_DEVOPS": [
        "DevOps Engineer", "DevOps Developer", "Junior DevOps Engineer",
        "Associate DevOps Engineer", "Cloud Engineer", "Cloud Infrastructure Engineer",
        "Cloud Developer", "Cloud Platform Engineer", "DevSecOps Engineer",
        "DevSecOps Developer", "Site Reliability Engineer", "SRE", "Junior SRE",
        "Reliability Engineer", "Infrastructure Engineer", "Infrastructure Software Engineer"
    ],
    "AUTOMATION": [
        "Automation Engineer", "Automation Developer", "AI Automation Engineer",
        "AI Automation Developer", "Intelligent Automation Engineer",
        "Intelligent Automation Developer", "Process Automation Engineer",
        "Process Automation Developer", "Workflow Automation Engineer",
        "AI Workflow Automation Engineer", "RPA Developer", "RPA Engineer",
        "Robotic Process Automation Engineer"
    ],
    "SECURITY": [
        "Cybersecurity Analyst", "Security Analyst", "Junior Security Analyst",
        "Security Engineer", "Cybersecurity Engineer", "AI Security Engineer",
        "AI Security Analyst", "Application Security Engineer",
        "Application Security Analyst", "Cloud Security Engineer", "Cloud Security Analyst",
        "DevSecOps Engineer"
    ],
    "QA_TESTING": [
        "QA Engineer", "QA Analyst", "QA Automation Engineer", "QA Automation Developer",
        "Test Automation Engineer", "Test Automation Developer", "Software Test Engineer",
        "Software Test Analyst", "SDET", "Software Development Engineer in Test",
        "AI Testing Engineer", "AI Quality Engineer", "Automation Test Engineer"
    ],
    "PRODUCT_TECH": [
        "AI Product Engineer", "Product Engineer", "Technical Product Engineer",
        "Technical Solutions Engineer", "Solutions Engineer", "Solutions Architect",
        "Technical Architect", "Technical Consultant", "Technology Consultant",
        "Implementation Engineer", "Implementation Specialist", "Integration Engineer",
        "Technical Integration Engineer"
    ],
    "OTHER_TECH": [
        "Technical Support Engineer", "Application Support Engineer",
        "Production Support Engineer", "Systems Engineer", "Systems Developer",
        "Computer Systems Engineer", "Technical Operations Engineer"
    ]
}

# -----------------------------------------------------------------------------
# Guardrails: Explicit False Positives
# (Non-software disciplines that should NEVER automatically match)
# -----------------------------------------------------------------------------
FALSE_POSITIVE_PATTERNS = [
    r"\bdata\s*center\b",
    r"\bdatacenter\b",
    r"\belectrical\s+engineer\b",
    r"\bmechanical\s+engineer\b",
    r"\bcivil\s+engineer\b",
    r"\bchemical\s+engineer\b",
    r"\bhardware\s+(?:design\s+)?engineer\b",
    r"\bstructural\s+engineer\b",
    r"\bfacilities\s+engineer\b",
    r"\bsales\s+engineer\b",
    r"\bfield\s+service\s+engineer\b",
    r"\bpetroleum\s+engineer\b",
    r"\baerospace\s+engineer\b",
    r"\bautomotive\s+engineer\b",
    r"\bmanufacturing\s+engineer\b",
    r"\boptical\s+engineer\b",
    r"\bclinical\s+engineer\b",
    r"\btechnician\b"
]

# -----------------------------------------------------------------------------
# Technology & Skill Lexicon
# -----------------------------------------------------------------------------
TECH_SKILLS = [
    "python", "sql", "power bi", "tableau", "pandas", "numpy", "scikit-learn",
    "machine learning", "deep learning", "nlp", "llm", "rag", "langchain",
    "llamaindex", "gemini", "openai", "agentic", "agents", "mcp", "n8n",
    "docker", "kubernetes", "fastapi", "flask", "django", "pytorch",
    "tensorflow", "mysql", "postgresql", "mongodb", "etl", "data pipeline",
    "aws", "gcp", "azure", "git", "rest api", "spark", "kafka", "dbt",
    "selenium", "playwright", "pytest", "devops", "ci/cd", "linux"
]

EXPERIENCE_PATTERNS = [
    (r"\b(\d+)\s*[-–to]+\s*(\d+)\s*(?:years?|yrs?)\b", "{0}–{1} years"),
    (r"\b(\d+)\+?\s*(?:years?|yrs?)\s+of\s+experience\b", "{0}+ years"),
    (r"\bexperience:\s*(\d+)\s*(?:years?|yrs?)\b", "{0} years"),
    (r"\b(?:fresher|new\s*grad(?:uate)?|entry\s*level|intern(?:ship)?)\b", "0–1 years"),
]


def compile_role_regex(role_name: str) -> re.Pattern:
    """Compile role into word-bounded, case-insensitive regex."""
    clean = re.escape(role_name).replace(r"\ ", r"\s+").replace(r"\/", r"[\/\s]+")
    return re.compile(rf"\b{clean}\b", re.IGNORECASE)


COMPILED_ROLES = {
    family: [(role, compile_role_regex(role)) for role in roles]
    for family, roles in ROLE_TAXONOMY.items()
}
COMPILED_FALSE_POSITIVES = [re.compile(p, re.IGNORECASE) for p in FALSE_POSITIVE_PATTERNS]


def extract_experience(text: str) -> str:
    """Extract required experience from title or description snippet."""
    for pattern, fmt in EXPERIENCE_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            groups = m.groups()
            return fmt.format(*groups)
    return ""


def classify_job(title: str, description: str = "", requirements: str = "") -> dict[str, Any]:
    """Multi-family intelligent classification for a job posting.
    
    Returns:
        matched_roles: list[str]
        role_families: list[str]
        role_confidence: float (0.0 to 1.0)
        matched_skills: list[str]
        experience_required: str
        is_false_positive: bool
    """
    clean_title = (title or "").strip()
    full_text = f"{clean_title} {description} {requirements}".lower()

    # 1. Guardrail check
    for fp in COMPILED_FALSE_POSITIVES:
        if fp.search(clean_title):
            return {
                "matched_roles": [],
                "role_families": [],
                "role_confidence": 0.0,
                "matched_skills": [],
                "experience_required": "",
                "is_false_positive": True
            }

    matched_roles: list[str] = []
    role_families: list[str] = []
    title_matches = 0

    # 2. Match roles across taxonomy
    for family, role_tuples in COMPILED_ROLES.items():
        family_matched = False
        for role_name, reg in role_tuples:
            if reg.search(clean_title):
                matched_roles.append(role_name)
                family_matched = True
                title_matches += 1
            elif description and reg.search(description[:800]):
                # weaker match in opening description
                if role_name not in matched_roles:
                    matched_roles.append(role_name)
                    family_matched = True
        if family_matched:
            role_families.append(family)

    # 3. Matched skills
    matched_skills = [
        skill for skill in TECH_SKILLS
        if re.search(rf"\b{re.escape(skill)}\b", full_text, re.IGNORECASE)
    ]

    # 4. Confidence calculation
    if title_matches > 0:
        confidence = min(0.98, 0.70 + (title_matches * 0.08) + min(len(matched_skills) * 0.03, 0.20))
    elif matched_roles:
        confidence = min(0.85, 0.50 + min(len(matched_skills) * 0.05, 0.35))
    else:
        confidence = 0.0

    exp_req = extract_experience(f"{clean_title} {description[:1200]}")

    return {
        "matched_roles": matched_roles[:6],
        "role_families": role_families,
        "role_confidence": round(confidence, 2),
        "matched_skills": matched_skills[:12],
        "experience_required": exp_req,
        "is_false_positive": False
    }
