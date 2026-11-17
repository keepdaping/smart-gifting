"""Live face check: the camera scans automatically and asks for head turns.

A printed photo or a phone screen cannot turn its head, so the person must:
  1. look straight at the camera,
  2. turn their head to their left and to their right (in a random order),
  3. look straight again (this frame is used for the face match).

Head turn is measured from YuNet's landmarks: how far the nose tip sits from the
midpoint between the eyes, divided by the distance between the eyes.
  ~0      looking straight
  > 0     turned to the person's own LEFT  (nose moves to the image's right)
  < 0     turned to the person's own RIGHT
Every frame must show the same person as the first one, so nobody can swap
a photo in halfway through.
"""
from __future__ import annotations

import base64
import random
import time
from dataclasses import dataclass

import numpy as np

from ml.face import service

STRAIGHT_MAX = 0.12          # |turn| below this counts as looking straight
TURN_MIN = 0.18              # |turn| above this counts as a head turn
SAME_PERSON_MIN = 0.20       # turned faces embed less reliably, so a lower bar
FINAL_SAME_PERSON_MIN = service.MATCH_THRESHOLD
TIME_LIMIT_SECONDS = 60

PROMPTS = {
    "center": "Look straight at the camera",
    "left": "Slowly turn your head to your left",
    "right": "Slowly turn your head to your right",
    "final": "Now look straight at the camera again",
}


def new_challenge(rng=random):
    turns = ["left", "right"]
    rng.shuffle(turns)
    return {"steps": ["center", *turns, "final"], "i": 0, "started": time.time(), "ref": None}


def pack(vector) -> str:
    return base64.b64encode(np.asarray(vector, dtype=np.float16).tobytes()).decode("ascii")


def unpack(text) -> np.ndarray:
    return np.frombuffer(base64.b64decode(text), dtype=np.float16).astype(np.float32)


@dataclass
class Frame:
    turn: float
    face: np.ndarray        # the YuNet row for the face
    image: np.ndarray


def read_frame(image) -> Frame:
    """Find the single face in a camera frame and measure its head turn."""
    image = service._prepare(image)
    faces = service.detect_faces(image)
    if len(faces) == 0:
        raise service.FaceError("Move your face into the oval.")
    if len(faces) > 1:
        faces = faces[np.argsort(-faces[:, 2] * faces[:, 3])]
        if faces[1][2] * faces[1][3] > 0.5 * faces[0][2] * faces[0][3]:
            raise service.FaceError("Only one person should be in view.")
    face = faces[0]
    if min(face[2], face[3]) < service.MIN_FACE_PIXELS:
        raise service.FaceError("Move a little closer to the camera.")
    right_eye_x, left_eye_x, nose_x = face[4], face[6], face[8]
    eye_gap = abs(left_eye_x - right_eye_x)
    if eye_gap < 1:
        raise service.FaceError("Face the camera so both eyes are visible.")
    turn = float((nose_x - (right_eye_x + left_eye_x) / 2) / eye_gap)
    return Frame(turn=turn, face=face, image=image)


def faceprint(frame: Frame) -> np.ndarray:
    _, recognizer = service._get_models()
    feature = recognizer.feature(recognizer.alignCrop(frame.image, frame.face)).astype(np.float32).ravel()
    return feature / (np.linalg.norm(feature) + 1e-12)


def step_reached(step, turn) -> bool:
    if step in ("center", "final"):
        return abs(turn) < STRAIGHT_MAX
    if step == "left":
        return turn >= TURN_MIN
    return turn <= -TURN_MIN


def hint(step, turn) -> str:
    """A short nudge when the person is not there yet."""
    if step in ("center", "final"):
        return PROMPTS[step]
    wanted = 1 if step == "left" else -1
    if turn * wanted > 0.05:
        return f"A little more to your {step}"
    return PROMPTS[step]


class Restart(Exception):
    """The check must start again (time limit, or a different person appeared)."""


def advance(state, image):
    """Process one camera frame. Returns (state, finished_faceprint_or_None, message).

    Raises service.FaceError for frames that cannot be used (keep scanning) and
    Restart when the check has to begin again.
    """
    if time.time() - state["started"] > TIME_LIMIT_SECONDS:
        raise Restart("That took too long. Let's start again.")
    frame = read_frame(image)
    step = state["steps"][state["i"]]
    if not step_reached(step, frame.turn):
        return state, None, hint(step, frame.turn)
    print_ = faceprint(frame)
    if state["ref"] is None:
        state["ref"] = pack(print_)
    else:
        ref = unpack(state["ref"])
        floor = FINAL_SAME_PERSON_MIN if step == "final" else SAME_PERSON_MIN
        if service.similarity(ref, print_) < floor:
            raise Restart("The face changed during the check. Let's start again with one person.")
    state["i"] += 1
    if step == "final":
        combined = unpack(state["ref"]) + print_
        return state, combined / (np.linalg.norm(combined) + 1e-12), "Done"
    return state, None, PROMPTS[state["steps"][state["i"]]]
