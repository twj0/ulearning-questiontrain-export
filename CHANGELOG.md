# Changelog

All notable changes to this project will be documented in this file.

## [0.1.3] - 2026-01-12

### Fixed

- Fix double-encoded HTML entities not being decoded properly.
  - Issue: Characters like `&ldquo;` `&lt;` `&gt;` appeared in exported text when the platform returned double-encoded entities (e.g. `&amp;ldquo;`).
  - Solution: Call HTML entity decode twice to handle double-encoded cases.
  - Affected: Python `formatter.py` and UserScript `_userscript.js`.
  - See: `docs/double-encoded-html-entities.md` for details.

## [0.1.2] - 2025-12-16

### Changed

- Userscript: strip HTML tags from exported text to improve readability.
  - Convert `<br>` / `<br/>` / `<br />` to `\n`.
  - Convert common block endings like `</p>` to `\n`.
  - Remove other tags and decode HTML entities.
- Python exporter: apply the same HTML stripping rules in the formatter, so `题干/选项/问答题答案` no longer contain raw HTML.

### Notes

- This cleanup happens only at export time (linear scan), and is negligible compared to network request time. It also improves searchability by removing tag noise.

## [0.1.1] - 2025-12-16

### Changed

- Default export mode now prefers "standard answers" (platform `correctAnswer`) instead of user-submitted answers.
  - Implementation uses `POST /questionTraining/student/answer` with a dummy answer to retrieve `result.correctAnswer`.
  - Userscript: default button exports correct answers.
  - Python: default CLI exports correct answers; legacy mode `--user-answer` exports user's submitted answers without submitting.

### Fixed

- Userscript: `{"code":2001,"message":"缺少访问token"}`
  - Improve Authorization handling by normalizing token and adding `Bearer` prefix when needed.
  - Provide clearer error message to prompt re-login and cookie verification.
- Python: `ConnectionResetError(10054)` when submitting many answers
  - Add retry with exponential backoff + jitter for `submit_answer` calls.
  - Increase default submission delay.

### Improved

- Question type detection: if extracted answer is boolean-like (`true/false`), force it to be `判断题` and map to `正确/错误`.
