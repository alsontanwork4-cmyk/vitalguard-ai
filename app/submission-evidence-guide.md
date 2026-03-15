# Submission Evidence Guide

This document is the canonical source of truth for repository claims, external form answers, and demo wording. If a statement is not supported here, soften it or move it to future work.

## Evidence Classes

| Class | Meaning | Use in Submission |
| --- | --- | --- |
| `implemented` | Directly demonstrated by code, scripts, or generated artifacts in this repository. | Safe to state as present functionality. |
| `supported but not clinically validated` | Reasonable interpretation of the prototype and benchmarks, but not proven by a clinical or operational study. | Keep the wording cautious and explicitly frame it as prototype evidence. |
| `future work` | Not present in the repository or only discussed as roadmap. | Keep it in roadmap/future plans only. |

## Claim Matrix

| Claim Area | Classification | Repo Basis | Submission Guidance |
| --- | --- | --- | --- |
| 3-agent ADK workflow | `implemented` | `agents/vitalguard/agent.py` | Safe to describe as current architecture. |
| Deterministic analytics: NEWS2, shock index, MAP, slopes, rolling trends, pattern detection | `implemented` | `tools/analytics.py` | Safe to describe as current technical depth. |
| VitalDB support: downloader, normalization, real-case loading | `implemented` | `scripts/download_vitaldb_case.py`, `tools/vitaldb_adapter.py`, `data/vitaldb_case_4096.csv` | Safe to describe as current data-ingestion support. |
| Recovery handling: missing file, missing tracks, no dataset, minute clamp, short window, degraded mode | `implemented` | `tools/monitor_tools.py`, `tools/vitaldb_adapter.py` | Safe to describe as current robustness behavior. |
| Evaluation artifacts: scenario verification, real VitalDB evaluation, degraded VitalDB evaluation | `implemented` | `scripts/verify_scenarios.py`, `scripts/evaluate_vitalguard.py`, `data/eval_reports/` | Safe to describe as current benchmark evidence. |
| Stable benchmark stays quiet | `implemented` | `stable_postop` fixture and evaluation outputs | Safe to describe as included benchmark behavior. |
| Prototype may help surface gradual deterioration earlier | `supported but not clinically validated` | multi-parameter analytics and benchmark timing | Use `is intended to` or `is designed to demonstrate`. |
| Prototype may reduce unnecessary escalations on stable cases | `supported but not clinically validated` | stable benchmark remains `INFO` | Do not claim reduced alarm fatigue in real care settings. |
| Security guardrails exist | `supported but not clinically validated` | constrained tool surface and validation logic | Describe as prototype guardrails, not production security architecture. |
| Workflow efficiency gains from Gemini / ADK | `supported but not clinically validated` | plausible based on orchestration design only | Do not claim measured efficiency without a benchmark. |
| Live bedside monitor integration | `future work` | not in repo | Keep in roadmap only. |
| EHR integration | `future work` | not in repo | Keep in roadmap only. |
| Clinician feedback loop | `future work` | not in repo | Keep in roadmap only. |
| Production auth, audit, compliance controls | `future work` | not in repo | Keep in roadmap only. |
| Reduced mortality or improved patient outcomes | `future work` | no clinical study | Do not claim. |

## Form Answer Guide

| Form Section | Status | How to Phrase It |
| --- | --- | --- |
| Agent Profiles | `safe as written` | Describe coordinator, trend analyzer, and protocol recommender as current implementation. |
| Google ADK Implementation | `safe as written` | State that the project uses a sequential ADK multi-agent workflow with function tools. |
| Technical Innovation | `safe as written` | Emphasize deterministic analytics plus agent interpretation and recovery behavior. |
| Success Metrics | `safe as written` | Keep metrics tied to alert timing, pattern detection, scenario pass/fail, and degraded-mode continuity. |
| SDG / Impact / Problem Statement | `safe as written with prototype framing` | Focus on the clinical problem and intended contribution, not proven hospital impact. |
| AI Functionality & Performance | `needs softer wording` | Say the system produces escalation-oriented summaries on synthetic and retrospective VitalDB data; avoid claims of validated clinical performance. |
| Security & Guardrails | `needs softer wording` | Say the prototype constrains tools and validates data paths; avoid claims of production-grade security/compliance. |
| Clinical impact / outcomes / alarm fatigue | `should be rewritten` | Replace with prototype intent and benchmark evidence only. |
| Future Roadmap | `future work` | Use for live integrations, compliance, feedback loops, and deployment plans only. |

## Approved Wording Snippets

### AI Functionality & Performance

Use:

> VitalGuard is a prototype multi-agent monitoring workflow that analyzes synthetic scenarios and retrospective VitalDB CSV exports. It computes deterministic early-warning metrics and converts them into escalation-oriented summaries with explicit recovery handling.

Avoid:

> VitalGuard improves patient outcomes.

### Security & Guardrails

Use:

> The prototype uses a constrained tool layer, deterministic validation, explicit recovery states, and schema normalization so that agents interpret structured outputs rather than inventing operational behavior.

Avoid:

> VitalGuard includes production-grade hospital security and compliance controls.

### Impact / Outcomes

Use:

> The project is intended to demonstrate a technically grounded approach for surfacing subtle deterioration patterns earlier in benchmark scenarios. Clinical validation and real-world impact measurement remain future work.

Avoid:

> VitalGuard reduces mortality and alarm fatigue.

## Submission Rules

- Prefer `prototype`, `benchmark`, `public VitalDB case`, `retrospective CSV`, and `escalation support`.
- Avoid `hospital-ready`, `clinically validated`, `deployable today`, `reduces mortality`, `reduces alarm fatigue`, and `production security`.
- Keep all future integrations and compliance claims in roadmap language only.
