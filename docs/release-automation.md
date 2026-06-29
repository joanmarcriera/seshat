# Distavo — Release automation

How much of shipping Distavo is unattended, what you push to trigger it, and the
one-time secrets each pipeline needs. The mechanical steps in
`docs/distribution-checklist.md` are what these workflows automate.

## What's automated vs manual

| Stage | Channel | Automated? | Trigger |
| --- | --- | --- | --- |
| Build + test (all 3 editions) | — | ✅ fully | every push / PR (`ci.yml`) |
| Sign → notarize → DMG → GitHub Release | **Direct** | ✅ fully (once secrets set) | push a `v*` tag (`release.yml`) |
| Build → sign → upload to App Store Connect | **App Store** | ✅ upload; **review/release manual** (Apple requires) | push a `v*` tag (`release-appstore.yml`) |
| Submit build | **Setapp** | ❌ first version is Web-UI only; later versions scriptable | manual — see `setapp-submission.md` |

Push **one tag** (`git tag v1.0.0 && git push origin v1.0.0`) and both release
workflows fire: a notarized DMG lands on GitHub Releases, and the App Store build
uploads to App Store Connect ready for you to submit. Setapp's first upload stays
manual by Setapp's own rules.

> These workflows are validated for YAML/shell syntax but **cannot be run end-to-end
> until the secrets below exist and the Apple/App-Store-Connect setup in
> `distribution-checklist.md` §1 + §4.1 is done.** Do a `workflow_dispatch` dry run
> of `release.yml` first — it builds and notarizes a DMG as an artifact without
> publishing a Release.

## One-time prerequisites (you, once)

From `distribution-checklist.md` §1 + §4.1:
- **Developer ID Application** certificate (Direct/Setapp signing).
- **Apple Distribution** *and* **3rd Party Mac Developer Installer** certificates + an
  App record for `uk.co.riera.distavo` in App Store Connect. A Mac App Store `.pkg`
  needs both: the first signs the `.app`, the second signs the `.pkg` installer.
- An **App-Specific Password** (notarization) and an **App Store Connect API key**
  (.p8, App Manager role — used for App Store upload and, with `-allowProvisioningUpdates`,
  to fetch/manage the App Store provisioning profile automatically).

## Secrets to add

Repo → **Settings → Secrets and variables → Actions → New repository secret**.
Never commit these; never paste them in chat — add them yourself in the GitHub UI.

### `release.yml` (Direct DMG)
| Secret | What it is / how to make it |
| --- | --- |
| `APPLE_TEAM_ID` | 10-char Team ID (developer.apple.com → Membership). |
| `DEVELOPER_ID_CERT_P12_BASE64` | Export the **Developer ID Application** identity from Keychain Access as `.p12`, then `base64 -i cert.p12 \| pbcopy`. |
| `DEVELOPER_ID_CERT_PASSWORD` | The password you set when exporting that `.p12`. |
| `APPLE_ID` | Your Apple Account email (used by `notarytool`). |
| `APPLE_NOTARY_PASSWORD` | App-specific password (account.apple.com → Sign-In & Security → App-Specific Passwords). |

### `release-appstore.yml` (App Store upload)
| Secret | What it is / how to make it |
| --- | --- |
| `APPLE_TEAM_ID` | Same as above (shared). |
| `APPLE_DISTRIBUTION_CERT_P12_BASE64` | Export the **Apple Distribution** identity (signs the `.app`) as `.p12`, base64 it. |
| `APPLE_DISTRIBUTION_CERT_PASSWORD` | That `.p12`'s export password. |
| `APPLE_INSTALLER_CERT_P12_BASE64` | Export the **3rd Party Mac Developer Installer** identity (signs the `.pkg`) as `.p12`, base64 it. Required — a Mac App Store submission is a signed installer. |
| `APPLE_INSTALLER_CERT_PASSWORD` | That `.p12`'s export password. |
| `ASC_API_KEY_ID` | App Store Connect → Users and Access → Integrations → App Store Connect API → key **Key ID**. |
| `ASC_API_ISSUER_ID` | The **Issuer ID** on that same page. |
| `ASC_API_KEY_P8_BASE64` | The downloaded `AuthKey_XXXX.p8`, base64'd (`base64 -i AuthKey_XXXX.p8`). With Automatic signing (`-allowProvisioningUpdates`) the App-Manager key lets `xcodebuild` fetch/manage the Mac App Store provisioning profile itself — **no separate profile secret needed**. (It can manage profiles but cannot mint distribution certs, which is why the two `.p12`s above are imported manually.) |

## How `release.yml` works (Direct)
1. Imports the Developer ID cert into a throwaway keychain.
2. `xcodegen generate` → archive the Direct edition with `Developer ID Application`.
3. Export (`developer-id`), zip the app, `notarytool submit --wait`, `stapler staple`.
4. `hdiutil` a DMG, notarize + staple **the DMG too** (trusted offline).
5. Gatekeeper assess (`spctl`), then `gh release create <tag>` with the DMG.
   A `workflow_dispatch` run stops at step 4 and uploads the DMG as an artifact (dry run).

## How `release-appstore.yml` works
1. Imports **both** signing certs (Apple Distribution + 3rd Party Mac Developer
   Installer) into a throwaway keychain, and installs the ASC API key.
2. Archives the `Distavo-AppStore` scheme with **Automatic** signing +
   `-allowProvisioningUpdates`, so xcodebuild fetches the App Store provisioning
   profile via the API key. The scheme pins `AppStore.xcconfig` (sandboxed edition).
3. Exports a signed `.pkg` (`method: app-store-connect`) with the two signing identities
   **pinned explicitly** — `Apple Distribution` for the `.app`, `3rd Party Mac Developer
   Installer` for the `.pkg` (a bare automatic export mis-selects the installer cert for
   code signing). The profile is resolved via `-allowProvisioningUpdates`. Then it uploads
   with `xcrun altool --upload-app`; the build appears in App Store Connect and you attach
   it to a version and **Submit for Review** (manual).

## Local equivalent
`apple/scripts/build-and-notarize.sh {direct|setapp|appstore}` does the same signing
+ notarization from your Mac (uses your Xcode-logged-in account / a `notarytool`
keychain profile instead of CI secrets) — handy for a one-off or to debug before tagging.

## What stays manual (and why)
- **App Review** and store release — Apple requires human submission/approval.
- **Setapp first upload** — Setapp only accepts the first version via its Web UI
  (`setapp-submission.md`); later versions can be scripted via its REST API.
- **Trademark clearance** on "Distavo" — a hard gate before any store submission.
