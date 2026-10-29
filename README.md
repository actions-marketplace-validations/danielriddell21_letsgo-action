# letsgo-action

Run [letsgo](https://github.com/danielriddell21/letsgo) in GitHub Actions.

letsgo builds a Go project, refuses to ship it if it's wrong, publishes it
reproducibly, and lets anyone prove afterwards that the binaries match the
source. This action installs it and runs it.

## Usage

```yaml
name: release
on:
  push:
    tags: ["v*"]

permissions:
  contents: write      # create the release and upload assets
  id-token: write      # provenance attestation
  attestations: write
  packages: write      # only if you publish a container image

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-go@v7
        with:
          go-version-file: go.mod

      - uses: danielriddell21/letsgo-action@v1
```

Go is a prerequisite: its version changes the bytes you ship, so the workflow
chooses it. letsgo is installed with `go install`, checked by the module proxy
against the public checksum database. A shallow clone is fine.

- **Plugins** pinned in `letsgo.mod` are installed before the command runs, and
  the plugin store is cached, so a workflow never names them.
- **A Homebrew tap** needs a token that can write to another repository. Pass
  `tap-app-id` and `tap-app-private-key` to mint one scoped to the tap alone.
- **`tag` and `promote`** create an annotated tag, so the action sets
  letsgo-champ[bot] as the git identity unless the workflow already set one.
  `promote` needs `fetch-depth: 0`.

`command` also runs `plan`, `apply`, `verify`, `promote`, `audit`, `doctor`,
`tag`, `yank`, `diff` and `features`, with `args` appended as written; empty
installs letsgo and runs nothing. The [GitHub Action wiki page][ga] covers an
approval gate between `plan` and `apply`, verifying a release, monorepos,
promoting a prerelease from the GitHub UI, and the reasoning behind each
default.

[ga]: https://github.com/danielriddell21/letsgo/wiki/GitHub-Action

## Inputs

| Input | Default | Description |
|---|---|---|
| `version` | `latest` | The letsgo release to install, a tag such as `v1.0.0`, or `local` to build `./cmd/letsgo` from the checkout. |
| `command` | `release` | `release`, `plan`, `apply`, `build`, `verify`, `diff`, `tag`, `promote`, `yank`, `audit`, `doctor`, `features`, or empty to install only. |
| `args` | `""` | Extra arguments, split on whitespace. |
| `working-directory` | `.` | Where to run. |
| `plan-file` | `release.plan` | Where `plan` saves the plan and `apply` reads it, relative to `working-directory`. |
| `plan-artifact` | `release.plan` | The artifact name `plan` uploads the plan under and `apply` downloads it from. |
| `token` | `github.token` | The forge token letsgo publishes with. |
| `tap-token` | `""` | The token a Homebrew formula is published with. Empty falls back to `token`. |
| `tap-app-id` / `tap-app-private-key` | `""` | A GitHub App that can write to the tap. Mints a token scoped to the tap alone and uses it as `tap-token`. |
| `tap-repository` | `homebrew-tap` | The tap the App token is scoped to. |
| `attest` | `false` | Attest provenance for the `dist/` archives. Needs `id-token: write` and `attestations: write`. |

## Outputs

| Output | Description |
|---|---|
| `letsgo-version` | The letsgo version that ran. |
| `version` | The project version that was built or published. |
| `release-url` | The release page, when a release was published. |
| `manifest` | Path to the `letsgo.json` letsgo wrote. |
| `plan-file` | Path to the plan `plan` saved. |
| `tag` | The release's tag, with the module directory prefix for a nested module (`services/api/v1.2.3`). |

## Pinning the letsgo version

`latest` saves this action a release every time letsgo publishes one. It is
the newest stable letsgo, and from v1.0.0 it stays on the v1 line: a future
major would need a `/v2` module path before `latest` could reach it. But
letsgo decides the archive layout and linker flags, so it is a build input like
the compiler: a release that must come out the same next time pins it, and
bumps the pin deliberately.

```yaml
      - uses: danielriddell21/letsgo-action@v1
        with:
          version: v1.0.0
```

## Permissions

`contents: write` is all a plain release needs. Add `id-token: write` and
`attestations: write` for provenance, and `packages: write` for a container
image. The tap App needs installing only on the tap, not on the repository
being released.
