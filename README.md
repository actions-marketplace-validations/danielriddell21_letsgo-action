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

A shallow clone is fine. letsgo falls back to the GitHub compare API when the
changelog needs history the runner does not have.

### Checking a pull request

`plan` resolves and gates a release without building one, in about two seconds:

```yaml
      - uses: danielriddell21/letsgo-action@v1
        with:
          command: plan
          args: --explain
```

### Verifying a published release

```yaml
      - uses: danielriddell21/letsgo-action@v1
        with:
          command: verify
          args: v1.3.0
```

### Installing letsgo without running it

```yaml
      - uses: danielriddell21/letsgo-action@v1
        with:
          command: ""
      - run: letsgo plan && letsgo build
```

## Inputs

| Input | Default | Description |
|---|---|---|
| `version` | `latest` | The letsgo release to install, or a tag such as `v0.8.0`. |
| `command` | `release` | `release`, `plan`, `build`, `verify`, `diff`, `tag`, `yank`, or empty to install only. |
| `args` | `""` | Extra arguments, split on whitespace. |
| `working-directory` | `.` | Where to run. |
| `token` | `github.token` | The forge token letsgo publishes with. |
| `tap-token` | `""` | The token a Homebrew formula is published with. Empty falls back to `token`. |

## Outputs

| Output | Description |
|---|---|
| `letsgo-version` | The letsgo version that ran. |
| `version` | The project version that was built or published. |
| `release-url` | The release page, when a release was published. |
| `manifest` | Path to the `letsgo.json` letsgo wrote. |

```yaml
      - uses: danielriddell21/letsgo-action@v1
        id: release
      - run: echo "published ${{ steps.release.outputs.release-url }}"
```

## Pinning the letsgo version

The default is `latest`, because the alternative was a release of this action
every time letsgo published one — and an action whose only change is a version
number teaches everyone to ignore its releases.

That default is a convenience, not a guarantee. letsgo decides the archive
layout and the linker flags, so it is a build input exactly as the compiler is,
and a release built by a version you did not choose is a release you cannot
reproduce. A repository that cares about that pins the tag:

```yaml
      - uses: danielriddell21/letsgo-action@v1
        with:
          version: v0.8.0
```

Bump that pin deliberately. `letsgo verify` replays a release from the manifest,
which records the version that built it, so a release stays checkable either
way — pinning is what makes the *next* one come out the same.

## How letsgo is installed

`go install github.com/danielriddell21/letsgo/cmd/letsgo@<version>`.

The module proxy checks what it fetches against the public checksum database,
which is a stronger guarantee than any digest this action could carry, and it
works on every runner without a platform matrix. The cost is a short compile;
letsgo has no dependencies, so it is short.

Go itself is a prerequisite rather than something this action installs: the Go
version changes the bytes of the binaries you ship, so choosing it belongs to
the workflow that knows which one your project releases with.

## Permissions

`contents: write` is the only one a plain release needs. Add `id-token` and
`attestations` for build provenance, and `packages: write` for a container
image.

A Homebrew tap lives in another repository, and the workflow token cannot write
to one. That needs an App token, passed as `tap-token` rather than as `token`:

```yaml
- uses: actions/create-github-app-token@v3
  id: tap-token
  with:
    app-id: ${{ vars.TAP_APP_ID }}
    private-key: ${{ secrets.TAP_APP_PRIVATE_KEY }}
    owner: ${{ github.repository_owner }}
    repositories: homebrew-tap

- uses: danielriddell21/letsgo-action@v1
  with:
    tap-token: ${{ steps.tap-token.outputs.token }}
```

Note what `repositories` does *not* list: the repository being released. Its
own release is published with the workflow token, so the App needs no
installation there — which also means a new repository cannot fail its first
release for having been left out of one. Passing the App token as `token`
instead works, and makes it a credential that can rewrite this repository's
releases too.
