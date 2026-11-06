| Detector | Precision | Recall | F1 | False-positive rate |
|---|---|---|---|---|
| Fixed rules | 0.982 | 0.750 | 0.850 | 0.001 |
| Isolation Forest | 0.895 | 0.944 | 0.919 | 0.005 |

Isolation Forest ROC-AUC: 0.999
Recall on blatant fraud  - rules: 1.000, iforest: 1.000
Recall on subtle fraud   - rules: 0.526, iforest: 0.895

NOTE: synthetic data. Results show the method works on injected patterns, not real-world performance.
