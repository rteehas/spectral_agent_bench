# Spectral Agent Bench — author review

A static GitHub Pages workspace for reviewing spectral benchmark examples, inspired by [SpectralBench's review page](https://yuxi120407.github.io/SpectralBench/review.html). The implementation is original; it does not copy the reference site's dataset or publication assets.

**Website:** https://rteehas.github.io/spectral_agent_bench/  
**Review alias:** https://rteehas.github.io/spectral_agent_bench/review.html

The initial dataset contains **four clearly labeled, fictional demonstration tasks across three papers**. Synthetic figures are illustrative, not experimental spectra.

## Review workflow

- Browse papers and expand a step, subhypothesis, or subquestion. Each example contains **Inputs → Orchestrator prompt → Verification**.
- Search by paper, author, DOI, question, input filename, background, or example ID. Combine category, facility, and verdict filters.
- Record **Correct**, **Needs revision**, or **Unsure**, with optional comments.
- Reviews save in the current browser, separately for each dataset ID. They are **not sent to a server or shared between reviewers**.
- Use **Export reviews** to download JSON and send it to the maintainer. **Import reviews** restores or merges a file from the same dataset, retaining the more recent review for each scenario. Importing multiple reviewers into one browser does not preserve separate identities; keep original files to retain each reviewer's feedback.
- **Open GitHub issue** prepares a draft with the scenario and feedback. The reviewer must be signed into GitHub and submit it themselves. Long comments are truncated in issue URLs; attach the exported JSON for full text.
- Scenario links use `#scenario-DEMO-001`, for example. Opening a direct link expands its paper and scenario.

Browser storage can be cleared by the browser or unavailable in private mode; export files are the durable copy. Verdict filters update after leaving a scenario so choosing a verdict does not interrupt comment entry.

## Add real benchmark examples

Edit **`docs/data/benchmark.json`**. Set `demo` to `false` when replacing the fictional dataset, and use a new `datasetId` such as `spectral-agent-v1`. Change the dataset ID for releases that materially change questions, inputs, prompts, or verification criteria so old verdicts are not silently reused. Keep paper and scenario IDs stable within a dataset release.

The dataset uses `schemaVersion: 2`. The `scenarios` list now contains tasks rather than compound records. The demo dataset ID changed to `spectral-agent-demo-v2`, so verdicts on the older questions are not reused. Existing v1 review exports remain separate.

Each example has:

- `kind`: `Step`, `Subhypothesis`, or `Subquestion`.
- `title`: the specific step, hypothesis, or question to review.
- `inputs`: the exact data files used by this task, with a name, URL, and description.
- `prompt.background` and `prompt.instruction`: background and directions for the LLM agent orchestrator. The site automatically inserts all input filenames, descriptions, and absolute clickable URLs between these two parts. Verification files are not included in the agent prompt.
- `verification.description`: how to compare the agent's output.
- `verification.data`: ground-truth file links, and/or `verification.figures`: comparison images from the paper, with captions and optional source links. At least one file or figure is required. Either list may be omitted or empty.

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
  "verification": {
    "description": "Compare the coefficients with the ground truth and the overlay with the paper's figure.",
    "data": [
      {
        "name": "expected_coefficients.json",
        "url": "data/verification/expected_coefficients.json",
        "description": "Expected coefficients and allowed error tolerance."
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

These resource links appear below the paper title and metadata when the paper is expanded. Omit either field when unavailable; do not add an empty string. The first demonstration paper links to this site’s sample dataset and source repository to illustrate both fields.


Comparison figure and paper evidence fields:

- `image`: required for comparison figures; an HTTPS URL or relative asset path, such as `assets/evidence/paper-001-page-4.png`.
- `url`: an HTTPS source link or local PDF path. Use a PDF fragment such as `#page=4` to point to a page.

Put your figures and PDFs inside `docs/assets/`. All files under `docs/` are published. Add only material you intend to share publicly and have permission to redistribute. Relative paths (without an initial `/`) work correctly under the GitHub project URL. External figures must allow loading from other sites. Text is displayed as plain text, not HTML or Markdown. Categories, facilities, and counts are computed from the data. File lists and verification data support JSON, CSV, HDF5, and other formats via ordinary links; the website does not parse or execute those files.

The demonstration input and ground-truth JSON files live in `docs/data/demo/`. Recreate them with `python3 scripts/generate_demo_data.py`. They are deterministic synthetic signals, not experimental spectra. Demo comparison plots are labeled as synthetic; replace them with actual PDF figure crops for real papers.

## Preview and validate

No dependencies or build step are required. From the repository root:

```sh
python3 scripts/validate_data.py
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
- `docs/data/benchmark.json`: benchmark content.
- `scripts/validate_data.py`: schema, duplicate-ID, input, verification, and local-asset checks.

There are no analytics, external fonts, third-party scripts, API keys, or backend services. GitHub Pages itself is public hosting, not an author-only authentication system.
