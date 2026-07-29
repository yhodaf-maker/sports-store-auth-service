# PR Diff Review Runner

`review_runner` prepares a supplied Pull Request unified diff for an AI review provider. It never inspects the repository or publishes GitHub comments. The default CLI remains offline and uses the mock provider; `OpenRouterProvider` is available to later workflow integration.

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
| `max_execution_seconds` | `300` | Overall runner/provider execution budget |

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

A provider implements `ReviewProvider.review(ReviewChunk) -> ProviderResult` and may implement `prepare(ReviewContext)` for run-scoped capability validation. Provider input must use `ReviewChunk.content`, which is constructed only after filtering and redaction. It must not receive the original patch.

## OpenRouter Provider

The MVP model is explicitly configured as `nvidia/nemotron-nano-9b-v2:free`. The adapter rejects `openrouter/free`, requires an explicit `:free` primary model, and never chooses a paid model implicitly. Change models through `OPENROUTER_MODEL`; approved model fallbacks may be listed explicitly in `OPENROUTER_APPROVED_FALLBACK_MODELS`. Changing providers requires only another `ReviewProvider` adapter and selection in `provider_factory.py`; diff processing and aggregation do not change.

Required configuration:

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | none | Required API credential; never logged |
| `OPENROUTER_API_BASE_URL` | `https://openrouter.ai/api/v1` | HTTPS API root |
| `OPENROUTER_MODEL` | `nvidia/nemotron-nano-9b-v2:free` | Exact approved free model |
| `OPENROUTER_MODEL_CONTEXT_TOKENS` | `128000` | Validated model context window |
| `OPENROUTER_MAX_OUTPUT_TOKENS` | `4000` | Per-response output ceiling |
| `OPENROUTER_CONNECT_TIMEOUT_SECONDS` | `10` | Connection timeout |
| `OPENROUTER_REQUEST_TIMEOUT_SECONDS` | `60` | Response timeout |
| `OPENROUTER_MAX_RETRIES` | `2` | Retries after the first attempt |
| `OPENROUTER_RETRY_INITIAL_DELAY_SECONDS` | `1` | Initial exponential-backoff delay |
| `OPENROUTER_RETRY_MAX_DELAY_SECONDS` | `8` | Maximum backoff delay |
| `OPENROUTER_MAX_REQUESTS_PER_RUN` | `25` | Physical request limit, including preflight and retries |
| `OPENROUTER_MAX_REQUESTS_PER_CHUNK` | `3` | Physical attempts per chunk |
| `OPENROUTER_MAX_INPUT_TOKENS_PER_RUN` | `100000` | Submitted input-token budget |
| `OPENROUTER_MAX_OUTPUT_TOKENS_PER_RUN` | `20000` | Reported output-token budget |
| `OPENROUTER_MAX_EXECUTION_SECONDS` | `300` | Provider run deadline |
| `OPENROUTER_MAX_RESPONSE_BYTES` | `256000` | Response parsing limit |
| `OPENROUTER_REQUIRE_STRUCTURED_OUTPUTS` | `true` | Require native JSON Schema support |
| `OPENROUTER_REQUIRE_ZERO_DATA_RETENTION` | `true` | Route only to ZDR endpoints |
| `OPENROUTER_DENY_DATA_COLLECTION` | `true` | Exclude collecting/training routes |
| `OPENROUTER_ALLOWED_PROVIDERS` | empty | Optional comma-separated route allowlist |
| `OPENROUTER_APP_URL` | empty | Optional `HTTP-Referer` attribution |
| `OPENROUTER_APP_TITLE` | empty | Optional application title |

Before reviewing content, the adapter queries the exact model's endpoints and verifies availability, runner/model context compatibility, maximum output size, route status, and native `response_format` plus `structured_outputs` parameters. Completion requests additionally set `provider.require_parameters`, `provider.data_collection`, and `provider.zdr`. If OpenRouter cannot satisfy privacy routing, the review fails open; controls are never weakened and another model is never selected silently.

The system prompt limits analysis to the supplied changes and declares all metadata and diff content untrusted. The user message separately delimits trusted metadata and the sanitized diff. No tools or plugins are supplied. Source instructions cannot change the schema, request secrets, suppress findings, or expand review scope.

The strict response contains `summary`, `overall_risk`, and `findings`. Each finding requires `file_path`, nullable `line_number`, `severity`, `category`, `title`, `explanation`, `suggested_remediation`, and `confidence`. Severity is one of `INFO`, `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`; category is one of `STYLE`, `PERFORMANCE`, `SECURITY`, `BUG`, `RELIABILITY`, or `MAINTAINABILITY`; confidence is between `0.0` and `1.0`. Extra fields and incorrect types are rejected. Unknown files invalidate the response. Invalid line numbers are conservatively converted to file-level findings with `line_number: null`.

Rate limits, network failures, timeouts, gateway/provider failures, and temporary invalid structured responses use bounded exponential retries. Authentication, invalid configuration, unsupported parameters, privacy rejection, and oversized payloads are not retried. Request, token, retry, and duration quotas are checked before requests. One failed chunk does not stop later chunks unless a run quota or preflight requirement blocks the review. `failure_details`, `partial`, and `ai_review_skipped` describe safe advisory outcomes.

Stable failure categories are `configuration_error`, `authentication_error`, `model_unavailable`, `unsupported_capability`, `privacy_requirement_unavailable`, `rate_limited`, `provider_unavailable`, `network_timeout`, `payload_too_large`, `invalid_structured_response`, `quota_exhausted`, and `unexpected_provider_error`. Their reasons are sanitized and contain no provider response text.

Operational logs contain identifiers, token counts, duration, retries, validation outcome, and failure category only. API keys, authorization headers, prompts, diffs, and raw responses are never logged.

Run deterministic provider tests without network access or quota consumption:

```bash
pytest -q tests/test_openrouter_provider.py tests/test_review_runner.py
```

For an optional manual test, export `OPENROUTER_API_KEY` from a secret store, construct the provider with `OpenRouterConfig.load()`, call `prepare(ReviewContext(...))`, and submit one already-sanitized `ReviewChunk`. Do not use a repository diff containing secrets. Manual testing is intentionally separate from pytest and is not part of CI.

Free OpenRouter models are limited, rate-limited, mutable, and non-SLA-backed. Availability, endpoint capabilities, and privacy-compatible routes may change. Such changes produce a skipped advisory review rather than switching models or failing deterministic CI.

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
