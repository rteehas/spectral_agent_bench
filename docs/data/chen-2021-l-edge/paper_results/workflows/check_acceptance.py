#!/usr/bin/env python3
"""Require publication agreement AND independently reviewed raw-data execution.

Reviews are evaluator-owned evidence, never files accepted from a solver.
A stale/missing review or a failed paper comparison always prevents acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def manifest(output):
    return {str(p.relative_to(output)): sha(p)
            for p in sorted(output.rglob('*')) if p.is_file()}


def verify(question, output, inputs, truth, reviews):
    errors = []
    artifacts = manifest(output)
    manifest_hash = hashlib.sha256(json.dumps(artifacts, sort_keys=True,
                                  separators=(',', ':')).encode()).hexdigest()
    checker = Path(__file__).resolve().with_name(f'verify_{question.lower()}.py')
    elements = ('Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu')
    native_hashes = {f'inputs/{e}.jsonl.gz': sha(inputs / f'{e}.jsonl.gz')
                     for e in elements if (inputs / f'{e}.jsonl.gz').is_file()}
    target_names = (['paper.pdf', 'figure4_traces.csv', 'figure4_calibration.json',
                     'figure4_comparison_contract.json'] if question == 'R1' else
                    ['figure5.png', 'figure5_comparison_contract.json'])
    target_hashes = {name: sha(truth / name) for name in target_names
                     if (truth / name).is_file()}
    with tempfile.TemporaryDirectory(prefix='chen-paper-gate-') as tmp:
        paper_report = Path(tmp) / 'comparison.json'
        command = [sys.executable, str(checker), '--output', str(output),
                   '--truth', str(truth), '--out', str(paper_report)]
        if question == 'R2':
            command += ['--inputs', str(inputs)]
        completed = subprocess.run(command, text=True, capture_output=True)
        if paper_report.is_file():
            publication = json.loads(paper_report.read_text())
        else:
            publication = {'error': completed.stderr[-3000:]}
        field = 'paper_numerical_pass' if question == 'R1' else 'paper_plot_pass'
        paper_pass = completed.returncode == 0 and publication.get(field) is True
        if not paper_pass:
            errors.append('Mandatory comparison against the published figure failed or could not execute')
    checks = {'publication_agreement': paper_pass}
    review_hashes = {}
    for filename in ['workflow_execution.json', 'scientific_review.json']:
        path = reviews / filename
        try:
            data = json.loads(path.read_text())
            review_hashes[filename] = sha(path)
            case = data['cases'][question]
            if filename == 'workflow_execution.json':
                required = ['pass', 'input_boundary_checked', 'source_code_inspected',
                            'replay_matches_outputs']
                passed = all(case.get(key) is True for key in required)
                passed &= case.get('artifact_sha256') == artifacts
                passed &= len(native_hashes) == 8 and case.get('native_input_sha256') == native_hashes
                checks['independent_raw_data_replay'] = bool(passed)
                if not passed:
                    errors.append('Independent source/code replay is missing, failed, incomplete, or bound to different native inputs/output files')
            else:
                required = ['pass', 'paper_comparison_pass', 'interpretation_supported']
                passed = all(case.get(key) is True for key in required)
                passed &= case.get('output_manifest_sha256') == manifest_hash
                passed &= len(target_hashes) == len(target_names) and case.get('paper_target_sha256') == target_hashes
                checks['independent_scientific_review'] = bool(passed)
                if not passed:
                    errors.append('Scientific review is missing, failed, or bound to different outputs/publication targets')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            checks[filename] = False
            errors.append(f'Unavailable evaluator review {filename}: {exc}')
    audit_path = reviews / 'verification_audit.json'
    try:
        audit = json.loads(audit_path.read_text())
        audit_files = audit['audited_file_sha256']
        expected = {f'workflows/{checker.name}': sha(checker)}
        expected.update({f'verification/figures/{k}': v for k, v in target_hashes.items()})
        audited = all(audit_files.get(k) == v for k, v in expected.items())
        case = audit[question]
        control_field = 'all_controls_pass' if question == 'R1' else 'all_mask_controls_pass'
        audited &= case.get(control_field) is True
        checks['independent_verifier_audit'] = bool(audited)
        review_hashes[audit_path.name] = sha(audit_path)
        if not audited:
            errors.append('Independent verifier audit is missing, failed, or stale for the checker/publication targets')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        checks['independent_verifier_audit'] = False
        errors.append(f'Unavailable independent verifier audit: {exc}')
    return {'question': question, 'accepted': not errors,
            'rule': 'Publication agreement AND independent native-data execution AND scientific review; no fallback gate',
            'checks': checks, 'errors': errors, 'paper_comparison': publication,
            'output_manifest_sha256': manifest_hash, 'artifact_sha256': artifacts,
            'paper_checker_sha256': sha(checker), 'paper_target_sha256': target_hashes,
            'native_input_sha256': native_hashes, 'evaluator_review_sha256': review_hashes}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--question', choices=['R1', 'R2'], required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--truth', type=Path, required=True)
    p.add_argument('--reviews', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    result = verify(args.question, args.output, args.inputs, args.truth, args.reviews)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'question': args.question, 'accepted': result['accepted'],
                      'checks': result['checks'], 'errors': result['errors']}, indent=2))
    raise SystemExit(0 if result['accepted'] else 1)


if __name__ == '__main__':
    main()
