"""Face verification for gift pickup.

Uses two small pre-trained OpenCV models (no training needed):
  * YuNet  finds the face and its five landmarks (eyes, nose, mouth corners);
  * SFace  turns the aligned face into a 128-number "faceprint".

Two faceprints are compared with cosine similarity. Scores at or above the
threshold mean "same person". Only faceprints are stored, never photos.
"""
from __future__ import annotations

import base64
import binascii
import json
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np

MODEL_DIR = Path(__file__).resolve().parent / "models"
DETECTOR_MODEL = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
RECOGNIZER_MODEL = MODEL_DIR / "face_recognition_sface_2021dec.onnx"

# OpenCV's recommended cosine threshold for SFace. Our own evaluation
# (ml/face/evaluate.py, results in ml/face/results.md) checks this choice.
MATCH_THRESHOLD = 0.363
MAX_IMAGE_BYTES = 3 * 1024 * 1024
MIN_FACE_PIXELS = 60          # faces smaller than this are too far from the camera
MIN_DETECTION_SCORE = 0.8


class FaceError(ValueError):
    """A photo that cannot be used, with a message a person can act on."""


@dataclass
class MatchResult:
    score: float
    matched: bool
    threshold: float = MATCH_THRESHOLD


_lock = threading.Lock()
_models = {}


def available() -> bool:
    """True when OpenCV and both model files are present."""
    try:
        import cv2  # noqa: F401
    except ImportError:
        return False
    return DETECTOR_MODEL.is_file() and RECOGNIZER_MODEL.is_file()


def _get_models():
    import cv2
    with _lock:
        if not _models:
            _models["detector"] = cv2.FaceDetectorYN.create(
                str(DETECTOR_MODEL), "", (320, 320), MIN_DETECTION_SCORE, 0.3, 5000)
            _models["recognizer"] = cv2.FaceRecognizerSF.create(str(RECOGNIZER_MODEL), "")
        return _models["detector"], _models["recognizer"]


def decode_image(data) -> np.ndarray:
    """Accept raw bytes or a data URL / base64 string from the browser camera."""
    import cv2
    if isinstance(data, str):
        if "," in data and data.strip().startswith("data:"):
            data = data.split(",", 1)[1]
        try:
            data = base64.b64decode(data, validate=False)
        except (binascii.Error, ValueError) as exc:
            raise FaceError("The photo could not be read. Please take it again.") from exc
    if not data:
        raise FaceError("No photo was received. Please take it again.")
    if len(data) > MAX_IMAGE_BYTES:
        raise FaceError("The photo is too large. Please take it again.")
    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FaceError("The photo could not be read. Please take it again.")
    return image


def _prepare(image: np.ndarray) -> np.ndarray:
    import cv2
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest > 1280:                          # keep detection fast on phone photos
        scale = 1280 / longest
        image = cv2.resize(image, (round(width * scale), round(height * scale)))
    elif longest < 320:                         # small photos: enlarge so YuNet sees the face
        scale = 320 / longest
        image = cv2.resize(image, (round(width * scale), round(height * scale)),
                           interpolation=cv2.INTER_CUBIC)
    return image


def detect_faces(image: np.ndarray) -> np.ndarray:
    detector, _ = _get_models()
    height, width = image.shape[:2]
    detector.setInputSize((width, height))
    _, faces = detector.detect(image)
    return faces if faces is not None else np.empty((0, 15), dtype=np.float32)


def embed(image: np.ndarray) -> np.ndarray:
    """Return the faceprint of the single face in the photo."""
    image = _prepare(image)
    faces = detect_faces(image)
    if len(faces) == 0:
        raise FaceError("No face was found. Face the camera in good light and try again.")
    if len(faces) > 1:
        faces = faces[np.argsort(-faces[:, 2] * faces[:, 3])]
        largest, second = faces[0], faces[1]
        if second[2] * second[3] > 0.5 * largest[2] * largest[3]:
            raise FaceError("More than one face is in the photo. Only the recipient should be in view.")
    face = faces[0]
    if min(face[2], face[3]) < MIN_FACE_PIXELS:
        raise FaceError("The face is too small. Move closer to the camera.")
    _, recognizer = _get_models()
    aligned = recognizer.alignCrop(image, face)
    feature = recognizer.feature(aligned).astype(np.float32).ravel()
    norm = float(np.linalg.norm(feature))
    if norm == 0:
        raise FaceError("The photo could not be used. Please take it again.")
    return feature / norm


def similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float32).ravel()
    b = np.asarray(b, dtype=np.float32).ravel()
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def compare(stored: np.ndarray, image: np.ndarray, threshold: float = MATCH_THRESHOLD) -> MatchResult:
    score = similarity(stored, embed(image))
    return MatchResult(score=round(score, 3), matched=score >= threshold, threshold=threshold)


def to_text(feature: np.ndarray) -> str:
    """Faceprint as compact text for the database (128 numbers, no photo)."""
    return json.dumps([round(float(x), 6) for x in np.asarray(feature).ravel()])


def from_text(text: str) -> np.ndarray:
    return np.asarray(json.loads(text), dtype=np.float32)
