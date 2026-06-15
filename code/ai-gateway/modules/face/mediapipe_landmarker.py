from __future__ import annotations

import os
import threading
import urllib.request
from dataclasses import dataclass
from typing import Any


_DEFAULT_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)


@dataclass(frozen=True)
class MPFaceResult:
    face_count: int
    # Normalized [0..1] landmarks for first face: list[{x,y,z?}]
    landmarks0: list[dict[str, float]]
    # Blendshape categories for first face: {category_name: score [0..1]}
    blendshapes0: dict[str, float]
    # 4x4 transform matrix (row-major, len=16) for first face
    transform_matrix0: list[float] | None


_detector_lock = threading.Lock()
_detector: Any | None = None
_detector_model_path: str | None = None


def _ensure_model_file(model_path: str, model_url: str) -> str:
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    if os.path.exists(model_path) and os.path.getsize(model_path) > 0:
        return model_path
    tmp_path = model_path + ".tmp"
    urllib.request.urlretrieve(model_url, tmp_path)
    os.replace(tmp_path, model_path)
    return model_path


def _default_model_path() -> str:
    base = os.environ.get("AI_GATEWAY_MODEL_DIR") or os.path.join("/tmp", "ai-gateway-models")
    return os.path.join(base, "mediapipe", "face_landmarker.task")


def _get_detector(*, model_path: str | None = None, model_url: str | None = None) -> Any:
    global _detector, _detector_model_path
    mp = __import__("mediapipe")  # defer heavy import until needed
    from mediapipe.tasks import python  # type: ignore
    from mediapipe.tasks.python import vision  # type: ignore

    path = model_path or _default_model_path()
    url = model_url or _DEFAULT_MODEL_URL

    with _detector_lock:
        if _detector is not None and _detector_model_path == path:
            return _detector

        _ensure_model_file(path, url)
        base_options = python.BaseOptions(model_asset_path=path)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=1,
        )
        _detector = vision.FaceLandmarker.create_from_options(options)
        _detector_model_path = path
        return _detector


def _matrix_to_list16(m: Any) -> list[float] | None:
    if m is None:
        return None
    data = getattr(m, "data", None)
    if isinstance(data, (list, tuple)) and len(data) == 16:
        try:
            return [float(x) for x in data]
        except Exception:
            return None
    if isinstance(m, (list, tuple)) and len(m) == 16:
        try:
            return [float(x) for x in m]
        except Exception:
            return None
    return None


def detect_face_landmarks_and_blendshapes(
    img_rgb: Any,
    *,
    model_path: str | None = None,
    model_url: str | None = None,
) -> MPFaceResult:
    """
    `img_rgb` must be a HxWx3 RGB numpy array.
    Returns only the first face (num_faces=1).
    """
    mp = __import__("mediapipe")  # defer
    detector = _get_detector(model_path=model_path, model_url=model_url)

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
    res = detector.detect(mp_image)

    face_landmarks = getattr(res, "face_landmarks", None) or []
    face_blendshapes = getattr(res, "face_blendshapes", None) or []
    matrices = getattr(res, "facial_transformation_matrixes", None) or []

    if not face_landmarks:
        return MPFaceResult(face_count=0, landmarks0=[], blendshapes0={}, transform_matrix0=None)

    lms0 = face_landmarks[0] or []
    landmarks0: list[dict[str, float]] = []
    for lm in lms0:
        x = getattr(lm, "x", None)
        y = getattr(lm, "y", None)
        z = getattr(lm, "z", None)
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            d: dict[str, float] = {"x": float(x), "y": float(y)}
            if isinstance(z, (int, float)):
                d["z"] = float(z)
            landmarks0.append(d)

    blend: dict[str, float] = {}
    if face_blendshapes:
        cats = face_blendshapes[0] or []
        for bs in cats:
            name = getattr(bs, "category_name", None)
            score = getattr(bs, "score", None)
            if isinstance(name, str) and isinstance(score, (int, float)):
                blend[name] = float(score)

    mat0 = _matrix_to_list16(matrices[0]) if matrices else None
    return MPFaceResult(face_count=1, landmarks0=landmarks0, blendshapes0=blend, transform_matrix0=mat0)

