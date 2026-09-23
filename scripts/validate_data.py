#!/usr/bin/env python3
"""Validate the public benchmark dataset before deployment (standard library only)."""
import json
import math
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
    require(data.get('schemaVersion') == 1, 'schemaVersion must be 1')
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
            for field in ('id', 'title', 'edge', 'prompt'):
                text(scenario.get(field), f'Scenario {field}')
            sid = scenario['id']
            require(bool(re.fullmatch(r'[A-Za-z0-9_-]+', sid)) and sid not in ('__proto__', 'constructor', 'prototype'), 'Scenario IDs must be URL-safe and non-reserved')
            require(sid not in scenario_ids, f'Duplicate scenario ID: {sid}')
            scenario_ids.add(sid)
            truth = scenario.get('groundTruth')
            require(isinstance(truth, dict) and bool(truth), f'{sid}: groundTruth must be a nonempty object')
            for key, value in truth.items():
                text(key, 'Ground truth field'); text(value, 'Ground truth value')
            rubric = scenario.get('rubric')
            require(isinstance(rubric, list) and bool(rubric), f'{sid}: rubric must be a nonempty list')
            for row in rubric:
                require(isinstance(row, dict), 'Rubric row must be an object')
                text(row.get('criterion'), 'Rubric criterion'); text(row.get('answer'), 'Rubric answer')
                points = row.get('points')
                require(type(points) in (int, float) and math.isfinite(points) and points >= 0, 'Rubric points must be finite nonnegative numbers')
            evidence(scenario.get('evidence', []))
    return len(paper_ids), len(scenario_ids)


if __name__ == '__main__':
    try:
        path = Path(sys.argv[1]) if len(sys.argv) > 1 else PUBLIC / 'data' / 'benchmark.json'
        papers, scenarios = validate(json.loads(path.read_text()))
        print(f'Valid dataset: {papers} papers, {scenarios} scenarios.')
    except (ValueError, OSError, TypeError) as exc:
        sys.exit(f'Dataset validation failed: {exc}')
