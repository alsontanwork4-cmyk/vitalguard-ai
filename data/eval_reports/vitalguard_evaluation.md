# VitalGuard Evaluation Report

| Dataset | Kind | Alert Minute | Severity | Expected Pattern | Pattern Minute | First Detected Patterns | Passed |
| --- | --- | ---: | --- | --- | ---: | --- | --- |
| sepsis_onset | scenario | 16 | WARNING | sepsis_triad | 21 | desaturation_trend | True |
| compensatory_shock | scenario | 28 | WARNING | compensatory_tachycardia | 28 | compensatory_tachycardia | True |
| respiratory_deterioration | scenario | 23 | WARNING | desaturation_trend | 23 | desaturation_trend | True |
| stable_postop | scenario | - | INFO | - | - | - | True |
| vitaldb_case_4096.csv | vitaldb | 1 | CRITICAL | - | - | - | True |
| degraded_vitaldb_case_4096.csv | vitaldb_degraded | 1 | CRITICAL | - | - | - | True |

## Recovery Notes

- Real VitalDB evaluation proves the loader can normalize a public case into the monitor schema.
- Degraded VitalDB evaluation removes temperature and creates intermittent NIBP gaps to verify recovery mode.
- Stable synthetic scenario is expected to remain INFO with no intervention.
