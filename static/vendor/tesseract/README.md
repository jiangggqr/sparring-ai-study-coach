# Vendored Tesseract browser OCR

These files are self-hosted so scanned PDF pages can be recognized without sending the
PDF, rendered page, or extracted text to a third-party CDN.

Pinned packages:

- `tesseract.js` 7.0.0 — Apache-2.0 (`TESSERACT_JS_LICENSE.md`);
- `tesseract.js-core` 7.0.0 — Apache-2.0 (`TESSERACT_CORE_LICENSE`);
- `@tesseract.js-data/eng` 1.0.0 — MIT according to the package metadata;
- `@tesseract.js-data/chi_sim` 1.0.0 — MIT according to the package metadata.

The language-package MIT notice is reproduced in `TESSERACT_DATA_LICENSE`.

Only the LSTM browser core variants and the optimized `4.0.0_best_int` English and
Simplified Chinese data files are included. Tesseract.js feature-detects the best
compatible core at runtime; do not replace `corePath` with a single fixed core file.

SHA-256 checksums:

```text
64871d76c75609fd5413b88a8171e2ef40deedd77d5875ba23df104b2d05eb29  tesseract.esm.min.js
576b7df7e3393e137e51849357c9adb53fe7ac1bb69bfa06cf3d61520f182c6d  worker.min.js
eef5f8b2f8e20e150680b20adaec4a60babafee3adbe8a94583c81fee46e8680  core/tesseract-core-lstm.wasm.js
861a536cf9ef8e63cb644d57bab39c388f37f7d6b6f60024b741c5f6b39a59b3  core/tesseract-core-relaxedsimd-lstm.wasm.js
c58b46a4c796c0b8afccf77591d5b875b6896b45d402bbce8caa6f5362447b38  core/tesseract-core-simd-lstm.wasm.js
b8a23f10c7de500891eb458a8adc9cc58ab7f242f08b7d149f5e9aea4ad5db7c  tessdata/chi_sim.traineddata.gz
45b4cb346724ac1774f1c36f42f182b887bcdb28ebe63e6fff90ac41f3fcff91  tessdata/eng.traineddata.gz
```
