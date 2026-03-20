"""
Template vocabulary builder for the HDFS preprocessing pipeline.

Reads the canonical event templates from HDFS.log_templates.csv (produced by
the Loghub Drain parser) and builds a token-to-integer mapping suitable for
embedding layers.

Vocabulary layout:
    0  = PAD   (padding token for short sequences)
    1  = E1    (first event template)
    ...
    29 = E29   (last event template)
    30 = UNK   (unknown / unseen template fallback)
"""

import csv
import json
from pathlib import Path
from typing import Dict, Tuple

PAD_TOKEN = "PAD"
UNK_TOKEN = "UNK"
PAD_ID = 0
UNK_ID_OFFSET = 1  # placed right after the last template


def build_vocab_from_csv(
    templates_path: Path,
) -> Tuple[Dict[str, int], Dict[int, str], Dict[str, str]]:
    """
    Build token-to-id and id-to-token mappings from HDFS.log_templates.csv.

    Returns:
        token_to_id:  {"PAD": 0, "E1": 1, ..., "E29": 29, "UNK": 30}
        id_to_token:  reverse of the above
        templates:    {"E1": "[*]Adding an already existing block[*]", ...}
    """
    templates: Dict[str, str] = {}
    with open(templates_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            event_id = row["EventId"].strip()
            template = row["EventTemplate"].strip()
            templates[event_id] = template

    token_to_id: Dict[str, int] = {PAD_TOKEN: PAD_ID}
    sorted_events = sorted(templates.keys(), key=lambda e: int(e[1:]))
    for idx, event_id in enumerate(sorted_events, start=1):
        token_to_id[event_id] = idx

    unk_id = len(token_to_id)
    token_to_id[UNK_TOKEN] = unk_id

    id_to_token = {v: k for k, v in token_to_id.items()}

    return token_to_id, id_to_token, templates


def save_vocab(
    path: Path,
    token_to_id: Dict[str, int],
    id_to_token: Dict[int, str],
    templates: Dict[str, str],
) -> None:
    """Persist vocabulary to a JSON file."""
    payload = {
        "token_to_id": token_to_id,
        "id_to_token": {str(k): v for k, v in id_to_token.items()},
        "templates": templates,
        "vocab_size": len(token_to_id),
        "pad_id": PAD_ID,
        "unk_id": token_to_id[UNK_TOKEN],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)


def load_vocab(path: Path) -> Tuple[Dict[str, int], Dict[int, str], Dict[str, str]]:
    """Load vocabulary from a previously saved JSON file."""
    with open(path) as f:
        payload = json.load(f)
    token_to_id = payload["token_to_id"]
    id_to_token = {int(k): v for k, v in payload["id_to_token"].items()}
    templates = payload["templates"]
    return token_to_id, id_to_token, templates
