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
        "ML Developer", "Artificial Intelligence Engineer", "Artificial Intelligence Developer",
        "Machine Learning & Python Developer", "ML & Python Developer"
    ],
    "GENAI_AGENTIC": [
        "GenAI Engineer", "Generative AI Engineer", "Generative AI Developer",
        "GenAI Developer", "LLM Engineer", "Large Language Model Engineer",
        "LLM Developer", "LLM Application Engineer", "LLM Application Developer",
        "GenAI & LLM Engineer / Developer (GenAI, LLMs, NLP, LangChain)",
        "GenAI & LLM Engineer", "GenAI & LLM Developer",
        "Agentic AI Engineer", "Agentic AI Developer", "AI Agent Engineer",
        "AI Agent Developer", "Agent Engineer", "Agent Developer",
        "AI Agents Engineer", "AI Workflow Engineer", "Agentic Workflow Engineer",
        "RAG Engineer", "RAG Developer", "Retrieval Engineer", "MCP Engineer",
        "MCP Developer", "Model Context Protocol Engineer", "AI Automation Engineer",
        "AI Automation Developer", "Intelligent Automation Engineer",
        "AI Application Engineer", "GenAI Application Engineer",
        "Conversational AI Engineer", "Conversational AI Developer", "Prompt Engineer",
        "LangChain Developer", "LangChain Engineer", "NLP Engineer", "NLP Developer",
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
        "API Development / Backend Engineer (FastAPI, Flask, REST APIs)",
        "API Development / Backend Engineer", "API Backend Engineer",
        "FastAPI Developer", "FastAPI Engineer", "Flask Developer", "Flask Engineer",
        "REST API Developer", "REST API Engineer", "Node.js Developer", "Node.js Engineer",
        "Full-Stack Developer / Engineer (React, Node.js)", "Full-Stack Developer / Engineer",
        "Full Stack Developer / Engineer", "Full-Stack Developer", "Full-Stack Engineer",
        "Full Stack Developer", "Full Stack Engineer", "React Developer", "React Engineer",
        "Mobile Developer (Flutter)", "Mobile Developer", "Mobile Engineer",
        "Flutter Developer", "Flutter Engineer", "Mobile App Developer",
        "Application Engineer", "Application Developer", "Software Application Engineer",
        "Web Application Engineer", "API Engineer", "API Developer",
        "Integration Engineer", "Integration Developer", "Platform Software Engineer"
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
        "Automation Engineer (n8n, Docker, CI/CD, Workflow Automation)",
        "Automation Engineer", "Automation Developer", "AI Automation Engineer",
        "AI Automation Developer", "Intelligent Automation Engineer",
        "Intelligent Automation Developer", "Process Automation Engineer",
        "Process Automation Developer", "Workflow Automation Engineer",
        "AI Workflow Automation Engineer", "n8n Developer", "n8n Automation Engineer",
        "CI/CD Engineer", "DevOps Automation Engineer",
        "RPA Developer", "RPA Engineer", "Robotic Process Automation Engineer"
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
# 7 Target Career Tracks with Roles, Categorized Skills & Keywords
# -----------------------------------------------------------------------------
TARGET_CAREER_TRACKS: dict[str, dict[str, Any]] = {
    "AI_ENGINEER": {
        "id": "ai_engineer",
        "title": "AI Engineer",
        "roles": [
            "AI Engineer", "Applied AI Engineer", "AI Developer",
            "Artificial Intelligence Engineer", "AI Software Engineer"
        ],
        "skills": ["Machine Learning", "GenAI", "LLMs", "NLP", "LangChain", "Python"],
        "keywords": ["ai", "artificial intelligence", "deep learning", "neural network", "machine learning", "python"],
    },
    "GENAI_LLM": {
        "id": "genai_llm",
        "title": "GenAI & LLM Engineer / Developer (GenAI, LLMs, NLP, LangChain)",
        "roles": [
            "GenAI Engineer", "Generative AI Engineer", "GenAI Developer",
            "Generative AI Developer", "LLM Engineer", "Large Language Model Engineer",
            "LLM Developer", "AI Agent Engineer", "AI Agent Developer",
            "LangChain Developer", "LangChain Engineer", "NLP Engineer", "NLP Developer",
            "RAG Engineer", "Prompt Engineer"
        ],
        "skills": ["GenAI", "LLMs", "NLP", "LangChain", "Python", "Machine Learning"],
        "keywords": ["genai", "generative ai", "llm", "llms", "nlp", "langchain", "rag", "agents", "openai", "gemini"],
    },
    "API_BACKEND": {
        "id": "api_backend",
        "title": "API Development / Backend Engineer (FastAPI, Flask, REST APIs)",
        "roles": [
            "Backend Engineer", "Backend Developer", "API Engineer", "API Developer",
            "Python Backend Developer", "Python Backend Engineer", "FastAPI Developer",
            "FastAPI Engineer", "Flask Developer", "REST API Developer", "Node.js Backend Developer"
        ],
        "skills": ["FastAPI", "Flask", "REST APIs", "Node.js", "Python"],
        "keywords": ["fastapi", "flask", "rest api", "rest apis", "restful", "node.js", "nodejs", "python", "backend", "api"],
    },
    "FULL_STACK": {
        "id": "full_stack",
        "title": "Full-Stack Developer / Engineer (React, Node.js)",
        "roles": [
            "Full Stack Developer", "Full Stack Engineer", "Full-Stack Developer",
            "Full-Stack Engineer", "React Developer", "Node.js Developer", "Web Developer"
        ],
        "skills": ["React", "Node.js"],
        "keywords": ["react", "react.js", "reactjs", "node.js", "nodejs", "node", "full stack", "full-stack", "frontend", "web"],
    },
    "MOBILE": {
        "id": "mobile",
        "title": "Mobile Developer (Flutter)",
        "roles": [
            "Mobile Developer", "Mobile Engineer", "Flutter Developer", "Flutter Engineer",
            "Mobile Application Developer", "Cross-Platform Mobile Developer"
        ],
        "skills": ["Flutter"],
        "keywords": ["flutter", "dart", "mobile", "mobile developer", "mobile engineer", "cross-platform"],
    },
    "AUTOMATION": {
        "id": "automation",
        "title": "Automation Engineer (n8n, Docker, CI/CD, Workflow Automation)",
        "roles": [
            "Automation Engineer", "Workflow Automation Engineer", "Automation Developer",
            "n8n Developer", "Process Automation Engineer", "CI/CD Engineer", "DevOps Engineer"
        ],
        "skills": ["n8n", "Docker", "CI/CD", "Automation"],
        "keywords": ["n8n", "docker", "ci/cd", "cicd", "automation", "workflow automation", "process automation", "devops"],
    },
    "ML_PYTHON": {
        "id": "ml_python",
        "title": "Machine Learning & Python Developer",
        "roles": [
            "Machine Learning Engineer", "Machine Learning Developer", "ML Engineer",
            "ML Developer", "Python Developer", "Python Engineer", "Data Scientist"
        ],
        "skills": ["Machine Learning", "Python", "SQL", "Power BI", "Pandas", "NumPy", "Scikit-learn"],
        "keywords": ["machine learning", "python", "ml", "scikit-learn", "pandas", "numpy", "sql", "power bi"],
    },
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
    "machine learning", "deep learning", "nlp", "llm", "llms", "rag", "langchain",
    "llamaindex", "gemini", "openai", "agentic", "agents", "mcp", "n8n",
    "docker", "kubernetes", "fastapi", "flask", "django", "pytorch",
    "tensorflow", "mysql", "postgresql", "mongodb", "etl", "data pipeline",
    "aws", "gcp", "azure", "git", "rest api", "rest apis", "spark", "kafka", "dbt",
    "selenium", "playwright", "pytest", "devops", "ci/cd", "linux",
    "react", "node.js", "nodejs", "flutter", "dart", "genai", "generative ai",
    "automation", "workflow automation"
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
    return re.compile(rf"(?<!\w){clean}(?!\w)", re.IGNORECASE)


COMPILED_ROLES = {
    family: [(role, compile_role_regex(role)) for role in roles]
    for family, roles in ROLE_TAXONOMY.items()
}
COMPILED_FALSE_POSITIVES = [re.compile(p, re.IGNORECASE) for p in FALSE_POSITIVE_PATTERNS]


def get_career_tracks() -> dict[str, dict[str, Any]]:
    """Return definition of all 7 Target Career Tracks with associated roles, skills, and keywords."""
    return TARGET_CAREER_TRACKS


def match_career_tracks(title: str, description: str = "", requirements: str = "") -> list[str]:
    """Match a job title/posting against the 7 Target Career Tracks."""
    clean_title = (title or "").lower().strip()
    clean_desc = (description or "").lower().strip()
    clean_req = (requirements or "").lower().strip()
    full_text = f"{clean_title} {clean_desc} {clean_req}".strip()
    matched_tracks: list[str] = []

    for track_key, track_info in TARGET_CAREER_TRACKS.items():
        # Check title against track title and track roles
        role_matched = False
        candidates = [track_info["title"]] + track_info["roles"]
        for role in candidates:
            clean_role = role.lower()
            if re.search(rf"(?<!\w){re.escape(clean_role)}(?!\w)", clean_title):
                matched_tracks.append(track_info["title"])
                role_matched = True
                break
        if role_matched:
            continue

        # Check title and text against keywords
        title_kw = any(re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", clean_title) for kw in track_info["keywords"])
        text_kw_count = sum(1 for kw in track_info["keywords"] if re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", full_text))
        if title_kw or text_kw_count >= 2:
            matched_tracks.append(track_info["title"])

    return matched_tracks


def extract_experience(text: str) -> str:
    """Extract required experience from title or description snippet."""
    if not text:
        return ""
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
        matched_tracks: list[str]
        experience_required: str
        is_false_positive: bool
    """
    clean_title = (title or "").strip()
    clean_desc = (description or "").strip()
    clean_req = (requirements or "").strip()
    full_text = f"{clean_title} {clean_desc} {clean_req}".lower()

    # 1. Guardrail check
    for fp in COMPILED_FALSE_POSITIVES:
        if fp.search(clean_title):
            return {
                "matched_roles": [],
                "role_families": [],
                "role_confidence": 0.0,
                "matched_skills": [],
                "matched_tracks": [],
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
            elif clean_desc and reg.search(clean_desc[:800]):
                # weaker match in opening description
                if role_name not in matched_roles:
                    matched_roles.append(role_name)
                    family_matched = True
        if family_matched:
            role_families.append(family)

    # 3. Matched skills
    matched_skills = [
        skill for skill in TECH_SKILLS
        if re.search(rf"(?<!\w){re.escape(skill)}(?!\w)", full_text, re.IGNORECASE)
    ]

    # 4. Matched career tracks
    matched_tracks = match_career_tracks(clean_title, clean_desc, clean_req)

    # 5. Confidence calculation
    if title_matches > 0:
        confidence = min(0.98, 0.70 + (title_matches * 0.08) + min(len(matched_skills) * 0.03, 0.20))
    elif matched_roles:
        confidence = min(0.85, 0.50 + min(len(matched_skills) * 0.05, 0.35))
    else:
        confidence = 0.0

    snippet = f"{clean_title} {clean_desc[:1200]}".strip()
    exp_req = extract_experience(snippet)

    return {
        "matched_roles": matched_roles[:6],
        "role_families": role_families,
        "role_confidence": round(confidence, 2),
        "matched_skills": matched_skills[:12],
        "matched_tracks": matched_tracks,
        "experience_required": exp_req,
        "is_false_positive": False
    }
