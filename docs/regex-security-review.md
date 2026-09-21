# M7 custom regex safety review required

## Status

Blocked before custom recognizers can be wired into the live Admin API or saved by operators.

## Implemented isolated control

`frostglass/admin/custom_recognizers.py` applies a conservative syntax filter before Python `re.compile`:

- Limits a pattern to 256 characters.
- Rejects invalid syntax.
- Rejects backreferences and lookarounds.
- Rejects nested quantifiers and quantified alternation.
- Rejects unbounded wildcard repetition and unbounded ranges.

The current tests reject these concrete patterns:

```text
(
(a+)+$
(a|aa)+$
.*secret
(?=secret)secret
(foo)\1
```

A bounded token pattern such as `AKIA[0-9A-Z]{16}` is accepted and reports match spans.

## Why this is not approved

Python's `re` engine has no reliable per-match timeout. The syntax filter is a defensive heuristic, not a proof that every accepted pattern has bounded execution time. It can also reject safe patterns and may miss a pathological accepted pattern.

## Required security decision

Do not expose custom-recognizer save or enable operations until review chooses one of these controls:

1. A dedicated regex engine with a hard execution limit and a documented supported syntax.
2. Isolated, resource-limited regex evaluation outside request handling.
3. A smaller, formally constrained recognizer grammar with a documented complexity bound.

The M7 PR must remain open for this security review.
