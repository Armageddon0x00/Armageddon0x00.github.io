# Repository guide

This repository is the source for the main personal site at `https://catakan.net/`, hosted directly with GitHub Pages. It is a dependency-free static site: edit the HTML, CSS, and JavaScript in place and do not introduce a build step unless the project owner requests one.

## Site map

- `/` is the primary `catakan.net` experience and internet banner: identity, manifesto, selected cyber security research, certifications, an animated penetration and exploitation flow, and external signals.
- `/ataturk/` is the standalone Atatürk Köşesi experience.
- `blog.catakan.net` is currently only a reserved, dormant destination mentioned inside the main page. It is not a separate page in this repository.

## Structure

- `index.html`, `styles.css`, and `script.js` power the main `catakan.net` experience.
- `ataturk/` contains the standalone Atatürk Corner served from `/ataturk/`.
- `ataturk_pictures/` contains the Atatürk archive media used by that page.
- `assets/research/` contains locally hosted research documents.
- `assets/generic_images/` contains locally hosted visual assets used by the main page.
- `.well-known/security.txt` publishes the RFC 9116 vulnerability-reporting contact for `catakan.net`; keep its required expiry current.

## Local preview

Run the site from the repository root so relative asset paths match GitHub Pages:

```sh
python3 -m http.server 4173 --bind 127.0.0.1
```

Then open `http://127.0.0.1:4173/` or `http://127.0.0.1:4173/ataturk/`.

## Design and implementation conventions

- Keep the site dependency-free and usable without a framework.
- Keep the public presentation self-contained and agnostic. Do not expose third-party case names, box names, source labels, citations, reference sections, or resource appendices in visible narrative copy unless the project owner explicitly requests them.
- Translate research-inspired attack flows into anonymous technical patterns. Named destinations and locally hosted research artifacts explicitly selected by the project owner are exceptions.
- Preserve the full-page vertical scroll-snap behavior on both pages.
- On the main page, keep the selected research card and the dormant `blog.catakan.net` node together as one visual unit and one desktop snap viewport.
- Keep the certifications ledger as one dedicated snap viewport with all eight credentials visible at supported desktop, tablet, and standard mobile sizes.
- Treat each primary Atatürk section as one snap viewport unless its content intentionally requires internal vertical travel.
- Preserve Turkish spelling and diacritics in visible copy and accessibility text.
- Use `193∞`, never `1938`, throughout the Atatürk Corner.
- Keep images and documents local; avoid runtime dependencies on third-party hosts.
- Cloudflare Web Analytics is an owner-approved exception: keep the supplied beacon and token in both HTML entry points unless the project owner requests its removal.
- Maintain keyboard access, descriptive alternative text, reduced-motion behavior, and responsive layouts.
- Test normal desktop, mobile, and wide/4K viewports after visual changes.
- Do not commit temporary screenshots, browser profiles, or diagnostic output.

## Validation

Before committing, run:

```sh
git diff --check
xmllint --html --noout index.html
xmllint --html --noout ataturk/index.html
```

Also confirm that both local preview URLs return HTTP 200 and that the page has no horizontal overflow at the affected breakpoints.

## Post-push verification

- After pushing, run `.github/scripts/verify-deployment.sh --marker "unique text from the change"`; add `--absent "removed text"` when applicable.
- The verifier waits for the exact commit's Pages run, checks local/tracking/public SHA parity, validates live endpoints and markers, confirms repository tooling is not served, and requires a clean worktree.
- Use `--timeout` or `--interval` only when the default ten-minute wait or five-second poll is unsuitable. `GITHUB_TOKEN` is optional for a higher public API rate limit.
- Do not claim the deployment is live unless the script finishes with `DEPLOYED`; report its failure and the associated Actions URL instead.
