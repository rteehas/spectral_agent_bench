# Spectral Agent Bench — author review

A static GitHub Pages workspace for reviewing spectral benchmark examples, inspired by [SpectralBench's review page](https://yuxi120407.github.io/SpectralBench/review.html). The implementation is original; it does not copy the reference site's dataset or publication assets.

**Website:** https://rteehas.github.io/spectral_agent_bench/  
**Review alias:** https://rteehas.github.io/spectral_agent_bench/review.html

The initial dataset contains **four clearly labeled, fictional demonstration scenarios across three papers**. Synthetic figures are illustrative, not experimental spectra.

## Review workflow

- Browse papers and expand individual scenarios to compare prompts, reference answers, rubrics, and evidence.
- Search by paper, author, material, DOI, prompt, or scenario ID. Combine category, facility, and verdict filters.
- Record **Correct**, **Needs revision**, or **Unsure**, with optional comments.
- Reviews save in the current browser, separately for each dataset ID. They are **not sent to a server or shared between reviewers**.
- Use **Export reviews** to download JSON and send it to the maintainer. **Import reviews** restores or merges a file from the same dataset, retaining the more recent review for each scenario. Importing multiple reviewers into one browser does not preserve separate identities; keep original files to retain each reviewer's feedback.
- **Open GitHub issue** prepares a draft with the scenario and feedback. The reviewer must be signed into GitHub and submit it themselves. Long comments are truncated in issue URLs; attach the exported JSON for full text.
- Scenario links use `#scenario-DEMO-001`, for example. Opening a direct link expands its paper and scenario.

Browser storage can be cleared by the browser or unavailable in private mode; export files are the durable copy. Verdict filters update after leaving a scenario so choosing a verdict does not interrupt comment entry.

## Add real benchmark examples

Edit **`docs/data/benchmark.json`**. Set `demo` to `false` when replacing the fictional dataset, and use a new `datasetId` such as `spectral-agent-v1`. Change the dataset ID for releases that materially change questions, answers, or rubrics so old verdicts are not silently reused. Keep paper and scenario IDs stable within a dataset release.

```json
{
  "schemaVersion": 1,
  "datasetId": "spectral-agent-v1",
  "title": "Spectral Agent Bench",
  "demo": false,
  "papers": [
    {
      "id": "paper-001",
      "title": "Your paper title",
      "authors": "Your paper authors",
      "category": "Catalyst",
      "facility": "Your facility",
      "scenarios": [
        {
          "id": "SCENARIO-001",
          "title": "Material and experimental condition",
          "edge": "Cu K-edge",
          "prompt": "Your full model prompt and questions.",
          "groundTruth": {
            "Reference answer": "The expected answer.",
            "Reasoning": "Evidence supporting the answer."
          },
          "rubric": [
            {
              "criterion": "Species identification",
              "answer": "What earns these points.",
              "points": 2
            }
          ],
          "evidence": [
            {
              "label": "Figure 2, page 4",
              "caption": "Describe the source evidence and attribution."
            }
          ]
        }
      ]
    }
  ]
}
```

Optional paper fields:

- `doi`: a bare DOI, for example `10.1234/example`.
- `pdf`: an HTTPS URL or a path relative to `docs/`, such as `assets/papers/paper-001.pdf`.
- `dataUrl`: an optional open-data URL (for example, a Zenodo record) or local data file path. Displays **Open data** when supplied.
- `codeUrl`: an optional open-code URL (for example, the study’s GitHub repository) or local code file path. Displays **Open code** when supplied.
- `evidence`: a list using the same format as scenario evidence, displayed under **Key paper evidence**.

These resource links appear below the paper title and metadata when the paper is expanded. Omit either field when unavailable; do not add an empty string. The first demonstration paper links to this site’s sample dataset and source repository to illustrate both fields.


Optional evidence fields:

- `image`: an HTTPS URL or relative asset path, such as `assets/evidence/paper-001-page-4.png`.
- `url`: an HTTPS source link or local PDF path. Use a PDF fragment such as `#page=4` to point to a page.

Put your figures and PDFs inside `docs/assets/`. All files under `docs/` are published. Add only material you intend to share publicly and have permission to redistribute. Relative paths (without an initial `/`) work correctly under the GitHub project URL. External figures must allow loading from other sites. Text is displayed as plain text, not HTML or Markdown. Categories, facilities, counts, and rubric totals are computed from the data.

## Preview and validate

No dependencies or build step are required. From the repository root:

```sh
python3 scripts/validate_data.py
node --check docs/assets/app.js
python3 -m http.server 8765 --directory docs
```

Open http://localhost:8765. Use an HTTP server rather than opening the HTML file directly, because the page fetches its JSON dataset.

## GitHub Pages deployment

The workflow in `.github/workflows/pages.yml` validates the dataset and deploys **only `docs/`** on pushes to `main`. Pull requests run validation without deployment.

In the repository's **Settings → Pages**, set **Source** to **GitHub Actions**. Once enabled, each successful push publishes the site at the URL above. Deployment status appears under **Actions → Deploy review site**.

## File map

- `docs/index.html`: review workspace and metadata.
- `docs/review.html`: compatibility redirect preserving query strings and scenario links.
- `docs/assets/style.css`: responsive styles.
- `docs/assets/app.js`: filtering, evidence viewer, local review state, JSON import/export, and issue drafts.
- `docs/data/benchmark.json`: benchmark content.
- `scripts/validate_data.py`: schema, duplicate-ID, rubric, and local-asset checks.

There are no analytics, external fonts, third-party scripts, API keys, or backend services. GitHub Pages itself is public hosting, not an author-only authentication system.
