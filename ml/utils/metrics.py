"""
Evaluation metrics for binary anomaly detection.

Because the dataset is heavily imbalanced (~2.9% anomaly), accuracy alone
is misleading.  Precision, recall, and F1 are the primary metrics.
"""

from typing import Dict, Any, Optional

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score,
)


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Compute classification metrics for binary anomaly detection.

    Args:
        y_true: ground-truth labels (0/1)
        y_pred: predicted labels (0/1)
        y_prob: predicted probabilities for the positive class (optional, for AUC)
    """
    cm = confusion_matrix(y_true, y_pred)

    metrics: Dict[str, Any] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "confusion_matrix": cm.tolist(),
    }

    if y_prob is not None and len(np.unique(y_true)) > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))

    return metrics


def format_metrics(m: Dict[str, Any]) -> str:
    """Format metrics dict as a readable multi-line string."""
    lines = [
        f"  Accuracy:  {m['accuracy']:.4f}",
        f"  Precision: {m['precision']:.4f}",
        f"  Recall:    {m['recall']:.4f}",
        f"  F1:        {m['f1']:.4f}",
    ]
    if "roc_auc" in m:
        lines.append(f"  ROC-AUC:   {m['roc_auc']:.4f}")
    if "confusion_matrix" in m:
        cm = m["confusion_matrix"]
        lines.append(f"  Confusion Matrix:")
        lines.append(f"    TN={cm[0][0]:>7,}  FP={cm[0][1]:>7,}")
        lines.append(f"    FN={cm[1][0]:>7,}  TP={cm[1][1]:>7,}")
    return "\n".join(lines)
