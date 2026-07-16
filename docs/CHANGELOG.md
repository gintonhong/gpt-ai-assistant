# Changelog

## v0.9.1.1 — OAuth PKCE Hotfix

### Fixed

- Saves the PKCE `code_verifier` together with OAuth state.
- Restores the same verifier during callback token exchange.
- Fixes `invalid_grant: Missing code verifier`.

### Important

- Complete authorization without restarting or redeploying Render.
- Start a fresh authorization after deploying this hotfix.
