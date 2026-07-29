# PR Diff Review Runner

`review_runner` prepares a supplied Pull Request unified diff for an AI review provider. It does not inspect the repository, call a network service, or publish GitHub comments.

## Local Use

Read a patch from a file:

```bash
python -m review_runner --diff changes.patch --mock-scenario findings
```

Read a patch from standard input:

```bash
git diff main...HEAD | python -m review_runner --mock-scenario no_findings
```

Operational logs go to stderr. The structured `ReviewResult` is emitted as JSON on stdout. Exit status is `0` when all generated chunks are processed, `1` when a provider chunk fails, and `2` for invalid configuration or input file errors.

The accepted input is a Git unified patch containing `diff --git` file sections and `@@` unified hunks. Empty patches are valid. Added, modified, deleted, renamed, binary, quoted-path, and missing-final-newline metadata are retained where Git includes them.

## Configuration

Pass a JSON object with `--config path.json`. Every option can also be overridden with a `REVIEW_RUNNER_<UPPERCASE_NAME>` environment variable. Tuple/list values use a JSON array or a comma-separated value.

| Option | Default | Purpose |
| --- | ---: | --- |
| `included_file_types` | Common source/config/documentation suffixes | Allowed file suffixes |
| `excluded_patterns` | See below | Excluded `PurePath.match` patterns |
| `sensitive_patterns` | `.env` patterns | Paths never included in provider input |
| `max_file_bytes` | `51200` | Maximum rendered diff bytes per file |
| `max_file_lines` | `1500` | Maximum rendered diff lines per file |
| `max_files` | `100` | Maximum included files |
| `max_total_pr_tokens` | `100000` | Total generated chunk budget |
| `max_chunk_input_tokens` | `24000` | Configured per-chunk ceiling |
| `max_chunks` | `20` | Maximum generated chunks |
| `model_context_tokens` | `32000` | Provider model context window |
| `reserved_instruction_tokens` | `1500` | Instruction reservation |
| `reserved_schema_tokens` | `750` | Result schema reservation |
| `reserved_metadata_tokens` | `500` | Provider metadata reservation |
| `reserved_output_tokens` | `4000` | Expected output reservation |
| `safety_margin_tokens` | `1000` | Additional safety reservation |
| `oversized_file_behavior` | `truncate` | `truncate` at hunk boundaries or `skip` |
| `redaction_rules` | Common credential patterns | Named regular expressions |
| `logging_level` | `INFO` | Python logging level |

Available diff tokens are the smaller of `max_chunk_input_tokens` and the model context window after every reservation. The fallback estimator charges one token per UTF-8 byte. This intentionally overestimates typical model tokenization; a future provider can inject an exact implementation of `TokenEstimator`.

Custom redaction expressions may use no capture groups to replace the complete match, or one first capture group containing a safe prefix to preserve. The remainder is replaced with a stable marker such as `[REDACTED:CREDENTIAL:1]`.

## Filtering And Coverage

Default exclusions include dependency lockfiles, `vendor`, `node_modules`, generated directories and filenames, build outputs, minified files, source maps, images, fonts, PDFs, and archives. Binary markers are excluded independently. Repository overrides can replace these lists.

Filtering and sensitive-path checks happen before redaction, estimation, and chunk construction. Path rules are checked against both old and new names for renames. Every excluded item appears in `skipped` with a path and reason; omitted hunks also include their hunk header. `file_statuses` records `fully_reviewed`, `partially_included`, or `skipped`.

Chunking attempts the complete PR, then file boundaries, then hunk boundaries, and finally complete diff-line boundaries. File headers and hunk headers are repeated where needed. Stable chunk IDs include their sequence and a content digest. Chunk and PR limits stop further construction and create explicit `chunk_budget_limit` records.

## Mock Provider

`MockReviewProvider` implements the same asynchronous `ReviewProvider` protocol intended for OpenRouter. Scenarios are deterministic:

- `findings`: one finding per chunk
- `no_findings`: valid response without findings
- `multiple`: multiple findings per chunk
- `duplicates`: normalized duplicate findings
- `empty`: invalid empty response
- `error`: provider exception
- `invalid`: invalid structured result
- `delayed`: deterministic local delay

A future provider implements `ReviewProvider.review(ReviewChunk) -> ProviderResult`. Provider input must use `ReviewChunk.content`, which is constructed only after filtering and redaction. It must not receive the original patch.

## Post-CI Integration

This task intentionally does not add a GitHub Actions workflow. The later review workflow must run through `workflow_run` only after the existing workflow named `PR Quality and Security` completes successfully. It must resolve the triggering run's Pull Request and head SHA, retrieve only that PR's unified diff, and invoke this CLI.

The workflows must not duplicate responsibilities:

| Existing `PR Quality and Security` workflow | Future post-CI review workflow |
| --- | --- |
| Ruff | Resolve triggering PR metadata |
| pytest, including runner tests | Retrieve the PR unified diff |
| Installed dependency validation | Run this review pipeline |
| Gitleaks history and directory scans | Invoke the future review provider |
| Checkov Dockerfile validation | Publish the future review result |
| Docker image build and Trivy scan | No quality, security, test, or image checks |

The future workflow should use `workflow_run.workflows: ["PR Quality and Security"]`, `types: [completed]`, and require `github.event.workflow_run.conclusion == 'success'`. It must not rerun Ruff, pytest, dependency checks, Gitleaks, Checkov, Docker builds, or Trivy.

## Limitations

- The parser supports standard Git unified patches, not arbitrary context or combined merge diffs.
- Files without `diff --git` sections are reported as unsupported.
- Rename metadata with unusual quoting outside standard Git output may be reported as malformed.
- The conservative estimator is intentionally much larger than a normal model tokenizer estimate.
- Redaction reduces transmission risk but is not a deterministic secret scanner and does not replace Gitleaks.
