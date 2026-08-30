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
- `.github/scripts/` contains the mandatory local operator toolkit and its durable site invariants. Keep generated reports, screenshots, profiles, PIDs, and logs under `/tmp`, never in the repository.

## Local preview (mandatory)

- Start or reuse the managed preview before evaluating or handing off any site change. This command serves the repository root, validates both implemented routes, safely reuses a matching process, and prints the operator URLs:

```sh
.github/scripts/site.sh preview
```

- Keep the preview running while work is being reviewed. Report its printed URLs in the handoff so the operator can open the exact result before anything is pushed. Agent runners that reap detached processes must use `.github/scripts/site.sh preview foreground` in a persistent terminal session. Use `preview status` to inspect a background preview and `preview stop` only when it is no longer needed; the stop command intentionally refuses to terminate unmanaged processes.
- Open `http://127.0.0.1:4173/` for the main page and `http://127.0.0.1:4173/ataturk/` for Atatürk Köşesi. `blog.catakan.net` has no local preview route while it remains dormant.
- Run `.github/scripts/site.sh check`; its HTTP gate confirms both implemented routes, security.txt, primary media/research artifacts, and every changed public file are served successfully.
- Inspect the affected page in a real browser; an HTTP status check alone is not visual validation. For every visual or interaction change, `.github/scripts/site.sh audit` and `.github/scripts/site.sh capture` are mandatory. `site.sh review` runs `check`, `audit`, and `capture` together. Inspect the resulting mobile, desktop, and wide/4K screenshots rather than treating successful generation as visual approval.
- Exercise every affected interaction with pointer and keyboard input. This includes navigation, vertical scroll snapping, moving ribbons, galleries and lightboxes, reduced-motion behavior, external links, and any newly introduced control or animation.
- Refresh each affected route from a direct URL rather than relying only on in-page navigation. Confirm local assets still resolve and the browser console has no new errors attributable to the change.
- Do not use the production domain as a substitute for local preview. Production verification happens only after commit and push through the post-push verifier.

## Design and implementation conventions

### Main page (`https://catakan.net/`)

- Treat `index.html`, `styles.css`, and `script.js` as the dependency-free implementation of the main internet banner. Do not introduce a framework, package dependency, or build step unless the project owner requests it.
- Preserve the current content hierarchy: identity hero, manifesto, selected research with the dormant blog node, certifications, the animated penetration and exploitation flow, and the closing external-signals page.
- Preserve full-page vertical scroll snapping. The hero, manifesto, research/blog unit, certifications ledger, exploitation-flow section, and closing signals/footer unit are each one desktop snap viewport; never turn the blog node into an additional snap stop.
- Keep the selected research card and `blog.catakan.net` node together as one visual unit. Keep the certifications ledger in its own snap viewport with all eight credentials visible at supported desktop, tablet, and standard mobile sizes.
- Keep visible security narratives self-contained and target-agnostic. Translate research-inspired attack flows into anonymous technical patterns; do not expose third-party case names, box names, source labels, citations, reference sections, or resource appendices unless the project owner explicitly requests them. Named destinations and locally hosted research artifacts explicitly selected by the owner are exceptions.
- Keep the top-right destination labelled `Atatürk Köşesi`, using Atatürk's locally stored signature rather than a generic icon.
- Keep images and research documents local. The owner-approved Cloudflare Web Analytics beacon is the only current runtime dependency on a third-party host; preserve its supplied token unless the owner requests its removal.
- Maintain keyboard access, descriptive alternative text, reduced-motion behavior, and responsive layouts. Test normal desktop, standard mobile, tablet, and wide/4K viewports after visual changes.

### Atatürk Köşesi (`https://catakan.net/ataturk/`)

- Treat `ataturk/index.html`, `ataturk/ataturk.css`, and `ataturk/ataturk.js` as a standalone, dependency-free experience served only from `/ataturk/`.
- Preserve full-page vertical scroll snapping. Treat the hero, Cumhuriyet scene, moving visual archive, and animated closing scene as individual snap viewports unless a section intentionally requires internal vertical travel.
- Keep `ataturk_trablusgarp.jpg` as the primary hero image and `ataturk_cumhuriyet_gif.gif` as the primary Cumhuriyet animation. Use every archive image through local files in `ataturk_pictures/`; do not hotlink media or add visible source, citation, reference, or appendix copy.
- Preserve the historical flag ribbon and the animated Turkish flags in the closing scene. Render Turkish flags accurately, including correctly oriented crescents and stars, and prefer repository-native SVG/CSS assets over remote images.
- Preserve Turkish spelling and diacritics in visible copy and accessibility text. Use `193∞`, never `1938`, throughout this experience, and do not reintroduce `Hayatta en hakiki mürşit ilimdir.` without an explicit request from the project owner.
- Keep the route back to the main page functional, all gallery images keyboard-accessible and expandable, and motion meaningful but safe under `prefers-reduced-motion`.
- Keep all images and documents local. Preserve the owner-approved Cloudflare Web Analytics beacon and supplied token in the Atatürk HTML entry point unless the owner requests its removal.
- Test normal desktop, standard mobile, tablet, and wide/4K viewports after visual changes, including snap behavior, archive motion, flags, and lightbox interaction.

### Blog (`blog.catakan.net`)

- Treat the blog as reserved and dormant. It currently exists only as the `blog.catakan.net` future-node inside the main page's selected-research section; there is no blog HTML entry point, route, subdirectory, application, deployment, or separate page in this repository.
- Do not make the future-node interactive, create placeholder blog pages, configure a subdomain, add a build system, or imply that the blog is live unless the project owner explicitly requests activation.
- Keep the node's purpose limited to a future home for the owner's original research, field notes, and findings. Keep it visually integrated with the selected research card and within the same desktop snap viewport.
- When the owner activates the blog, define its architecture, publishing workflow, analytics, accessibility, and deployment boundary before implementation. Do not assume the main site's static-file conventions or Cloudflare beacon automatically apply to that future system.
- Future public research writing must remain self-contained and target-agnostic by default; references to third-party cases, resources, or source material require explicit owner direction.

## Validation

Before every commit that changes the site, its content, assets, or operator tooling, run:

```sh
.github/scripts/site.sh check
```

The command is mandatory even for apparently isolated changes. It runs `git diff --check`, both `xmllint` checks, content invariants, asset inventory, local endpoint checks, and changed-public-file checks. Do not bypass it by running only its individual subcommands.

For visual, responsive, animation, scrolling, or interaction changes, run the complete browser review before committing:

```sh
.github/scripts/site.sh review
```

Review the generated screenshots and JSON audit report under `/tmp`. Automated browser success does not replace manual pointer, keyboard, animation, and visual inspection. Do not commit temporary screenshots, browser profiles, logs, or diagnostic output.

Use `.github/scripts/site.sh content` or `assets` for focused diagnosis, not as substitutes for the mandatory complete gate. Update `.github/scripts/site-config.json` when an owner-approved structural change intentionally alters routes, snap targets, viewport coverage, asset policy, analytics values, or content counts. Full command documentation is in `.github/scripts/README.md`.

## Post-push verification

- After every push, run `.github/scripts/site.sh deploy --marker "unique text from the change"`; add `--absent "removed text"` when applicable. Omit `--marker` only for tooling/documentation-only commits that intentionally change no public HTML.
- The verifier waits for the exact commit's Pages run, checks local/tracking/public SHA parity, validates live endpoints and markers, confirms repository tooling is not served, and requires a clean worktree.
- Use `--timeout` or `--interval` only when the default ten-minute wait or five-second poll is unsuitable. `GITHUB_TOKEN` is optional for a higher public API rate limit.
- Do not claim the deployment is live unless the script finishes with `DEPLOYED`; report its failure and the associated Actions URL instead.
