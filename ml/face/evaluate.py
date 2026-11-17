"""Evaluate face matching on a folder of labelled photos.

Folder layout: one sub-folder per person, any number of photos each.

    python -m ml.face.evaluate path/to/faces --name "ORL (AT&T)"

Every pair of photos of the same person is a genuine pair; every pair of photos
of different people is an impostor pair. We report, at the app's threshold:
  * FAR (false accept rate): impostor pairs wrongly accepted as the same person;
  * FRR (false reject rate): genuine pairs wrongly rejected;
plus ROC-AUC and the equal error rate, and save the ROC curve.

Use this on consented photos of your own group too (different days, lighting
and phones), because public datasets do not represent Ugandan users well.
"""
from __future__ import annotations

import argparse
import itertools
import re
import json
from pathlib import Path

import numpy as np

from ml.face import service

IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".pgm", ".ppm", ".bmp", ".webp"}
HERE = Path(__file__).resolve().parent


def load_faceprints(folder: Path):
    import cv2
    people, prints, skipped = [], [], []
    for person in sorted(p for p in folder.iterdir() if p.is_dir()):
        for photo in sorted(person.iterdir()):
            if photo.suffix.lower() not in IMAGE_TYPES:
                continue
            image = cv2.imread(str(photo))
            try:
                prints.append(service.embed(image))
                people.append(person.name)
            except service.FaceError as exc:
                skipped.append(f"{person.name}/{photo.name}: {exc}")
    return people, np.vstack(prints), skipped


def pair_scores(people, prints):
    sims = prints @ prints.T
    genuine, impostor = [], []
    for i, j in itertools.combinations(range(len(people)), 2):
        (genuine if people[i] == people[j] else impostor).append(float(sims[i, j]))
    return np.array(genuine), np.array(impostor)


def rates(genuine, impostor, threshold):
    far = float(np.mean(impostor >= threshold))
    frr = float(np.mean(genuine < threshold))
    return far, frr


def roc(genuine, impostor):
    thresholds = np.unique(np.concatenate([genuine, impostor, [-1.0, 1.0]]))
    tpr = np.array([np.mean(genuine >= t) for t in thresholds])
    fpr = np.array([np.mean(impostor >= t) for t in thresholds])
    order = np.argsort(fpr)
    auc = float(np.trapezoid(tpr[order], fpr[order])) if hasattr(np, "trapezoid") else float(np.trapz(tpr[order], fpr[order]))
    frr = 1 - tpr
    k = int(np.argmin(np.abs(fpr - frr)))
    return fpr, tpr, thresholds, auc, float((fpr[k] + frr[k]) / 2), float(thresholds[k])


def plot(fpr, tpr, far, frr, name, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.2, 4.6), dpi=150)
    ax.plot(fpr, tpr, color="#16845B", lw=2, label="SFace (cosine similarity)")
    ax.scatter([far], [1 - frr], color="#8A5A12", zorder=3,
               label=f"App threshold {service.MATCH_THRESHOLD}")
    ax.plot([0, 1], [0, 1], color="#BBBBBB", lw=1, ls="--", label="Chance")
    ax.set_xscale("symlog", linthresh=0.001)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.01)
    ax.set_xlabel("False accept rate (strangers accepted)")
    ax.set_ylabel("Genuine accept rate (right person accepted)")
    ax.set_title(f"Face matching ROC: {name}")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--name", default=None, help="dataset name for the report")
    parser.add_argument("--out", type=Path, default=HERE / "results")
    args = parser.parse_args(argv)
    name = args.name or args.folder.name
    people, prints, skipped = load_faceprints(args.folder)
    genuine, impostor = pair_scores(people, prints)
    far, frr = rates(genuine, impostor, service.MATCH_THRESHOLD)
    fpr, tpr, _, auc, eer, eer_t = roc(genuine, impostor)
    args.out.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"-+", "-", "".join(c if c.isalnum() else "-" for c in name.lower())).strip("-")
    plot(fpr, tpr, far, frr, name, args.out / f"roc-{slug}.png")
    result = {
        "dataset": name,
        "people": len(set(people)),
        "photos_used": len(people),
        "photos_skipped": len(skipped),
        "genuine_pairs": int(len(genuine)),
        "impostor_pairs": int(len(impostor)),
        "threshold": service.MATCH_THRESHOLD,
        "far": round(far, 5),
        "frr": round(frr, 5),
        "false_accepts": int(np.sum(impostor >= service.MATCH_THRESHOLD)),
        "false_rejects": int(np.sum(genuine < service.MATCH_THRESHOLD)),
        "roc_auc": round(auc, 5),
        "eer": round(eer, 5),
        "eer_threshold": round(eer_t, 3),
        "genuine_mean": round(float(genuine.mean()), 3),
        "impostor_mean": round(float(impostor.mean()), 3),
        "impostor_max": round(float(impostor.max()), 3),
    }
    (args.out / f"metrics-{slug}.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    for line in skipped[:10]:
        print("skipped:", line)
    return result


if __name__ == "__main__":
    main()
