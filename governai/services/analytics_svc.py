import math
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from api.schemas import RawPredictionPayload
from database.models import RawPrediction

BATCH_WINDOW_N = 30  # how many recent predictions to retain/consider per system
SENSITIVE_WORDS = ["gender", "race", "age", "religion", "female", "male", "nationality"]


def _is_sensitive(text: str | None) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    return any(w in text_lower for w in SENSITIVE_WORDS)


def save_raw_prediction(db: Session, system_id: str, raw_prediction: RawPredictionPayload) -> RawPrediction:
    """Persists a raw prediction and prunes rows beyond the last N for this system."""
    record = RawPrediction(
        system_id=system_id,
        input_text=raw_prediction.input_text,
        output_text=raw_prediction.output_text,
        confidence_score=raw_prediction.confidence_score,
        sensitive_flag=1 if _is_sensitive(raw_prediction.input_text) else 0,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Prune: keep only the most recent BATCH_WINDOW_N rows for this system
    stale = (
        db.query(RawPrediction.id)
        .filter(RawPrediction.system_id == system_id)
        .order_by(desc(RawPrediction.created_at))
        .offset(BATCH_WINDOW_N)
        .all()
    )
    if stale:
        stale_ids = [r.id for r in stale]
        db.query(RawPrediction).filter(RawPrediction.id.in_(stale_ids)).delete(synchronize_session=False)
        db.commit()

    return record


def _psi(reference: List[float], current: List[float], bins: int = 5) -> float:
    """Population Stability Index between two numeric samples."""
    if not reference or not current:
        return 0.0
    all_vals = reference + current
    lo, hi = min(all_vals), max(all_vals)
    if hi == lo:
        return 0.0

    def bucket_props(vals):
        counts = [0] * bins
        for v in vals:
            idx = min(bins - 1, max(0, int((v - lo) / (hi - lo) * bins)))
            counts[idx] += 1
        total = len(vals)
        return [max(c / total, 1e-4) for c in counts]  # floor avoids log(0)

    ref_props, cur_props = bucket_props(reference), bucket_props(current)
    psi = sum((c - r) * math.log(c / r) for r, c in zip(ref_props, cur_props))
    return round(psi, 3)


def calculate_batch_drift(db: Session, system_id: str) -> float:
    """
    Splits the last N predictions into an older half (reference) and a newer
    half (current), then measures how much the confidence-score distribution
    has shifted between them via PSI. Falls back to input-length distribution
    if confidence scores aren't populated.
    """
    records = (
        db.query(RawPrediction)
        .filter(RawPrediction.system_id == system_id)
        .order_by(RawPrediction.created_at.asc())
        .all()
    )
    if len(records) < 6:
        return 0.0  # not enough history for a meaningful batch comparison

    mid = len(records) // 2
    older, newer = records[:mid], records[mid:]

    ref_conf = [r.confidence_score for r in older if r.confidence_score is not None]
    cur_conf = [r.confidence_score for r in newer if r.confidence_score is not None]

    if ref_conf and cur_conf:
        drift_score = _psi(ref_conf, cur_conf)
    else:
        ref_len = [len(r.input_text) for r in older if r.input_text]
        cur_len = [len(r.input_text) for r in newer if r.input_text]
        drift_score = _psi(ref_len, cur_len) if ref_len and cur_len else 0.0

    return round(min(drift_score, 1.0), 3)  # PSI is unbounded in theory; clamp for a 0-1 scale


def calculate_batch_bias(db: Session, system_id: str) -> float:
    """
    Compares average confidence between predictions whose input mentioned a
    sensitive keyword vs. those that didn't. A larger gap = the model behaves
    (or is scored) differently on sensitive-topic inputs.
    NOTE: this is a keyword proxy, not a true protected-class fairness metric —
    the payload has no demographic field to group on. Worth flagging as a demo
    limitation to Mebin.
    """
    records = db.query(RawPrediction).filter(RawPrediction.system_id == system_id).all()

    flagged = [r.confidence_score for r in records if r.sensitive_flag and r.confidence_score is not None]
    unflagged = [r.confidence_score for r in records if not r.sensitive_flag and r.confidence_score is not None]

    if not flagged or not unflagged:
        # not enough of both groups yet — fall back to keyword density
        matches = sum(r.sensitive_flag for r in records)
        return round(min(matches / max(len(records), 1) * 0.3, 1.0), 3)

    gap = abs(sum(flagged) / len(flagged) - sum(unflagged) / len(unflagged))
    return round(min(gap * 2, 1.0), 3)