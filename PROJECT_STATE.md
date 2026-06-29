# Project State

## Current objective

Keep release versions increasing automatically after merges to `main` and
verify that the repository has no stale branches.

## Completed work

- App Store 1.1.0 build 2 was uploaded from CI in the previous cycle.
- Static website source was added under `ops/site`.
- Setapp submission playbook now reflects repo-side metadata and packaging
  work that can be automated.
- Setapp Release build validation passes unsigned and produces a universal
  `x86_64 arm64` app with the expected Setapp Info.plist keys.
- `swift test` passes for `apple/DistavoCore`.
- `ops/site` is deployed and live at `https://distavo.com/`.
- Homepage now includes recording-law nuance and a free/open recorder tools
  section, including Notely Voice from F-Droid.
- Added `version-bump.yml` so every non-bot push to `main` gets a follow-up
  commit that increments the marketing minor version and build number.
- Remote branch hygiene was checked after `git fetch --prune`; only `main` and
  the active unmerged `fix/appstore-signing` branch remain.

## Current implementation state

- `ops/site` is deployed as the public static website.
- The website explains that recording consent, data/privacy use, sharing, and
  court/tribunal admissibility are separate legal questions.
- The website recommends open/free recording tools that can export audio into
  the watched folder workflow.
- The Setapp build uses `apple/Setapp-Info.plist` for Setapp-only metadata,
  including `NSUpdateSecurityPolicy`.
- `apple/scripts/build-and-notarize.sh setapp` packages a notarized app with
  `Distavo.app` and `AppIcon.png` in the final upload zip.
- `scripts/bump-minor-version.py` is the single script used by the workflow for
  main-merge version bumps.

## Files changed

- `ops/site/`
- `apple/Setapp-Info.plist`
- `apple/configs/Setapp.xcconfig`
- `apple/scripts/build-and-notarize.sh`
- `docs/setapp-submission.md`
- `PROJECT_STATE.md`
- `TASKS.md`
- `DECISIONS.md`
- `.github/workflows/version-bump.yml`
- `scripts/bump-minor-version.py`

## Tests run

- `plutil -lint apple/Setapp-Info.plist` — passed.
- `bash -n apple/scripts/build-and-notarize.sh` — passed.
- Static website link/asset/title/meta parser over `ops/site` — passed.
- `git diff --check` — passed.
- `cd apple && xcodegen generate` — passed.
- `cd apple && xcodebuild -project Distavo.xcodeproj -scheme Distavo -configuration Release -derivedDataPath build/SetappValidation -xcconfig configs/Setapp.xcconfig CODE_SIGNING_ALLOWED=NO build` — passed unsandboxed after the sandbox blocked Swift/Xcode cache writes.
- Built Setapp app metadata check — passed: bundle id `uk.co.riera.distavo-setapp`, version `1.1.0`, build `2`, icon key, `LSUIElement`, and `NSUpdateSecurityPolicy`.
- `lipo -info apple/build/SetappValidation/Build/Products/Release/Distavo.app/Contents/MacOS/Distavo` — passed: `x86_64 arm64`.
- Simulated Setapp zip extraction — passed: root contains `Distavo.app` and `AppIcon.png`.
- `cd apple/DistavoCore && swift test` — passed unsandboxed: 62 tests, 1 live E2E skipped.
- Clean `ops/site` tarball deployed to `/opt/stacks/core/distavo` on the
  existing server. Current remote backup is
  `/tmp/distavo-site-backup-20260629T165646Z`.
- Live HTTPS check for `https://distavo.com/`, `/privacy/`, `/support/`,
  `/feedback/`, `/assets/site.css`, and `/assets/settings.png` — passed.
- Static website link/asset/title/meta/parser check after adding legal/tools
  sections — passed.
- `git diff --check` after legal/tools website update — passed.
- Verified current F-Droid metadata for Notely Voice package
  `com.module.notelycompose.android`: package exists, license is
  `GPL-3.0-only`, source is published, and voice/audio transcription features
  are listed.
- Clean `ops/site` tarball redeployed to `/opt/stacks/core/distavo`.
  Current remote backup is `/tmp/distavo-site-backup-20260629T170546Z`.
- Live HTTPS check for the new homepage legal/tools copy and updated CSS —
  passed.
- Added legal and recorder source links resolve over HTTPS. The ICO link was
  checked with `GET` because it rejects `HEAD`.
- `git fetch origin --prune` — passed; no merged remote branches remain.
- Remote branch audit — passed: `origin/main` plus active unmerged
  `origin/fix/appstore-signing` only.
- `python3 -m py_compile scripts/bump-minor-version.py` — passed.
- `python3 scripts/bump-minor-version.py --dry-run` — passed:
  `1.1.0` → `1.2.0`, build `2` → `3`.
- Temporary-copy write test for `scripts/bump-minor-version.py` — passed:
  updated `apple/project.yml`, `ops/site/index.html`, and
  `docs/setapp-submission.md`.
- YAML parse check for `.github/workflows/version-bump.yml` — passed.
- `actionlint` availability check — not installed locally.
- `gh api repos/joanmarcriera/distavo/branches --paginate` — passed:
  remote repository has only `main` and active `fix/appstore-signing`.
- `git diff --check` after version policy changes — passed.

## Unresolved risks

- The new version bump workflow must be merged to `main` before it can enforce
  future main-merge version bumps.
- Setapp Framework integration still requires the vendor dashboard public key
  and SDK archive.
- The first Setapp build must still be uploaded through the Setapp Web UI.

## Known blockers

- Marc must create or access the Setapp vendor account, choose the distribution
  model, and provide the Setapp Framework/public key assets.

## Next recommended action

Commit and push this version policy update.
