# Vendored browser document readers

## PDF.js

This directory contains the browser distribution from `pdfjs-dist` 6.2.108:

- `pdf.mjs` — legacy minified browser API build;
- `pdf.worker.mjs` — matching legacy minified worker;
- `cmaps/` and `standard_fonts/` — same-origin text-extraction support.

PDF.js is licensed under Apache-2.0. See `PDFJS_LICENSE`.

## Tesseract.js

`tesseract/` contains the pinned browser OCR runtime and English/Simplified Chinese
language data used only when PDF.js finds a scanned page without enough selectable
text. See `tesseract/README.md` for versions, checksums, and license notices.
