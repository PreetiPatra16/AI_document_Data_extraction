import argparse
import json
import re
from pathlib import Path


def normalize(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def score(expected_path: Path, actual_path: Path):
    expected = json.loads(expected_path.read_text())
    actual = json.loads(actual_path.read_text())
    actual_fields = actual.get("fields", {})
    totals = {"typed": 0, "handwritten": 0}
    matches = {"typed": 0, "handwritten": 0}
    missing = 0
    for name, spec in expected["fields"].items():
        kind = spec["kind"]
        totals[kind] += 1
        value = actual_fields.get(name, {}).get("normalized_value")
        if value is None:
            missing += 1
        elif normalize(value) == normalize(spec["value"]):
            matches[kind] += 1
    return {
        "typed_accuracy": matches["typed"] / totals["typed"] if totals["typed"] else None,
        "handwritten_accuracy": matches["handwritten"] / totals["handwritten"] if totals["handwritten"] else None,
        "missing_fields": missing,
        "false_positive_fields": len(set(actual_fields) - set(expected["fields"])),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("expected", type=Path)
    parser.add_argument("actual", type=Path)
    args = parser.parse_args()
    print(json.dumps(score(args.expected, args.actual), indent=2))
