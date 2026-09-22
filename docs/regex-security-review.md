# M7 custom regex safety control

## Decision

M7 custom recognizers use `google-re2`, imported as `re2`, for the custom-recognizer path only. Google RE2 uses a non-backtracking engine and gives linear-time matching for supported patterns.

Existing `re` usage in detection, masking, and other code paths is unchanged.

## Defence in depth

`frostglass/admin/custom_recognizers.py` retains a conservative pre-compile filter. It rejects:

- Invalid syntax.
- Backreferences and lookarounds, which RE2 does not support.
- Nested quantifiers and quantified alternation.
- Unbounded wildcard repetition and unbounded ranges.

The test suite rejects the following patterns before they reach RE2:

```text
(
(a+)+$
(a|aa)+$
.*secret
(?=secret)secret
(foo)\1
```

The suite also evaluates the adversarial nested-quantifier and quantified-alternation shapes with a 50,001-character non-match and asserts a bounded completion time. RE2, rather than a timing assertion, is the safety guarantee.

## Supported recognizer syntax

The M7 feature needs character classes, anchors, grouping, fixed or bounded quantifiers, and literal tokens. These are supported by RE2. Lookarounds and backreferences are intentionally unsupported and are not required by Part H.

## Remaining review

The M7 PR remains open for review of dependency provenance and the final live routing. The previous hard stop on a standard-library `re` implementation is cleared.
