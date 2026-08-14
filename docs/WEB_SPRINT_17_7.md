# Sprint 17.7 — Framework-Weighted Risk Heatmap

Sprint 17.7 adds framework-native control weighting and a dashboard heatmap of weighted control exposure.

- CMMC / NIST SP 800-171 assessments use official SPRS deduction values.
- Omni CCF assessments use the relative 1–10 Control Weighting values in Column F. Zero is preserved only for deprecated/unscored controls such as TDA-11.2.
- CCF authority mappings begin at Column G; Control Weighting is not treated as an external authority.
- MET controls contribute zero exposure, NOT MET controls contribute their framework weight, NOT APPLICABLE controls are excluded, and unassessed weight is reported separately as unknown.
- Domain exposure is `finding weight / assessed applicable weight` and is presented in five visual states: none, low, moderate, high, and critical.

The visualization deliberately does not infer likelihood. It is a weighted control-exposure heatmap, distinct from a conventional likelihood-by-impact risk matrix.
