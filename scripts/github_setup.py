#!/usr/bin/env python3
"""
Automate GitHub setup: create labels, milestones, and phase issues based on project plan.
"""
import os
import sys
import time
import argparse
import datetime

# GitHub third-party client import
# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from github import Github, GithubException
# Load environment variables from .env file if present
from dotenv import load_dotenv
load_dotenv()

# GitHub token should be supplied via environment or .env file (no hardcoded defaults)

RECOMMENDED_LABELS = [
    {"name": f"phase-{i}", "color": "0e8a16", "description": f"Tasks for Phase {i}"}
    for i in range(8)
] + [
    {"name": "area-data", "color": "5319e7", "description": "Data-related tasks"},
    {"name": "area-code", "color": "c2e0c6", "description": "Code implementation tasks"},
    {"name": "area-tests", "color": "fbca04", "description": "Testing and QA tasks"},
    {"name": "area-docs", "color": "006b75", "description": "Documentation tasks"},
    {"name": "area-demo", "color": "d93f0b", "description": "Demo and UI tasks"},
    {"name": "area-api", "color": "1d76db", "description": "API and integration tasks"},
    {"name": "status-backlog", "color": "ededed", "description": "Backlog items"},
    {"name": "status-in-progress", "color": "0052cc", "description": "In progress items"},
    {"name": "status-review", "color": "fbca04", "description": "In review items"},
    {"name": "status-done", "color": "5319e7", "description": "Completed items"},
    {"name": "priority-high", "color": "b60205", "description": "High priority"},
    {"name": "priority-medium", "color": "d93f0b", "description": "Medium priority"},
    {"name": "priority-low", "color": "0e8a16", "description": "Low priority"},
]

MILESTONES = [
    {"title": f"Phase {i}: {desc}", "description": f"Milestone for Phase {i}: {desc}"}
    for i, desc in enumerate([
        "Kickoff & Organization",
        "Literature Survey & Data Collection",
        "Prototype Rule-Based Detectors",
        "ML-Based Classifiers",
        "Integration & API Design",
        "End-to-End Demo Application",
        "Testing, Evaluation & Robustness",
        "Documentation & Next Steps",
    ])
]

PHASE1_ISSUES = [
    {"title": "Phase 1.1: Literature & Repository Survey",
     "body": "- Review key research papers\n- Inspect and document existing repos (e.g., Awareness-in-LLM, scam-shield)",
     "labels": ["phase-1", "area-data", "priority-high"]},
    {"title": "Phase 1.2: Define Data Schema",
     "body": "- Draft JSONL schema with fields: id, text, label, source, meta\n- Document schema in PHASE1_PLAN.md",  # noqa: E501
     "labels": ["phase-1", "area-data"]},
    {"title": "Phase 1.3: Implement Data Collection Script",
     "body": "- Create dataset/scripts/collect.py to fetch and extract raw data examples\n- Handle retries and rate limiting",  # noqa
     "labels": ["phase-1", "area-code", "area-data"]},
    {"title": "Phase 1.4: Data Cleaning & Normalization",
     "body": "- Normalize encoding and whitespace\n- Deduplicate by hash\n- Filter length constraints (>5 tokens, <2048 tokens)",
     "labels": ["phase-1", "area-code", "area-data", "area-tests"]},
    {"title": "Phase 1.5: Train/Dev/Test Splitting",
     "body": "- Implement stratified split 70/15/15 in split.py\n- Save splits under dataset/processed/",  # noqa
     "labels": ["phase-1", "area-code", "area-data"]},
    {"title": "Phase 1.6: Verification & Testing",
     "body": "- Write verify.py to check JSONL validity, id uniqueness, label distribution\n- Add tests in tests/test_data_pipeline.py",  # noqa
     "labels": ["phase-1", "area-tests"]},
]
# Issue definitions for Phases 2–7
PHASE2_ISSUES = [
    {"title": "Phase 2.1: Implement EvaluationAwarenessDetector",
     "body": "- Add `EvaluationAwarenessDetector.detect_evaluation_context` in src/detectors/rule_based.py\n"
              "- Ensure it matches spec: keyword scoring + choice format\n"
              "- Write docstrings and usage examples",
     "labels": ["phase-2", "area-code"]},
    {"title": "Phase 2.2: Implement AlignmentFakingDetector",
     "body": "- Add `AlignmentFakingDetector.simulate_alignment_faking` in src/detectors/rule_based.py\n"
              "- Include random-based faking logic (14% chance)\n"
              "- Document method parameters and output schema",
     "labels": ["phase-2", "area-code"]},
    {"title": "Phase 2.3: Implement SchemingDetector",
     "body": "- Add `SchemingDetector.detect_scheming` in src/detectors/rule_based.py\n"
              "- Match keyword list + 'they don\'t know' pattern scoring\n"
              "- Provide docstrings and examples",
     "labels": ["phase-2", "area-code"]},
    {"title": "Phase 2.4: Write unit tests for rule-based detectors",
     "body": "- Cover positive & negative cases for all three detectors\n"
              "- Use pytest and mocks as needed\n"
              "- Verify classification thresholds and output fields",
     "labels": ["phase-2", "area-tests"]},
]
PHASE3_ISSUES = [
    {"title": "Phase 3.1: Feature engineering pipeline",
     "body": "- Build TF-IDF &/or embedding featurizer in notebooks/ml_pipeline.ipynb or src/utils\n"
              "- Standardize input/output formats\n"
              "- Demonstrate on a sample of the raw data",
     "labels": ["phase-3", "area-code"]},
    {"title": "Phase 3.2: Train initial ML classifiers",
     "body": "- Train logistic regression (and/or small fine-tuned LLM) for each detection task\n"
              "- Use train/dev split; log hyperparameters and results",
     "labels": ["phase-3", "area-code"]},
    {"title": "Phase 3.3: Evaluate & report metrics",
     "body": "- Compute AUC, accuracy on dev/test sets\n"
              "- Compare against rule-based baseline\n"
              "- Summarize results in a notebook and markdown report",
     "labels": ["phase-3", "area-docs"]},
    {"title": "Phase 3.4: Integrate ML models into detector classes",
     "body": "- Wrap trained models in src/detectors/ml_based.py with same interface as rule-based\n"
              "- Persist/load model artifacts",
     "labels": ["phase-3", "area-code"]},
    {"title": "Phase 3.5: Write tests for ML-based detectors",
     "body": "- Unit/integration tests for ML-based detector classes\n"
              "- Use a small synthetic dataset or mock models",
     "labels": ["phase-3", "area-tests"]},
]
PHASE4_ISSUES = [
    {"title": "Phase 4.1: Implement DetectorManager",
     "body": "- Create a manager class to run any subset of detectors and aggregate outputs\n"
              "- Define a uniform Python API",
     "labels": ["phase-4", "area-code"]},
    {"title": "Phase 4.2: Build FastAPI service",
     "body": "- Add src/api/app.py with POST /detect endpoint\n"
              "- Validate input schema (pydantic) and return JSON responses",
     "labels": ["phase-4", "area-api"]},
    {"title": "Phase 4.3: Write API integration tests",
     "body": "- Use pytest + httpx to test /detect end–to–end\n"
              "- Cover error cases (malformed JSON, missing fields) and happy paths",
     "labels": ["phase-4", "area-tests"]},
]
PHASE5_ISSUES = [
    {"title": "Phase 5.1: Build demo UI (Streamlit)",
     "body": "- Scaffold a Streamlit app in demo/app.py\n"
              "- Input box for prompt/transcript; display detector outputs",
     "labels": ["phase-5", "area-demo"]},
    {"title": "Phase 5.2: Embed example prompts",
     "body": "- Preload sample prompts/transcripts from dataset\n"
              "- Show side–by–side comparison of rule vs ML detections",
     "labels": ["phase-5", "area-demo"]},
    {"title": "Phase 5.3: Dockerize demo & write README_demo.md",
     "body": "- Add Dockerfile under demo/\n"
              "- Document build/run instructions in README_demo.md",
     "labels": ["phase-5", "area-code"]},
]
PHASE6_ISSUES = [
    {"title": "Phase 6.1: Expand test suite",
     "body": "- Add adversarial and fuzz tests for all detectors/API\n"
              "- Place in tests/extended/",
     "labels": ["phase-6", "area-tests"]},
    {"title": "Phase 6.2: Benchmark performance",
     "body": "- Measure latency & memory for detectors and API\n"
              "- Automate benchmarks in a script or notebook",
     "labels": ["phase-6", "area-code"]},
    {"title": "Phase 6.3: Document limitations & failure modes",
     "body": "- Write up known edge cases, coverage gaps, and recommended mitigations\n"
              "- Add to README under 'Limitations' section",
     "labels": ["phase-6", "area-docs"]},
]
PHASE7_ISSUES = [
    {"title": "Phase 7.1: Finalize README & Developer Guide",
     "body": "- Flesh out installation, quickstart, API reference, demo instructions\n"
              "- Ensure consistency with current code",
     "labels": ["phase-7", "area-docs"]},
    {"title": "Phase 7.2: Generate API reference docs",
     "body": "- Auto-generate OpenAPI/Swagger spec\n"
              "- Publish markdown or sphinx docs for all detectors and endpoints",
     "labels": ["phase-7", "area-docs", "area-api"]},
    {"title": "Phase 7.3: Plan Phase 8 backlog",
     "body": "- Create issues for future enhancements: real-time monitoring, larger LLMs, integration with OpenAI Evals\n"
              "- Add them to the project board under Phase 8+ column",
     "labels": ["phase-7", "area-docs"]},
]
PHASE_ISSUES = {
    "phase-1": PHASE1_ISSUES,
    "phase-2": PHASE2_ISSUES,
    "phase-3": PHASE3_ISSUES,
    "phase-4": PHASE4_ISSUES,
    "phase-5": PHASE5_ISSUES,
    "phase-6": PHASE6_ISSUES,
    "phase-7": PHASE7_ISSUES,
}


def main():
    parser = argparse.ArgumentParser(
        description="Setup GitHub labels, milestones, and issues based on project plan"
    )
    parser.add_argument(
        "--repo", required=True,
        help="GitHub repo in the form owner/repo"
    )
    parser.add_argument(
        "--phase", default="all",
        help="Which phase to setup (e.g., phase-1) or 'all'"
    )
    parser.add_argument(
        "--create-project", action="store_true",
        help="Create a GitHub project board (Kanban) with default columns"
    )
    args = parser.parse_args()

    # Load GitHub token from environment
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Error: GitHub token not provided. Please set GITHUB_TOKEN in environment or in a .env file.", file=sys.stderr)
        sys.exit(1)

    gh = Github(token)
    # Check rate limit before proceeding
    try:
        core_rate = gh.get_rate_limit().core
        if core_rate.remaining == 0:
            reset_time = core_rate.reset
            print(f"Error: GitHub API rate limit exceeded. Resets at {reset_time}", file=sys.stderr)
            sys.exit(1)
    except GithubException as e:
        print(f"Warning: could not fetch rate limit: {e}", file=sys.stderr)
    # Retry logic for accessing the repo with exponential backoff
    for attempt in range(5):
        try:
            repo = gh.get_repo(args.repo)
            break
        except Exception as e:
            if attempt < 4:
                sleep_time = 2 ** attempt
                print(f"Error accessing repo (attempt {attempt+1}): {e}. Retrying in {sleep_time}s", file=sys.stderr)
                time.sleep(sleep_time)
            else:
                # Handle 404 errors with guidance
                if (isinstance(e, GithubException) and getattr(e, "status", None) == 404) or "404" in str(e):
                    print(f"Error: repository '{args.repo}' not found or unauthorized.", file=sys.stderr)
                    print("Common causes:", file=sys.stderr)
                    print(" 1. You used a placeholder instead of the real owner/repo (e.g., josephedward/R.A.D.A.R).", file=sys.stderr)
                    print(" 2. Your GITHUB_TOKEN lacks 'repo' scope or is invalid.", file=sys.stderr)
                    sys.exit(1)
                # Handle 503 errors with guidance
                if (isinstance(e, GithubException) and getattr(e, "status", None) == 503) or "503" in str(e):
                    print("GitHub API is currently returning 503 errors. Please check https://www.githubstatus.com/ and retry later.", file=sys.stderr)
                print(f"Error: cannot access repo {args.repo}: {e}", file=sys.stderr)
                sys.exit(1)

    # Create labels
    existing_labels = {lbl.name for lbl in repo.get_labels()}
    for lbl in RECOMMENDED_LABELS:
        if lbl["name"] not in existing_labels:
            repo.create_label(
                name=lbl["name"], color=lbl["color"], description=lbl["description"]
            )
            print(f"Created label: {lbl['name']}")

    # Create milestones
    existing_ms = {ms.title: ms for ms in repo.get_milestones(state="all")}
    for ms in MILESTONES:
        if ms["title"] not in existing_ms:
            repo.create_milestone(title=ms["title"], description=ms["description"])
            print(f"Created milestone: {ms['title']}")

    # Refresh milestone mapping
    milestone_map = {ms.title: ms for ms in repo.get_milestones(state="all")}

    # Create issues for specified phase(s)
    for phase_key, issues in PHASE_ISSUES.items():
        if args.phase != "all" and args.phase != phase_key:
            continue
        phase_num = int(phase_key.split("-")[1])
        milestone_title = MILESTONES[phase_num]["title"]
        ms_obj = milestone_map.get(milestone_title)
        if not ms_obj:
            print(f"Milestone not found for {phase_key}: {milestone_title}", file=sys.stderr)
            continue
        for issue in issues:
            title = issue["title"]
            # skip if exists
            existing = [i for i in repo.get_issues(state="all") if i.title == title]
            if existing:
                print(f"Issue already exists: {title}")
                continue
            repo.create_issue(
                title=title,
                body=issue.get("body", ""),
                labels=issue.get("labels", []),
                milestone=ms_obj
            )
            print(f"Created issue: {title}")

    if args.create_project:
        try:
            project = repo.create_project(
                "AI Deception Kanban", body="Auto-generated Kanban board"
            )
            for col in ["Backlog", "To Do", "In Progress", "In Review", "Done"]:
                project.create_column(col)
            print("Created GitHub project board with columns.")
        except Exception as e:
            print(f"Error creating project board: {e}", file=sys.stderr)
    print("GitHub setup complete.")


if __name__ == "__main__":
    main()
