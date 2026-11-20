"""Verification suite for Shubham Kadam's Target Career Tracks, Skills, and Contact info.

Ensures:
1. profile.json and profile.example.json define all 7 Target Career Tracks,
   categorized skills, contact information, and target locations.
2. config.yaml and jobhunt/roles.py define all 7 Target Career Tracks and their keywords.
3. gui/index.html and root index.html display the updated tracks, categorized skills,
   and contact details in the Profile tab.
"""
from __future__ import annotations

import json
from pathlib import Path
import yaml
import pytest

from jobhunt.roles import TARGET_CAREER_TRACKS, get_career_tracks, match_career_tracks, classify_job, TECH_SKILLS

ROOT_DIR = Path(__file__).resolve().parent.parent
PROFILE_JSON = ROOT_DIR / "profile.json"
PROFILE_EXAMPLE_JSON = ROOT_DIR / "profile.example.json"
CONFIG_YAML = ROOT_DIR / "config.yaml"
GUI_INDEX = ROOT_DIR / "gui" / "index.html"
ROOT_INDEX = ROOT_DIR / "index.html"

EXPECTED_7_TRACKS = [
    "AI Engineer",
    "GenAI & LLM Engineer / Developer (GenAI, LLMs, NLP, LangChain)",
    "API Development / Backend Engineer (FastAPI, Flask, REST APIs)",
    "Full-Stack Developer / Engineer (React, Node.js)",
    "Mobile Developer (Flutter)",
    "Automation Engineer (n8n, Docker, CI/CD, Workflow Automation)",
    "Machine Learning & Python Developer",
]

EXPECTED_SKILL_CATEGORIES = {
    "AI & ML": ["Machine Learning", "GenAI", "LLMs", "NLP", "LangChain", "Python"],
    "API & Backend": ["FastAPI", "Flask", "REST APIs", "Node.js", "Python"],
    "Full-Stack & Frontend": ["React", "Node.js"],
    "Mobile": ["Flutter"],
    "Automation & DevOps": ["n8n", "Docker", "CI/CD", "Automation"],
    "Data & BI": ["SQL", "Power BI", "Pandas", "NumPy", "Scikit-learn"],
}


def test_profile_json_and_example_target_roles():
    """R1: Both profile.json and profile.example.json must contain all 7 target career tracks."""
    for path in [PROFILE_JSON, PROFILE_EXAMPLE_JSON]:
        assert path.exists(), f"{path} must exist"
        data = json.loads(path.read_text(encoding="utf-8"))

        roles = data.get("target_roles", [])
        for track in EXPECTED_7_TRACKS:
            assert track in roles, f"Track '{track}' missing in target_roles of {path.name}"


def test_profile_json_and_example_categorized_skills():
    """R1: Both profile.json and profile.example.json must contain the 6 categorized skill groups."""
    for path in [PROFILE_JSON, PROFILE_EXAMPLE_JSON]:
        data = json.loads(path.read_text(encoding="utf-8"))
        skills = data.get("skills", {})

        for cat, expected_list in EXPECTED_SKILL_CATEGORIES.items():
            assert cat in skills, f"Category '{cat}' missing in skills of {path.name}"
            actual = [s.lower() for s in skills[cat]]
            for s in expected_list:
                assert s.lower() in actual, f"Skill '{s}' missing in '{cat}' of {path.name}"


def test_profile_json_contact_and_locations():
    """R1: Contact email, phone, and target locations match requirements."""
    for path in [PROFILE_JSON, PROFILE_EXAMPLE_JSON]:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("email") == "ssk080204@gmail.com"
        assert data.get("phone") == "+918169832448"
        loc = str(data.get("location", ""))
        assert "Mumbai" in loc
        assert "Remote" in loc


def test_roles_py_supports_all_7_career_tracks():
    """R2: jobhunt/roles.py defines and supports all 7 target career tracks."""
    tracks = get_career_tracks()
    assert len(tracks) == 7

    track_titles = [t["title"] for t in tracks.values()]
    for expected in EXPECTED_7_TRACKS:
        assert expected in track_titles, f"Track '{expected}' missing from TARGET_CAREER_TRACKS"


def test_config_yaml_supports_all_7_career_tracks():
    """R2: config.yaml defines target_career_tracks with all 7 tracks and keywords."""
    with open(CONFIG_YAML, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    assert "target_career_tracks" in cfg
    yaml_tracks = cfg["target_career_tracks"]
    assert len(yaml_tracks) == 7

    titles = [t["title"] for t in yaml_tracks.values()]
    for expected in EXPECTED_7_TRACKS:
        assert expected in titles, f"Track '{expected}' missing in config.yaml target_career_tracks"
        # Each track must have keywords
        matching_entry = next(t for t in yaml_tracks.values() if t["title"] == expected)
        assert len(matching_entry.get("keywords", [])) >= 2, f"Track '{expected}' missing keywords in config.yaml"


def test_career_tracks_matching_logic():
    """R2: match_career_tracks maps job titles and text to target tracks."""
    sample_jobs = [
        ("Senior AI Engineer", "AI Engineer"),
        ("GenAI Application Developer", "GenAI & LLM Engineer / Developer (GenAI, LLMs, NLP, LangChain)"),
        ("FastAPI Backend Engineer", "API Development / Backend Engineer (FastAPI, Flask, REST APIs)"),
        ("Full Stack Developer (React / Node)", "Full-Stack Developer / Engineer (React, Node.js)"),
        ("Cross-platform Flutter Mobile Engineer", "Mobile Developer (Flutter)"),
        ("DevOps & n8n Workflow Automation Engineer", "Automation Engineer (n8n, Docker, CI/CD, Workflow Automation)"),
        ("Machine Learning & Python Developer", "Machine Learning & Python Developer"),
    ]
    for title, expected_track in sample_jobs:
        matched = match_career_tracks(title)
        assert expected_track in matched, f"'{title}' did not match '{expected_track}', got: {matched}"


def test_tech_skills_lexicon_alignment():
    """R2: TECH_SKILLS in roles.py contains all skills across the 6 skill categories."""
    skills_lower = set(s.lower() for s in TECH_SKILLS)
    for cat, skill_list in EXPECTED_SKILL_CATEGORIES.items():
        for skill in skill_list:
            assert skill.lower() in skills_lower, f"Skill '{skill}' from category '{cat}' missing in TECH_SKILLS"


def test_gui_and_root_index_html_display_career_tracks():
    """R3: gui/index.html and root index.html display updated career tracks in Profile tab."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        content = html_path.read_text(encoding="utf-8")
        assert "Target Career Tracks" in content

        # Check all 7 tracks appear in content (raw HTML or escaped)
        for track in EXPECTED_7_TRACKS:
            escaped_track = track.replace("&", "&amp;")
            assert track in content or escaped_track in content, f"Track '{track}' missing in {html_path.name}"

        # Check contact info
        assert "ssk080204@gmail.com" in content
        assert "+918169832448" in content

        # Check location
        assert "Mumbai Metropolitan Region" in content
        assert "Remote" in content


def test_root_index_html_bundled_profile_payload():
    """R3: root index.html bundled window.INITIAL_DATA.profile contains tracks and skills."""
    content = ROOT_INDEX.read_text(encoding="utf-8")
    import re
    m = re.search(r"window\.INITIAL_DATA\s*=\s*(\{.*?\});\s*</script>", content, re.DOTALL)
    assert m, "window.INITIAL_DATA not found in root index.html"
    data = json.loads(m.group(1))

    profile = data.get("profile", {})
    assert profile.get("email") == "ssk080204@gmail.com"
    assert profile.get("phone") == "+918169832448"

    roles = profile.get("target_roles", [])
    for track in EXPECTED_7_TRACKS:
        assert track in roles, f"Track '{track}' missing in window.INITIAL_DATA.profile.target_roles"
