# Lab 06 — Bug Report

Each bug below was introduced **one at a time** in `app/routers/artworks.py`. After every mutation, I ran `python -m pytest -q --tb=no`, recorded the affected tests, and restored the original router before trying the next bug.

| Bug | Test(s) that failed (or had fixture setup errors) |
| --- | --- |
| **1 — POST returns 200 instead of 201** | `test_create_artwork` **failed**. Six tests **errored during fixture setup** because `created_artwork` expected a 201: `test_create_artwork_is_saved`, `test_update_artwork`, `test_delete_artwork`, `test_create_duplicate`, `test_create_duplicate_ignores_case`, `test_update_same_title_and_artist_is_allowed`. |
| **2 — Duplicate check is case-sensitive** | `test_create_duplicate_ignores_case` |
| **3 — An artwork counts as a duplicate of itself** | `test_update_same_title_and_artist_is_allowed` |
| **4 — DELETE does not actually delete** | `test_delete_artwork` |
| **5 — Artist filter only matches the beginning of a name** | `test_filter_by_artist[lowercase-partial]`, `test_filter_by_artist[da-vinci-partial]` |

## Results of each intentional bug

| Bug | pytest results with bug in place |
| --- | --- |
| 1 | 1 failed, 27 passed, 6 errors |
| 2 | 1 failed, 33 passed |
| 3 | 1 failed, 33 passed |
| 4 | 1 failed, 33 passed |
| 5 | 2 failed, 32 passed |

All five intentional bugs were detected by the tests. **Every mutation was reverted.** With the original router restored, all **34 tests passed** (`python -m pytest -q`). The original `artworks.db` also has identical bytes to the copy included in the instructor's starter ZIP.
