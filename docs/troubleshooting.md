# Troubleshooting

## Doctor (coming soon)
- Run: `gitscaffold settings doctor`
- Checks: gh presence and auth, GITHUB_TOKEN set, optional AI keys.

## Common gh issues
- `gh: ... exit status 1` — ensure `gh auth status` is OK and `--repo owner/repo` is correct.
- Missing `gh project` — install/update gh to a version with Projects support or install the extension.

## Tokens
- Set `GITHUB_TOKEN`; avoid expired or insufficient scopes.
- For AI features, set `OPENAI_API_KEY` or `GEMINI_API_KEY`.

## Network
- If behind a proxy or offline, gh operations will fail. Use API fallbacks where available or try again when connected.
