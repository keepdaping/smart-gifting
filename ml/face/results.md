# Face check: evaluation

**Models (pre-trained, not trained by us):** YuNet finds the face and five landmarks; SFace turns
the aligned face into a 128-number faceprint. Two faceprints are compared with cosine similarity.
The app accepts a match at **0.363**, OpenCV's recommended threshold for SFace.

## Results on the AT&T (ORL) Database of Faces

40 consenting volunteers, 10 photos each (400 photos), every pair compared.

| Measure | Value |
|---|---|
| Genuine pairs (same person) | 1,800 |
| Impostor pairs (different people) | 78,000 |
| Photos where no usable face was found | 0 |
| **False reject rate** (right person refused) at 0.363 | **0.0%** (0 of 1,800) |
| **False accept rate** (stranger accepted) at 0.363 | **0.18%** (137 of 78,000) |
| ROC-AUC | 1.000 |
| Equal error rate | 0.055% (at threshold 0.404) |
| Mean similarity, same person / different people | 0.823 / 0.080 |

ROC curve: `results/roc-orl-at-t.png`. Raw numbers: `results/metrics-orl-at-t.json`.

## What this does and does not show

* It shows the pipeline works: faces are found and matched reliably on clean photos.
* ORL photos were taken in one lab, mostly of white European adults, in even light. They are much
  easier than phone selfies at a Kampala till, and they do not represent our users. Real error
  rates will be higher.
* **Next step:** run the same script on consented photos of our group and volunteers (several
  phones, indoor and outdoor light, different days) and report the rates separately:

      python -m ml.face.evaluate path/to/our_faces --name "Group volunteers"

  One sub-folder per person. Only run this with written consent, and delete the photos afterwards.
* There is no liveness check: a good printed photo or a screen could fool the camera. The cashier
  sees the person in front of them, the check is one layer among several (one-time code, single-use
  voucher, fraud check), and three failed matches force the one-time code.
