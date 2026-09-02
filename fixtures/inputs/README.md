# Input fixtures

These fixtures are synthetic test inputs. The manifest is intentionally kept
next to the files so `scripts/verify/verify_fixture_manifest.py` can verify size
and SHA-256 before tests use them.

| File | Bytes | SHA-256 | Purpose |
|---|---:|---|---|
| `valid-reference.png` | 185 | `0a973c86b1963678a4414a3bdf0d27df868ccd603b140a7209c9c1758f4208b0` | Valid supported PNG |
| `valid-reference.jpg` | 694 | `7aa76ffb5961533ccc9c4942ed60acbda017a6063ca7374bcdbdf1002f92bc08` | Valid supported JPEG |
| `corrupt-image.png` | 15 | `9b21135bbcfef66e3d3f3d689b0a4a216327f0b57b91d2b9f74a0f80cfa0a0d0` | Corrupt content rejected before queueing |
| `spoofed-extension.jpg` | 16 | `bffba3884ad05de5cb91d0dfc9be41dae72b14f2e59916e4d744e0b21b69739b` | Unsupported content with a misleading extension |
| `oversized-reference.png` | 10485761 | `11846650f3ba997ccc61bc9306d3ed2ecfca54ccfb15c1dc67293b02f10bc049` | Payload above the 10 MiB limit |

The values are generated once and must be refreshed only when the fixture content
changes intentionally.
