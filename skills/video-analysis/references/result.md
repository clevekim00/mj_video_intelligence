# Result interpretation

- `completed` means the requested runtime path completed, not that all facts in
  the video were discovered or verified.
- `needs_input` with `NEEDS_MEDIA` means no usable transcript is available.
  Show source metadata and request a local media file; a silent upload needs a
  different evidence source, since OCR/vision is not implemented.
- `failed` has an error and must not be reported as successful analysis.
- `execution.analysisMode=evidence-only` is transcription/collection, not
  semantic extraction. `transcript` contains the collected segments.
- `coverage.complete=true` in `full-transcript` means every collected transcript
  chunk was submitted, not that every visual/audio detail is represented.
- `selective` uses bounded agent search. Do not describe it as exhaustive.
- Finding evidence must match an original segment's start, end and text. This
  checks provenance, not semantic entailment or transcription accuracy.

`result.json` is the authoritative structured result; `report.md` is a concise
rendering. A skill may create a better report from that JSON, but should preserve
coverage, uncertainty, source identity and quoted evidence.
