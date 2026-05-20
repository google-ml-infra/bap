# BAP (Benchmarking and Analysis Platform)

This repository was migrated from `google-ml-infra/actions/benchmarking`.

## Repository Structure

- The contents of the original `benchmarking/` directory are now at the root.
- **Protobufs:** The `proto/` directory was renamed to `bap_proto/` to avoid Python namespace collisions with the third-party `proto-plus` library. Always import protos from `bap_proto`.

## Build & Dependencies

- **Bazel:** Uses `MODULE.bazel`.
- **Pip:** If experiencing authentication issues with private registries, `MODULE.bazel` is configured to override the index to public PyPI via `extra_pip_args`.
- **Python:** Managed via `rules_python`.

## CI/CD

- GitHub Actions are located in `.github/workflows/`.
- Irrelevant/broken workflows from the original repository have been removed.
- Use `actionlint` and `ruff` for validation.

## Maintenance

### Syncing with upstream (google-ml-infra/actions)

To pull in new changes from the original repository:

1. Add upstream: `git remote add upstream https://github.com/google-ml-infra/actions.git`
2. Fetch: `git fetch upstream`
3. Filter updates: `git filter-repo --source upstream/main --target upstream-filtered --path benchmarking/ --path .github/ --path-rename benchmarking/:`
4. Merge: `git merge upstream-filtered --allow-unrelated-histories`
