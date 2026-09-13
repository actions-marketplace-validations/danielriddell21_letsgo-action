#!/usr/bin/env python3
"""Check action.yml.

actionlint reads workflows, not action metadata, so the action's own file goes
unchecked unless something checks it. The rule that matters most here is the
one a schema would not catch: an input interpolated into a `run:` block is a
shell injection, because an input can be a branch name and a branch name can
be anything.
"""

import os
import shutil
import subprocess
import sys
import tempfile

import yaml

ACTION = "action.yml"


def fail(message: str) -> None:
    print(f"::error file={ACTION}::{message}", file=sys.stderr)
    globals()["failures"] += 1


failures = 0


def main() -> int:
    with open(ACTION, encoding="utf-8") as f:
        action = yaml.safe_load(f)

    for key in ("name", "description", "runs"):
        if not action.get(key):
            fail(f"{key} is required")

    # Marketplace listings need both, and an action without them cannot be
    # published even if it works.
    branding = action.get("branding") or {}
    if not branding.get("icon") or not branding.get("color"):
        fail("branding needs an icon and a colour to be publishable")

    for name, spec in (action.get("inputs") or {}).items():
        if not (spec or {}).get("description"):
            fail(f"input {name} has no description")

    for name, spec in (action.get("outputs") or {}).items():
        if not (spec or {}).get("description"):
            fail(f"output {name} has no description")
        if not (spec or {}).get("value"):
            fail(f"output {name} has no value; a composite action must map it to a step")

    runs = action.get("runs") or {}
    if runs.get("using") != "composite":
        fail(f'runs.using is {runs.get("using")!r}; this action is composite')

    scripts = []
    for i, step in enumerate(runs.get("steps") or []):
        where = step.get("name") or f"step {i}"
        if "run" not in step:
            continue

        # Composite steps do not inherit a default shell, and a step without
        # one is a syntax error at run time rather than at parse time.
        if not step.get("shell"):
            fail(f"{where}: a composite run step must declare a shell")

        if "${{" in step["run"]:
            fail(
                f"{where}: an expression is interpolated into the script. "
                "Pass it through env: instead — an input can contain shell."
            )
        scripts.append((where, step["run"]))

    shellcheck(scripts)

    if failures:
        print(f"\n{ACTION}: {failures} problem(s)", file=sys.stderr)
        return 1

    print(f"{ACTION}: ok ({len(scripts)} script(s) checked)")
    return 0


def shellcheck(scripts) -> None:
    """Run shellcheck over each step's script."""
    if not shutil.which("shellcheck"):
        print("shellcheck is not installed; skipping the script checks")
        return

    with tempfile.TemporaryDirectory() as tmp:
        for i, (where, script) in enumerate(scripts):
            path = os.path.join(tmp, f"step{i}.sh")
            with open(path, "w", encoding="utf-8") as f:
                f.write("#!/usr/bin/env bash\n" + script)

            result = subprocess.run(
                ["shellcheck", "--shell=bash", path],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                fail(f"{where}: shellcheck\n{result.stdout}{result.stderr}")


if __name__ == "__main__":
    sys.exit(main())
