# Repository guide

This repository is the source for `catakan.net`, hosted directly with GitHub Pages. It is a dependency-free static site: edit the HTML, CSS, and JavaScript in place and do not introduce a build step unless the project owner requests one.

## Structure

- `index.html`, `styles.css`, and `script.js` power the main research landing page.
- `ataturk/` contains the standalone Atatürk Corner served from `/ataturk/`.
- `ataturk_pictures/` contains the Atatürk archive media used by that page.
- `assets/research/` contains locally hosted research documents.

## Local preview

Run the site from the repository root so relative asset paths match GitHub Pages:

```sh
python3 -m http.server 4173 --bind 127.0.0.1
```

Then open `http://127.0.0.1:4173/` or `http://127.0.0.1:4173/ataturk/`.

## Design and implementation conventions

- Keep the site dependency-free and usable without a framework.
- Preserve the full-page vertical scroll-snap behavior on both pages.
- Treat each primary Atatürk section as one snap viewport unless its content intentionally requires internal vertical travel.
- Preserve Turkish spelling and diacritics in visible copy and accessibility text.
- Use `193∞`, never `1938`, throughout the Atatürk Corner.
- Keep images and documents local; avoid runtime dependencies on third-party hosts.
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
