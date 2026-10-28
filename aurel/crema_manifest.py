"""Offline metadata audit; does not validate audio or run a model."""
import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter
from pathlib import Path

REVISION = '1658cd342dff90010aa843eaeebd53610a08b1dc'
EMOTIONS = ('A', 'D', 'F', 'H', 'N', 'S')
SENTENCES = {'IEO', 'IOM', 'DFA', 'IWL'}
TARGETS = {'NEU': ('neutral', 'N'), 'HAP': ('happy', 'H')}


def rows(data, required):
    reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig')))
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)) or not set(required) <= set(fields):
        raise ValueError('missing or duplicate CSV columns')
    result = list(reader)
    if not result or any(None in row or any(v is None for v in row.values()) for row in result):
        raise ValueError('empty or malformed CSV')
    return result


def integer(value):
    if not re.fullmatch(r'[0-9]+', value):
        raise ValueError('expected nonnegative integer')
    return int(value)


def build_manifest(votes_bytes, mapping_bytes, revision):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('revision must be a full lowercase commit SHA')
    mapping = {}
    for row in rows(mapping_bytes, ['Stimulus_Number', 'Filename']):
        key = integer(row['Stimulus_Number'])
        if key == 0 or key >= 100000 or key in mapping:
            raise ValueError('invalid or duplicate stimulus number')
        mapping[key] = row['Filename']
    table = rows(votes_bytes, ['', 'fileName', 'numResponses', *EMOTIONS])
    votes_hash = hashlib.sha256(votes_bytes).hexdigest()
    mapping_hash = hashlib.sha256(mapping_bytes).hexdigest()
    seen, clips = set(), set()
    records = []
    for row in table:
        row_id = integer(row[''])
        modality, clip_number = divmod(row_id, 100000)
        if modality not in (1, 2, 3) or row_id in seen:
            raise ValueError('unknown modality or duplicate annotation row')
        seen.add(row_id)
        if mapping.get(clip_number) != row['fileName']:
            raise ValueError('stimulus mapping mismatch')
        if modality != 1:
            continue
        clip = row['fileName']
        if clip in clips:
            raise ValueError('duplicate audio-only clip')
        clips.add(clip)
        match = re.fullmatch(r'(\d{4})_([A-Z]{3})_(ANG|DIS|FEA|HAP|NEU|SAD)_(LO|MD|HI|XX)', clip)
        if not match:
            raise ValueError('unexpected clip filename')
        speaker, sentence, intended, intensity = match.groups()
        votes = {key: integer(row[key]) for key in EMOTIONS}
        total = integer(row['numResponses'])
        if sum(votes.values()) != total:
            raise ValueError('vote total mismatch')
        reasons = []
        if sentence not in SENTENCES:
            reasons.append('sentence_out_of_scope')
        if intended not in TARGETS:
            reasons.append('emotion_out_of_scope')
        target, code = TARGETS.get(intended, (None, None))
        fraction = votes[code] / total if code and total else None
        if not total:
            reasons.append('zero_votes')
        elif code:
            if votes[code] * 5 < total * 3:
                reasons.append('target_vote_fraction_below_0.60')
            winners = [k for k, v in votes.items() if v == max(votes.values())]
            if winners != [code]:
                reasons.append('target_not_unique_majority')
        path = f'AudioWAV/{clip}.wav'
        records.append({
            'schema_version': 1, 'dataset': 'CREMA-D', 'source_revision': revision,
            'source_path': path,
            'source_url': f'https://github.com/CheyneyComputerScience/CREMA-D/blob/{revision}/{path}',
            'clip_id': clip, 'speaker_id': speaker, 'sentence_id': sentence,
            'pair_id': f'{speaker}_{sentence}', 'intended_emotion': target,
            'intended_emotion_code': intended, 'intensity': intensity,
            'annotation_path': 'processedResults/tabulatedVotes.csv',
            'annotation_sha256': votes_hash,
            'mapping_path': 'SentenceFilenames.csv',
            'mapping_sha256': mapping_hash,
            'annotation_row_id': row[''], 'annotation_modality': 'audio-only',
            'votes': votes, 'num_responses': total, 'target_vote_fraction': fraction,
            'license_urls': ['https://opendatacommons.org/licenses/odbl/1.0/',
                             'https://opendatacommons.org/licenses/dbcl/1.0/'],
            'attribution': 'Cao et al. (2014), CREMA-D, doi:10.1109/TAFFC.2014.2336244',
            'audio_sha256': None, 'bytes': None, 'sample_rate': None,
            'channels': None, 'duration_seconds': None,
            'status': 'excluded' if reasons else 'metadata_eligible',
            'exclusion_reasons': reasons, 'human_review_status': 'pending',
        })
    if not records:
        raise ValueError('no audio-only rows')
    return sorted(records, key=lambda item: item['clip_id'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--votes', type=Path, required=True)
    parser.add_argument('--mapping', type=Path, required=True)
    parser.add_argument('--source-revision', required=True,
                        help='Commit actually used to obtain both input files; not inferred')
    parser.add_argument('--output', type=Path, required=True,
                        help='New output directory; existing directories are never overwritten')
    args = parser.parse_args()
    try:
        records = build_manifest(args.votes.read_bytes(), args.mapping.read_bytes(), args.source_revision)
        args.output.mkdir(parents=True, exist_ok=False)
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Input/output error: {exc}\n')
    summary = {'audio_validated': False, 'source_revision': args.source_revision,
               'source_revision_verified_by_tool': False,
               'audio_only_rows': len(records),
               'statuses': dict(Counter(r['status'] for r in records)),
               'exclusion_reason_counts': dict(Counter(reason for r in records for reason in r['exclusion_reasons']))}
    with (args.output / 'manifest.jsonl').open('w', encoding='utf-8', newline='\n') as out:
        for record in records:
            out.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
