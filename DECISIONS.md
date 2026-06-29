# Decisions

## 2026-06-29 - Keep the website static and self-contained

Decision: Host the public Distavo website as plain static files under
`ops/site`.

Alternatives considered: Introduce a framework such as Next.js or Astro, or
split the website into a separate repository.

Rationale: The current site needs product, privacy, support, and feedback pages
with no dynamic runtime. Static files match the existing nginx hosting surface
and minimize deployment risk.

Consequences: Changes are simple to review and deploy, but there is no content
CMS or app-side integration.

Revisit when: The site needs dynamic downloads, account-specific content,
localized pages, or a larger documentation system.

## 2026-06-29 - Use a Setapp-only Info.plist

Decision: Add `apple/Setapp-Info.plist` and point `Setapp.xcconfig` at it
instead of adding Setapp metadata to the generated shared plist.

Alternatives considered: Add `NSUpdateSecurityPolicy` to all editions, or try
to encode the nested dictionary through `INFOPLIST_KEY_*` build settings.

Rationale: `NSUpdateSecurityPolicy` is Setapp-specific and nested. A dedicated
plist keeps Direct and App Store metadata clean and is easier to inspect.

Consequences: Shared Info.plist keys must be kept in sync if the app adds new
required usage descriptions later.

Revisit when: XcodeGen gains a cleaner per-xcconfig plist merge path or the
Setapp target is split into a dedicated target/scheme.

## 2026-06-29 - Delay Setapp Framework linking until dashboard assets exist

Decision: Do not link `libSetapp.a` or add framework calls until the vendor
dashboard public key and SDK are available.

Alternatives considered: Stub the framework integration or add placeholder
paths to the project.

Rationale: Placeholder framework paths would break local and CI builds. The
current safe progress is metadata, packaging, and documentation.

Consequences: The Setapp build is closer to submission, but final framework
activation remains blocked on Marc's vendor account assets.

Revisit when: The Setapp SDK archive and app public key file are in the repo or
available in a local, documented path.

## 2026-06-29 - Bump versions after main merges, but do not auto-tag

Decision: Add a `version-bump.yml` workflow that runs after non-bot pushes to
`main`, increments the marketing minor version and build number, and commits
the result with `[skip version bump]`.

Alternatives considered: Create a `v*` tag automatically on every merge to
`main`, or require manual version bump commits in every pull request.

Rationale: Tags trigger the expensive signing, notarization, GitHub Release,
and App Store upload workflows. Keeping the version ahead automatically makes
the next release monotonic without unexpectedly uploading a store build after
every merge.

Consequences: Releases still require a deliberate `v*` tag. If branch
protection blocks GitHub Actions from pushing to `main`, the workflow will need
either an allowed bot token or a PR-based bump flow.

Revisit when: Every merge to `main` should become a fully automated public
release and App Store Connect upload.

## 2026-06-29 - Pin App Store provisioning manually for TestFlight eligibility

Decision: Require a base64-encoded Mac App Store provisioning profile secret
and pin that profile during the App Store archive/export workflow.

Alternatives considered: Continue relying on `-allowProvisioningUpdates` with
App Store Connect API credentials, or ignore ITMS-90889 because App Store
Connect accepted delivery.

Rationale: Apple reported that build 2 was delivered but not eligible for
TestFlight because the main `Distavo.app` bundle lacked a provisioning profile.
Manual profile installation gives the workflow a concrete profile to embed and
allows CI to fail before upload if it is missing.

Consequences: The App Store upload workflow now needs the
`MAC_APP_STORE_PROVISIONING_PROFILE_BASE64` repository secret. Profile renewal
must be handled when the profile expires.

Revisit when: Xcode automatic signing reliably embeds the profile in archived
and exported Mac App Store packages under GitHub Actions.
