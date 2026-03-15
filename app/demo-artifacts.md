# Demo Runbook

This runbook is the judge-facing demo source of truth for the current MVP. Use it together with `app/submission-evidence-guide.md` so spoken claims match what the repository actually proves.

## Primary Demo Path

- Launch the ADK Web UI with `python -m google.adk.cli web agents`.
- Use the built-in ADK UI as the only committed interface for this submission.
- Present the system as a prototype that analyzes scenario CSVs and VitalDB exports, not a live hospital deployment.

## Live Prompt Sequence

1. `Load scenario sepsis_onset and assess the patient`
   Expected safe outcome: warning-level deterioration language with detected sepsis-style multi-parameter patterning.
2. `Load scenario compensatory_shock and assess the patient`
   Expected safe outcome: warning-level compensatory tachycardia / bleeding-risk style language before frank collapse in the fixture.
3. `Load scenario respiratory_deterioration and assess the patient`
   Expected safe outcome: warning-level desaturation trend language before severe end-state desaturation in the fixture.
4. `Load scenario stable_postop and assess the patient`
   Expected safe outcome: `INFO` output with no unnecessary escalation.
5. `Load VitalDB file .\data\vitaldb_case_4096.csv and assess minute 25`
   Expected safe outcome: the system loads a real public case CSV, normalizes it, and produces an escalation-oriented assessment.

## Recovery Demo Prompts

1. `Assess the patient`
   Expected safe outcome: recovery response explaining that no scenario or VitalDB file is active yet.
2. `Load VitalDB file C:\missing\case.csv and assess the patient`
   Expected safe outcome: recovery response explaining the file is missing and that a full Windows path is required.
3. `Load VitalDB file .\data\vitaldb_case_4096.csv and assess minute 999`
   Expected safe outcome: minute clamp note showing the requested minute and the valid range.

## Safe Presenter Notes

- Say `prototype`, `demo`, `benchmark`, `public VitalDB case`, and `escalation support`.
- Do not say the system improves patient outcomes, reduces mortality, reduces alarm fatigue, or is deployed in a hospital.
- Do not imply live bedside feeds, EHR connectivity, or production security/compliance controls.
- If asked about impact, say the project is intended to demonstrate a technically grounded early-warning workflow and that clinical validation remains future work.

## Backup Artifacts

- Pending artifact path: `app/demo-backup.mp4`
  Status: not committed in the repository yet. Create before submission if a prerecorded fallback is required.
- Pending artifact path: `app/demo-sepsis-alert.png`
  Status: not committed in the repository yet. Capture before submission if a static screenshot is required.
- If a custom frontend is added later, keep it under `app/` and preserve the ADK Web UI fallback path.
