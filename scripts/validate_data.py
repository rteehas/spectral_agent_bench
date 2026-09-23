#!/usr/bin/env python3
"""Validate the public benchmark dataset before deployment (standard library only)."""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'docs'


def validate(data, public=PUBLIC):
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def text(value, field):
        require(isinstance(value, str) and bool(value.strip()), f'{field} must be a nonempty string')

    def asset(value):
        text(value, 'Asset URL')
        url = urlsplit(value)
        if url.scheme:
            require(url.scheme in ('https', 'http') and bool(url.netloc), 'Assets must use HTTP(S)')
        else:
            require(not url.netloc and not value.startswith('/'), 'Use relative asset paths for GitHub project pages')
            path = (public / unquote(url.path)).resolve()
            require(public.resolve() in path.parents, 'Asset must remain inside docs/')
            require(path.is_file(), f'Missing asset: {value}')

    def files(items, field):
        require(isinstance(items, list), f'{field} must be a list')
        names = set()
        for item in items:
            require(isinstance(item, dict), f'{field} entries must be objects')
            text(item.get('name'), f'{field} filename')
            require(item['name'] not in names, f'Duplicate filename in {field}: {item["name"]}')
            names.add(item['name'])
            text(item.get('description'), f'{field} description')
            asset(item.get('url'))

    def evidence(items):
        require(isinstance(items, list), 'evidence must be a list')
        for item in items:
            require(isinstance(item, dict), 'Evidence entries must be objects')
            text(item.get('label'), 'Evidence label')
            text(item.get('caption'), 'Evidence caption')
            for key in ('image', 'url'):
                if key in item:
                    asset(item[key])

    require(isinstance(data, dict), 'Dataset must be an object')
    require(data.get('schemaVersion') == 2, 'schemaVersion must be 2')
    text(data.get('datasetId'), 'datasetId')
    require(bool(re.fullmatch(r'[A-Za-z0-9_-]+', data['datasetId'])), 'datasetId must be URL-safe')
    require(isinstance(data.get('demo'), bool), 'demo must be true or false')
    text(data.get('title'), 'title')
    require(isinstance(data.get('papers'), list), 'papers must be a list')
    paper_ids, scenario_ids = set(), set()
    for paper in data['papers']:
        require(isinstance(paper, dict), 'Paper must be an object')
        for field in ('id', 'title', 'authors', 'category', 'facility'):
            text(paper.get(field), f'Paper {field}')
        require(bool(re.fullmatch(r'[A-Za-z0-9_-]+', paper['id'])), 'Paper IDs must be URL-safe')
        require(paper['id'] not in paper_ids, f'Duplicate paper ID: {paper["id"]}')
        paper_ids.add(paper['id'])
        if 'doi' in paper:
            require(isinstance(paper['doi'], str) and bool(re.fullmatch(r'10\.\d{4,9}/\S+', paper['doi'])), 'Use a bare DOI, not a URL')
        for field in ('pdf', 'dataUrl', 'codeUrl'):
            if field in paper:
                asset(paper[field])
        evidence(paper.get('evidence', []))
        require(isinstance(paper.get('scenarios'), list) and paper['scenarios'], 'Each paper needs scenarios')
        for scenario in paper['scenarios']:
            require(isinstance(scenario, dict), 'Scenario must be an object')
            for field in ('id', 'title', 'kind'):
                text(scenario.get(field), f'Scenario {field}')
            sid = scenario['id']
            require(bool(re.fullmatch(r'[A-Za-z0-9_-]+', sid)) and sid not in ('__proto__', 'constructor', 'prototype'), 'Scenario IDs must be URL-safe and non-reserved')
            require(sid not in scenario_ids, f'Duplicate scenario ID: {sid}')
            scenario_ids.add(sid)
            require(scenario['kind'] in ('Step', 'Subhypothesis', 'Subquestion'), f'{sid}: invalid example kind')
            inputs = scenario.get('inputs')
            files(inputs, 'Inputs')
            require(bool(inputs), f'{sid}: at least one input file is required')
            prompt = scenario.get('prompt')
            require(isinstance(prompt, dict), f'{sid}: prompt must contain background and instruction')
            text(prompt.get('background'), 'Prompt background')
            text(prompt.get('instruction'), 'Prompt instruction')
            if 'groundTruthReasoning' in scenario:
                text(scenario['groundTruthReasoning'], 'Ground truth reasoning')
            verification = scenario.get('verification')
            require(isinstance(verification, dict), f'{sid}: verification must be an object')
            text(verification.get('description'), 'Verification description')
            data_files = verification.get('data', [])
            figures = verification.get('figures', [])
            files(data_files, 'Ground-truth data')
            files(verification.get('methods', []), 'Worked workflow and checker')
            if 'thresholds' in verification:
                thresholds = verification['thresholds']
                require(isinstance(thresholds, dict), f'{sid}: thresholds must be an object')
                for field in ('origin', 'generatedBy', 'provenance'):
                    text(thresholds.get(field), f'Thresholds {field}')
                if 'description' in thresholds:
                    text(thresholds['description'], 'Thresholds description')
                notes = thresholds.get('notes', [])
                require(isinstance(notes, list), f'{sid}: threshold notes must be a list')
                for note in notes:
                    require(isinstance(note, dict), f'{sid}: threshold notes must be objects')
                    text(note.get('title'), 'Threshold note title')
                    text(note.get('description'), 'Threshold note description')
                require(bool(notes or thresholds.get('description')), f'{sid}: thresholds need notes or a description')
                files(thresholds.get('data', []), 'Threshold policy files')
            evidence(figures)
            require(bool(data_files or figures), f'{sid}: verification needs ground-truth data or comparison figures')
            for figure in figures:
                asset(figure.get('image'))
    return len(paper_ids), len(scenario_ids)


if __name__ == '__main__':
    try:
        path = Path(sys.argv[1]) if len(sys.argv) > 1 else PUBLIC / 'data' / 'benchmark.json'
        papers, scenarios = validate(json.loads(path.read_text()))
        print(f'Valid dataset: {papers} papers, {scenarios} scenarios.')
    except (ValueError, OSError, TypeError) as exc:
        sys.exit(f'Dataset validation failed: {exc}')
