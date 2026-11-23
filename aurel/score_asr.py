"""Score matched clean/perturbed transcripts using JiWER, not toy accuracy.

Input JSONL: one row per source, with source_id, reference, clean, perturbed.
Only completed model calls belong here; an empty model answer is still scored.
Transport failures must be recorded separately, never converted to empty text.
"""
import argparse
import json
from pathlib import Path
from importlib.metadata import version

import jiwer


def score(rows):
    if not rows:
        raise ValueError("At least one matched source is required")
    seen = set()
    for row in rows:
        for key in ("source_id", "reference", "clean", "perturbed"):
            if not isinstance(row.get(key), str):
                raise ValueError(f"{key} must be a string (missing calls are not scored)")
        if not row["source_id"] or row["source_id"] in seen:
            raise ValueError("source_id must be nonempty and unique")
        seen.add(row["source_id"])
        if not row["reference"].strip():
            raise ValueError("Empty reference requires a separate silence evaluation")
    # Explicit conservative policy: preserve case and punctuation, collapse whitespace.
    normalize = lambda text: " ".join(text.split())
    refs = [normalize(row["reference"]) for row in rows]
    result = {"sources": len(rows), "jiwer_version": version("jiwer"),
              "normalization": "whitespace-only-v1; case and punctuation preserved",
              "scope": "one model and one perturbation condition; matched completed calls only"}
    for condition in ("clean", "perturbed"):
        hypotheses = [normalize(row[condition]) for row in rows]
        words = jiwer.process_words(refs, hypotheses)
        result[condition] = {"wer": words.wer, "cer": jiwer.cer(refs, hypotheses),
                             "substitutions": words.substitutions,
                             "deletions": words.deletions, "insertions": words.insertions,
                             "reference_words": words.hits + words.substitutions + words.deletions}
    result["wer_increase"] = result["perturbed"]["wer"] - result["clean"]["wer"]
    result["cer_increase"] = result["perturbed"]["cer"] - result["clean"]["cer"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    result = score(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
