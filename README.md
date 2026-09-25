# Spectral Agent Bench — author review

A static GitHub Pages workspace for reviewing spectral benchmark examples, inspired by [SpectralBench's review page](https://yuxi120407.github.io/SpectralBench/review.html). The implementation is original; it does not copy the reference site's dataset or publication assets.

**Website:** https://rteehas.github.io/spectral_agent_bench/  
**Review alias:** https://rteehas.github.io/spectral_agent_bench/review.html

The live dataset, [`docs/data/benchmark.json`](docs/data/benchmark.json), contains two active questions for [Gleason et al. (2024)](papers/gleason-2024-cu-oxidation/README.md), with minimal input bundles and verification targets. Q1 has an executed offline candidate workflow; Q8 covers live search and fresh simulations and remains partially validated. The four fictional demonstration tasks are preserved separately in [`docs/data/benchmark.examples.json`](docs/data/benchmark.examples.json) as a reference; they are not loaded by the website.

## Review workflow

- Browse papers and expand a step, subhypothesis, or subquestion. Each example contains **Inputs → Orchestrator prompt → Verification → Ground truth reasoning**.
- Search by paper, author, DOI, question, input filename, background, or example ID. Combine category, facility, and verdict filters.
- Record **Correct**, **Needs revision**, or **Unsure**, with optional comments.
- Reviews save in the current browser, separately for each dataset ID. They are **not sent to a server or shared between reviewers**.
- Use **Export reviews** to download JSON and send it to the maintainer. **Import reviews** restores or merges a file from the same dataset, retaining the more recent review for each scenario. Importing multiple reviewers into one browser does not preserve separate identities; keep original files to retain each reviewer's feedback.
- **Open GitHub issue** prepares a draft with the scenario and feedback. The reviewer must be signed into GitHub and submit it themselves. Long comments are truncated in issue URLs; attach the exported JSON for full text.
- Scenario links use `#scenario-DEMO-001`, for example. Opening a direct link expands its paper and scenario.

Browser storage can be cleared by the browser or unavailable in private mode; export files are the durable copy. Verdict filters update after leaving a scenario so choosing a verdict does not interrupt comment entry.

## Add real benchmark examples

### Instructions for labeling agents

1. Read [`docs/data/benchmark.examples.json`](docs/data/benchmark.examples.json) for complete examples of the schema, optional paper links, inputs, orchestrator prompts, verification files/figures, and ground truth reasoning. Its contents and linked assets are synthetic demonstrations, not labels or evidence for real papers.
2. Populate [`docs/data/benchmark.json`](docs/data/benchmark.json) **from scratch using the actual papers and supplied data**. Use the reference for structure only. Do not copy its fictional paper records, task content, values, reasoning, `DEMO-*` IDs, or `data/demo/` assets into the real dataset. Leave the reference JSON intact.
3. Add real paper records to the active file's `papers` array. Keep `demo: false`, use stable, unique paper/task IDs, and link the specific input files and verification evidence for each task. Populate `groundTruthReasoning` from the actual evidence; do not invent missing results.
4. Run `python3 scripts/validate_data.py` before publishing. The site loads only `benchmark.json`; it never falls back to the reference examples. An empty `papers` array intentionally displays “No examples published yet.”

The starting active dataset is:

```json
{
  "schemaVersion": 2,
  "datasetId": "spectral-agent-v1",
  "title": "Spectral Agent Bench",
  "demo": false,
  "papers": []
}
```

Change `datasetId` for releases that materially change questions, inputs, prompts, or verification criteria so old verdicts are not silently reused. Keep paper and scenario IDs stable within a dataset release. The `scenarios` list contains tasks rather than compound records. The reference dataset retains its separate `spectral-agent-demo-v2` ID.

Each example has:

- `kind`: `Step`, `Subhypothesis`, or `Subquestion`.
- `title`: the specific step, hypothesis, or question to review.
- `inputs`: the exact data files used by this task, with a name, URL, and description.
- `prompt.background` and `prompt.instruction`: background and directions for the LLM agent orchestrator. The site automatically inserts all input filenames, descriptions, and absolute clickable URLs between these two parts. Verification files are not included in the agent prompt.
- `verification.description`: how to compare the agent's output.
- `groundTruthReasoning`: a step-by-step worked solution in plain text. For each step, name the tools/programs used, explain the operation and its purpose, and state the resulting output or finding. Distinguish solving the question from evaluator-side comparison with a held-back reference, and identify the execution record where available. Shown after Verification and excluded from the orchestrator prompt. Paragraph breaks are preserved. If omitted, the section states that reasoning has not been added yet.
- `verification.data`: ground-truth file links, and/or `verification.figures`: comparison images from the paper, with captions and optional source links. At least one file or figure is required. Either list may be omitted or empty.
- `verification.thresholds` (optional): notes at the end of Verification, after reference data, figures and methods. Provide `origin` and `generatedBy` metadata and a `provenance` string displayed verbatim, plus `notes` entries with `title` and `description` (or a legacy `description` string). Each note title is bold and followed by a colon. Optional `data` file links appear as a final Comparison Policy note. Identify who defined/generated the thresholds and distinguish benchmark choices from paper-reported values. These fields are excluded from the agent prompt.
- `verification.methods` (optional): worked workflow and checker file links, displayed separately from ground-truth data and excluded from the agent prompt.

Example task (replace the example paths with files you add):

```json
{
  "id": "STEP-001",
  "kind": "Step",
  "title": "Estimate the reference contributions to the measured spectrum",
  "inputs": [
    {
      "name": "spectrum.json",
      "url": "data/inputs/spectrum.json",
      "description": "Target spectrum with energy and normalized signal arrays."
    },
    {
      "name": "references.json",
      "url": "data/inputs/references.json",
      "description": "Reference spectra on the same energy axis."
    }
  ],
  "prompt": {
    "background": "Relevant preparation, measurement, and analysis context from the paper.",
    "instruction": "Coordinate loading, validation, and fitting of these files. Return fitted coefficients, residuals, and an overlay plot."
  },
  "groundTruthReasoning": "Explain why the expected coefficients follow from the data and what conclusions the fit does or does not justify.",
  "verification": {
    "description": "Compare the coefficients with the ground truth and the overlay with the paper's figure.",
    "data": [
      {
        "name": "expected_coefficients.json",
        "url": "data/verification/expected_coefficients.json",
        "description": "Expected coefficients."
      }
    ],
    "figures": [
      {
        "image": "assets/evidence/paper-001-figure-2.png",
        "label": "Figure 2 · page 4",
        "caption": "Plot extracted from the paper PDF for comparison.",
        "url": "assets/papers/paper-001.pdf#page=4"
      }
    ]
  }
}
```

Paper records still require `id`, `title`, `authors`, `category`, `facility`, and `scenarios`. The dataset object still requires `schemaVersion`, `datasetId`, `title`, `demo`, and `papers`.

Optional paper fields:

- `doi`: a bare DOI, for example `10.1234/example`.
- `pdf`: an HTTPS URL or a path relative to `docs/`, such as `assets/papers/paper-001.pdf`.
- `dataUrl`: an optional open-data URL (for example, a Zenodo record) or local data file path. Displays **Open data** when supplied.
- `codeUrl`: an optional open-code URL (for example, the study’s GitHub repository) or local code file path. Displays **Open code** when supplied.
- `evidence`: a list using the same format as scenario evidence, displayed under **Key paper evidence**.

These resource links appear below the paper title and metadata when the paper is expanded. Omit either field when unavailable; do not add an empty string. The first paper in the reference JSON links to the reference dataset and source repository to illustrate both fields.


Comparison figure and paper evidence fields:

- `image`: required for comparison figures; an HTTPS URL or relative asset path, such as `assets/evidence/paper-001-page-4.png`.
- `url`: an HTTPS source link or local PDF path. Use a PDF fragment such as `#page=4` to point to a page.

Put your figures and PDFs inside `docs/assets/`. All files under `docs/` are published. Add only material you intend to share publicly and have permission to redistribute. Relative paths (without an initial `/`) work correctly under the GitHub project URL. External figures must allow loading from other sites. Text is displayed as plain text, not HTML or Markdown. Categories, facilities, and counts are computed from the data. File lists and verification data support JSON, CSV, HDF5, and other formats via ordinary links; the website does not parse or execute those files.

The reference examples’ demonstration input and ground-truth JSON files remain in `docs/data/demo/` so their links can still be inspected. Recreate them with `python3 scripts/generate_demo_data.py`. They are deterministic synthetic signals, not experimental spectra. Demo comparison plots are labeled as synthetic; replace them with actual PDF figure crops for real papers.

## Preview and validate

No dependencies or build step are required. From the repository root:

```sh
python3 scripts/validate_data.py
python3 scripts/validate_data.py docs/data/benchmark.examples.json
node --check docs/assets/app.js
python3 -m http.server 8765 --directory docs
```

Open http://localhost:8765. Use an HTTP server rather than opening the HTML file directly, because the page fetches its JSON dataset.

## GitHub Pages deployment

The workflow in `.github/workflows/pages.yml` validates the dataset and deploys **only `docs/`** on pushes to `main`. Pull requests run validation without deployment. Each deployment versions the JavaScript, stylesheet, and dataset requests together so a reload does not mix cached files from earlier releases.

In the repository's **Settings → Pages**, set **Source** to **GitHub Actions**. Once enabled, each successful push publishes the site at the URL above. Deployment status appears under **Actions → Deploy review site**.

## File map

- `docs/index.html`: review workspace and metadata.
- `docs/review.html`: compatibility redirect preserving query strings and scenario links.
- `docs/assets/style.css`: responsive styles.
- `docs/assets/app.js`: filtering, evidence viewer, local review state, JSON import/export, and issue drafts.
- `docs/data/benchmark.json`: active real benchmark dataset.
- `docs/data/benchmark.examples.json`: preserved fictional examples for labeling agents to consult; never loaded by the review page.
- `scripts/validate_data.py`: schema, duplicate-ID, input, verification, and local-asset checks.

There are no analytics, external fonts, third-party scripts, API keys, or backend services. GitHub Pages itself is public hosting, not an author-only authentication system.
