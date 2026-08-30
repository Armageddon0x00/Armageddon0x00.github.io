# Site operator toolkit

Run every command from any directory inside the repository through the single dispatcher:

```sh
.github/scripts/site.sh COMMAND
```

The toolkit does not change the public-site runtime. Repository tooling lives under `.github/scripts/`, and all generated preview state, browser profiles, audit reports, and screenshots are written under `/tmp`.

## Required workflow

1. Start or reuse the operator preview with `site.sh preview`. Keep the printed URLs available for visual review.
2. Run `site.sh check` before every commit that changes the site or its operational files.
3. For any visual, responsive, animation, scrolling, or interaction change, run `site.sh audit` and `site.sh capture`, then inspect the generated screenshots. `site.sh review` runs all three stages in sequence.
4. Commit and push only after the required local commands pass.
5. Run `site.sh deploy --marker "unique deployed text"` after every push. Add `--absent "removed text"` when applicable. Omit `--marker` only when a tooling/documentation-only commit intentionally changes no public HTML.

## Commands

### `preview [start|foreground|status|stop]`

Starts or reuses a Python HTTP server rooted at the repository on `127.0.0.1:4173`. It validates both HTML entry points before accepting an existing process. A managed background server records its PID and log under `/tmp`; `stop` refuses to terminate an unknown process. Use `preview foreground` in agent runners or ephemeral terminals that reap detached processes when a command exits; keep that terminal session open and stop it with Ctrl-C.

### `check`

Runs the mandatory static pre-commit gate:

- whitespace/error checks and both HTML parser checks;
- content invariants and security.txt expiry;
- local asset existence, external-runtime policy, orphan inventory, and size warnings;
- preview HTTP checks for both pages, security.txt, primary research/media, and every changed public file.

### `content`

Checks durable page invariants independently. Counts, prohibited phrases, required section IDs, fragment targets, analytics beacons, blog dormancy, the JavaScript year, and RFC 9116 fields are configured in `site-config.json` or encoded where structural context is required.

### `assets`

Checks HTML, CSS, and JavaScript asset references; rejects missing or unapproved external runtime assets; inventories `assets/` and `ataturk_pictures/`; and reports orphaned or unusually large files. Size findings are warnings so intentional research documents and archival images remain possible.

### `audit`

Uses an isolated local audit server and headless Chromium. It checks every route at mobile, desktop, and wide/4K sizes for horizontal overflow, missing or nested snap targets, broken loaded images, and browser errors. It also checks both routes in reduced-motion mode. The detailed JSON report is written to `/tmp/catakan-audit-TIMESTAMP.json`.

### `capture [--output DIR]`

Captures every configured snap section on both pages at mobile, desktop, and wide/4K sizes. The default output is `/tmp/catakan-preview-TIMESTAMP/`, with a `manifest.json` recording the source URL, viewport, section, dimensions, and screenshot path. Never copy these diagnostics into the repository.

### `review [--output DIR]`

Runs `check`, `audit`, and `capture` in order. This is the preferred command before handing off a visual change for operator review.

### `deploy [options]`

Delegates to `verify-deployment.sh`. It waits for the exact commit's GitHub Pages workflow, waits for the custom domain, checks local/tracking/public SHA parity, validates live routes and requested markers, confirms repository tooling is not public, and requires a clean worktree.

## Configuration and dependencies

Durable routes, snap targets, viewports, asset roots, analytics values, and content counts live in `site-config.json`. Update that file whenever an owner-approved structural change intentionally changes an invariant.

The scripts use Bash, Python 3 standard-library modules, Git, curl, xmllint, jq, and Chromium or Chrome. They introduce no package manager, build step, or browser-side dependency.
