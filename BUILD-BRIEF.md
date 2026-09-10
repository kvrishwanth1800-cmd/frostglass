# Frostglass — Complete Build Brief for an Autonomous Coding Agent

**Document type:** Engineering brief + agent operating manual
**Deliverable:** A production-quality open-source AI gateway with data-loss prevention
**License:** Apache-2.0
**Status:** Ready to execute — start at Part A

> **Place this file at the repository root as `BUILD-BRIEF.md` and commit it in the first commit.**
> Every agent session must read it before writing code.

---

# TABLE OF CONTENTS

| Part | Contents |
|---|---|
| **A** | How to drive the agent — bootstrap, resume, and milestone prompts |
| **B** | Review gates — seven reviewer prompts (QA, tester, security, UX, perf, docs, product) |
| **C** | Product definition |
| **D** | Naming and repository metadata |
| **E** | Git structure and workflow |
| **F** | System architecture |
| **G** | Prescribed tech stack |
| **H** | Component specifications |
| **I** | Data model |
| **J** | Configuration |
| **K** | Milestones M0–M9 |
| **L** | Testing strategy |
| **M** | Security and threat model |
| **N** | Performance targets |
| **O** | Open-source housekeeping |
| **P** | Risks and honest caveats |
| **Q** | Final Definition of Done |

---

# PART A — HOW TO DRIVE THE AGENT

## A.0 The core problem this part solves

Long builds fail in two ways: the agent **stops mid-milestone** and the next session has no idea where it was, or the agent **declares victory early** because nothing forced it to verify. Part A fixes the first, Part B fixes the second.

The mechanism is a single tracked file, `STATUS.md`, that the agent updates continuously. It is the project's memory between sessions.

## A.1 `STATUS.md` — the resume contract

Create this in M0 and **update it in every single commit**. It lives at the repo root and is committed like code.

```markdown
# Build Status

**Current milestone:** M3 — Masking engine
**Branch:** m3-masking-engine
**Last updated:** 2026-09-09 by agent-session-14

## Milestone progress
- [x] M0 Repository foundation      — merged, PR #1
- [x] M1 Pass-through gateway       — merged, PR #4
- [x] M2 Detection engine           — merged, PR #9
- [ ] M3 Masking engine             — IN PROGRESS
- [ ] M4 Policy engine + shadow mode
- [ ] M5 Audit + Admin API
- [ ] M6 Dashboard
- [ ] M7 Detectors, dictionaries, suggestions
- [ ] M8 Hardening, docs, 1.0 release

## M3 task state
- [x] surrogates.py — all generators except DATE
- [x] consistency.py — request + session scope
- [ ] surrogates.py — DATE constant-offset shifting   ← NEXT
- [ ] vault.py — encryption at rest
- [ ] restore.py — streaming buffer algorithm
- [ ] tests: stream-split at every offset

## Open decisions / blockers
- None

## Notes for the next session
- Vault TTL is configurable but the purge job is not written yet; it is
  tracked as an M5 task, not M3.
- `surrogates.py` uses a seeded Faker instance per tenant salt. Do not
  reseed per call or consistency breaks.
```

**Rules:**
- The agent updates `STATUS.md` **before ending any session**, whether or not work is complete.
- "Notes for the next session" must contain enough context that a fresh agent with no memory can continue without re-reading the whole codebase.
- Never mark a task `[x]` unless its tests exist and pass.

## A.2 Bootstrap prompt — paste this first, once

```
You are the implementing engineer for an open-source project. The repository
is connected and empty (or nearly so).

Your specification is BUILD-BRIEF.md. If it is not yet in the repo, I have
provided it in this conversation — commit it to the repo root as the very
first thing you do.

Read BUILD-BRIEF.md in full before writing any code. Then:

1. Confirm back to me, in under 200 words: what we are building, the name,
   the tech stack, and the list of milestones. If anything in the brief is
   contradictory or unclear, list those items now — do not start coding with
   unresolved ambiguity.

2. Once I confirm, execute Milestone M0 exactly as specified in Part K.

Working rules (from Part A.5 of the brief, non-negotiable):
- One branch and one pull request per milestone.
- Conventional commits.
- Every milestone ships tests. A milestone is not done without them.
- CI must be green before you open the PR.
- Update STATUS.md and CHANGELOG.md in every commit.
- Never commit secrets. Ship .env.example only.
- Do not substitute the prescribed tech stack. If you believe a substitution
  is necessary, open a GitHub issue explaining why and wait.
- If the spec is ambiguous, choose the simpler implementation and record the
  assumption as an ADR in docs/decisions/. Never silently invent product
  behaviour.
- Security beats convenience every time. If a requirement conflicts with
  Part M, stop and ask.

Do not proceed past M0 until I have run the review gates in Part B and told
you the milestone is accepted.
```

## A.3 Resume prompt — paste this at the start of every later session

```
You are resuming work on this repository. You have no memory of previous
sessions.

Do these in order before anything else:

1. Read BUILD-BRIEF.md — your full specification.
2. Read STATUS.md — the current state of the build.
3. Run `git log --oneline -20` and `git status` to confirm STATUS.md matches
   reality. If they disagree, trust the repository and correct STATUS.md.
4. Run the test suite. Report what passes and what fails.

Then report to me, in under 150 words:
- Which milestone is in progress
- Which specific task is next
- Anything in "Notes for the next session" that affects how you proceed
- Any discrepancy you found between STATUS.md and the actual repo

Then continue from the next unchecked task. Do not restart completed work.
Do not refactor things outside the current milestone's scope.
```

## A.4 Per-milestone prompt template

```
Execute Milestone [M#]: [name] exactly as specified in Part K of
BUILD-BRIEF.md.

Before you start:
- Create branch [branch-name] from an up-to-date main.
- Re-read the component specification in Part H that this milestone
  implements, plus Part L (testing) for the parts that apply.
- Update STATUS.md to mark this milestone IN PROGRESS with the task list.

While working:
- Commit incrementally with conventional commit messages. Do not build the
  whole milestone in a single commit.
- Update STATUS.md task checkboxes as you complete each one.

Before opening the PR, run this self-check and paste the results into the PR
description:
- [ ] Every Definition of Done item for this milestone is met — quote each
      one and state how it is satisfied
- [ ] Every acceptance test ID listed for this milestone exists and passes
- [ ] `ruff check`, `ruff format --check`, and `mypy` pass
- [ ] Test coverage meets the gate in Part L.3
- [ ] CHANGELOG.md updated
- [ ] STATUS.md updated
- [ ] No secrets, keys, or real personal data committed
- [ ] Any assumptions recorded as ADRs in docs/decisions/

If you cannot honestly tick an item, say so explicitly rather than opening
the PR. A blocked milestone reported clearly is worth far more to me than a
milestone declared finished that isn't.
```

## A.5 Non-negotiable working rules

1. Milestones run **in order**, M0 → M8. M9 is optional and only after v1.0 is tagged.
2. One branch, one PR per milestone. Branch naming: `m3-masking-engine`.
3. Conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`, `perf:`, `sec:`.
4. **Every PR ships tests.** No tests, no merge.
5. CI green before the PR is opened, not after review.
6. **No secrets in git, ever.** `.env.example` with empty values only.
7. **No real personal data in the test corpus, ever.** Synthetic or public test data only.
8. Do not substitute the prescribed stack (Part G) without an approved issue.
9. Ambiguity → simpler implementation + an ADR in `docs/decisions/`. Never invent product behaviour silently.
10. Security beats convenience. Conflicts with Part M stop work and get escalated.
11. **Do not refactor outside the current milestone's scope.** Note it as an issue instead.
12. `STATUS.md` and `CHANGELOG.md` updated in every commit.

---

# PART B — REVIEW GATES

After each milestone PR is opened and **before you merge it**, run the relevant reviewer prompts below in a fresh session. Each is written to be pasted as-is.

**Which gates apply to which milestone:**

| Milestone | Required gates |
|---|---|
| M0 | B.6 Docs/DX |
| M1 | B.1 QA, B.3 Security, B.5 Performance |
| M2 | B.1 QA, B.2 Adversarial Tester |
| M3 | B.1 QA, B.2 Adversarial Tester, B.3 Security |
| M4 | B.1 QA, B.2 Adversarial Tester, B.7 Product |
| M5 | B.1 QA, B.3 Security, B.5 Performance |
| M6 | B.1 QA, B.4 UX, B.7 Product |
| M7 | B.1 QA, B.4 UX, B.7 Product |
| M8 | **All seven** |

**Rule:** every finding from a review gate becomes either a fix in the same PR or a tracked GitHub issue with a severity label. Nothing is dismissed silently. Critical and high severity findings block the merge.

---

## B.1 QA Engineer

```
You are a senior QA engineer reviewing pull request [#N] on this repository.
You did not write this code and you are not here to be agreeable.

Your specification is BUILD-BRIEF.md, Part K (the milestone's Definition of
Done) and Part L (testing strategy).

Do this:

1. Read the milestone's Definition of Done. For each item, find the evidence
   in the code and tests that it is actually satisfied. State PASS, FAIL, or
   UNVERIFIABLE for each, with file and line references. "The PR says it's
   done" is not evidence.

2. Confirm every acceptance test ID listed for this milestone exists, is
   actually asserting the behaviour it claims, and is not a placeholder. Flag
   any test that would pass even if the feature were deleted.

3. Find untested paths. Specifically hunt for:
   - error and exception branches
   - empty, null, and boundary inputs
   - concurrent and race conditions
   - configuration variants (SQLite vs Postgres, Redis vs in-memory,
     streaming vs non-streaming, shadow mode on vs off)

4. Run the test suite and the coverage report. Report actual numbers against
   the Part L.3 gates.

5. List every bug and gap you found, ranked: CRITICAL / HIGH / MEDIUM / LOW.
   For each, give the reproduction and the file to fix.

End with a single verdict: ACCEPT, ACCEPT WITH FIXES (list them), or REJECT
(state the blocking reason). Do not soften the verdict to be polite.
```

## B.2 Adversarial Tester

```
You are a QA specialist whose entire job is to break this feature. Assume the
implementing engineer was optimistic and tested the paths that work.

Context: this is Frostglass, an AI gateway that detects and masks sensitive
data in LLM prompts before they leave a company's network. Read BUILD-BRIEF.md
Parts H.2 (detection), H.3 (masking), and H.4 (policy).

Attack it on these axes and write a concrete failing test case for every
weakness you find:

DETECTION EVASION — try to get sensitive data past the detector:
- Obfuscation: "j dot smith at acme dot com", "4111 1111 1111 1111" with odd
  spacing, unicode homoglyphs, zero-width characters, base64, ROT13
- Splitting a value across message boundaries or across tool-call arguments
- Sensitive data inside code blocks, JSON payloads, SQL, YAML, CSV
- Non-English text and mixed-script strings
- Very long inputs, and inputs at the exact token/length limits
- Data hidden in fields the extractor might not walk: system prompt, tool
  definitions, tool results, multi-part content arrays, image alt text

MASKING FAILURES — try to break correctness:
- Overlapping detected spans, adjacent spans, spans at index 0 and at EOF
- A surrogate value that itself matches a detector (recursive masking)
- A surrogate split across SSE chunk boundaries at every possible offset
- Same value appearing 100 times — does consistency hold?
- Multi-turn conversation — does the identity stay stable across turns?
- Dates: do intervals between them survive the shift?
- What happens if the vault is empty, expired, or unreachable at restore time?

POLICY BYPASS:
- Conflicting rules at the same specificity
- A request that matches both a block rule and an allow rule
- Shadow mode combined with a block rule — does anything leak or get wrongly
  blocked?
- Policy changed mid-conversation

For each finding: give the exact input, the observed behaviour, the expected
behaviour, and a severity. Write the failing test.

Report the count of successful bypasses. If it is zero, say so and explain
what you tried — that is a meaningful result, not a failure to find work.
```

## B.3 Security Reviewer / Red Team

```
You are a security engineer reviewing this codebase before an open-source
release. Treat this as a real audit.

Critical context: Frostglass is a proxy that sees EVERY AI prompt in a
company. It is the single highest-value target in the network it is deployed
into. A vulnerability here is not a bug, it is a breach of every secret the
company has ever typed into an AI tool.

Read BUILD-BRIEF.md Part M (threat model) and audit against it.

Check every one of these and report PASS / FAIL / NOT IMPLEMENTED with file
references:

SECRETS AND CREDENTIALS
- Are vendor API keys ever returned by any endpoint, logged, or rendered to
  the browser?
- Are virtual keys hashed at rest? Is comparison constant-time?
- Does the app refuse to boot with a missing or default encryption key?
- Scan the entire git history, not just HEAD, for committed secrets.

THE VAULT (surrogate ↔ original mapping)
- Encrypted at rest with a key held outside the database?
- Is the TTL enforced, and is expired data actually purged?
- Can any API endpoint be induced to return vault contents?

THE AUDIT DATABASE
- With content capture disabled, prove no raw sensitive value reaches any
  table. Write a test that seeds known corpus values and greps every column.
- Are Finding records storing raw matched values anywhere? They must not.

ACCESS CONTROL
- Is RBAC enforced server-side on every /admin endpoint, or does any endpoint
  trust a client-supplied role?
- Can an `auditor` mutate policy? Can a `viewer` read captured content?
- Is there an IDOR anywhere — can user A fetch user B's request by ID?

INJECTION AND NETWORK
- SSRF via provider base-URL configuration — are private IP ranges blocked?
- SQL injection through filter parameters on list endpoints
- XSS in the dashboard where prompt content or entity values are rendered
- Prompt injection: can a crafted prompt cause the response restoration step
  to reveal values it should not?

SUPPLY CHAIN
- Are dependencies pinned with hashes? Is pip-audit in CI? Is there an SBOM?
- Reference case: the March 2026 supply-chain incident involving a widely-used
  LLM proxy. Assume the same attack will be attempted here.

FAILURE MODES
- If detection throws, does the request fail open (data leaks) or fail closed?
  Default must be fail-closed. Verify it.
- If Redis is down, what happens to masking?

For each finding: severity (CRITICAL/HIGH/MEDIUM/LOW), the attack path, the
impact, and the fix. CRITICAL and HIGH block the merge.

End with: is this safe to release publicly? Yes or no, with reasons.
```

## B.4 UX Reviewer

```
You are a product designer reviewing the Frostglass dashboard.

The users are two people with different needs:
- A security/platform engineer who wants to see what's leaving the network
  and investigate specific incidents.
- A compliance officer with no engineering background who needs to configure
  what gets masked and prove it to an auditor.

Read BUILD-BRIEF.md Part H.6 for the intended design direction and page specs.

Evaluate, page by page:

1. THE CORE TASK TEST. Without reading any documentation, can you:
   - Find who sent the most flagged prompts this week?
   - Determine exactly why a specific request was blocked?
   - Change PERSON from `allow` to `pseudonymize` and preview the effect
     before saving?
   If any of these takes more than three clicks or requires guessing, that is
   a finding.

2. DESIGN DIRECTION. The brief specifies that colour is reserved exclusively
   for policy outcomes (blocked / masked / shadow) and nothing else. Verify
   this holds. Flag any decorative use of colour, any gradient used as
   ornament, any place where identical rounded cards have been used to chop
   up content that isn't actually a set of peers.

3. INFORMATION DENSITY. This is an operations tool, not a marketing page.
   Flag wasted vertical space, tables that show fewer than ~20 rows without
   scrolling, and any chart that conveys less than the table it replaced.

4. STATES. Every view needs loading, empty, error, and permission-denied
   states. Empty states must tell the user what to do next, not just say "No
   data". Errors must say what happened and how to fix it, never apologise or
   be vague.

5. COPY. Check labels are written from the user's perspective in plain
   language, buttons say exactly what happens ("Save policy", not "Submit"),
   and an action keeps the same name through its whole flow.

6. ACCESSIBILITY. Keyboard navigation through the full policy editor, visible
   focus states, contrast ratios on the signal colours, screen-reader labels
   on icon-only buttons, and reduced-motion respected.

7. THE TRUST TEST. This is a security tool. Does the interface make the user
   feel they can verify what it claims, or does it ask to be believed? Flag
   anywhere a number is shown without a way to drill into what produced it.

Rank findings CRITICAL / HIGH / MEDIUM / LOW. Be specific — "improve the UX"
is not a finding; "the blocked-request reason is truncated at 40 characters
so the operator cannot see which rule fired" is.
```

## B.5 Performance Engineer

```
You are a performance engineer benchmarking this build.

Read BUILD-BRIEF.md Part N for the targets. Measure each one and report the
actual number against the target. Do not estimate — measure.

1. LATENCY. Using a mock provider so vendor latency is excluded, measure the
   added p50/p95/p99 latency of the Frostglass hop for:
   - deterministic detection only (regex, checksum, dictionary)
   - full pipeline including NER
   - streaming: added time-to-first-token

2. THROUGHPUT. Single instance, sustained load. Find the rps at which p95
   exceeds the latency budget. Report it.

3. THE DASHBOARD. Seed 100,000 audit rows. Measure p95 on every list
   endpoint. Check the query plans — flag any sequential scan on the
   `requests` or `findings` tables and name the missing index.

4. MEMORY. Steady-state RSS with the NER model loaded. Check for leaks: run
   10,000 requests and report whether memory returns to baseline.

5. HOT PATHS. Profile a single request and report where the time actually
   goes. Specifically check:
   - Is the dictionary matcher O(n) (Aho-Corasick) or is it looping regexes?
   - Is the spaCy model loaded once at startup or per request?
   - Is the streaming restore buffer holding back more than it needs to?
   - Are there any synchronous/blocking calls on the async path?

6. DEGRADATION. What happens under Redis latency, database slowness, and
   provider timeouts? Does the proxy queue, drop, or block?

Report every measurement in a table: metric, target, actual, PASS/FAIL. For
each FAIL, identify the specific bottleneck and propose the fix.
```

## B.6 Documentation and Developer Experience Reviewer

```
You are a developer who has never seen this project. You found it on GitHub
five minutes ago.

Do not read the source code. Use only the README and docs/.

1. THE TEN-MINUTE TEST. Following only the README, go from `git clone` to a
   working masked request. Time yourself. Record every point where you had to
   guess, look at the source, or search elsewhere. Each of those is a
   documentation bug.

2. THE README. Within the first screen, can you tell:
   - What this does, in one sentence?
   - Whether it solves your problem?
   - What it does NOT do?
   - How to try it?
   If any answer is no, that is a HIGH finding. Check that the architecture
   diagram and a dashboard demo GIF are above the fold.

3. ACCURACY. Run every command in the docs verbatim. Report any that fail,
   any output that doesn't match what's documented, and any env var mentioned
   in docs but absent from .env.example (or vice versa).

4. CONTRIBUTOR PATH. Using CONTRIBUTING.md alone, can you set up a dev
   environment and run the tests? Is there a documented, genuinely easy first
   contribution — adding a new detector should be it.

5. HONESTY. This project is a security tool. Check the docs state plainly:
   detection is probabilistic and will miss things; masking can still change
   model behaviour; this is not legal compliance. Flag any overclaim, any
   unqualified accuracy number, and any comparison to another project that
   isn't fair.

6. API DOCS. Is the OpenAPI schema published and complete? Are the policy
   YAML reference and the masking-modes doc sufficient to configure the tool
   without reading Python?

Report findings ranked, with the exact file and line to fix.
```

## B.7 Product Acceptance Reviewer

```
You are the product manager for Frostglass. You are accepting or rejecting
this milestone against the user's actual need, not against the ticket.

The real user problem, in the user's own words:
"My company took an enterprise AI, the whole team is using the API, but we
don't know whether sensitive info is being sent to the AI or not. And when we
mask it, we can't lose the context — the prompt still has to work."

Read BUILD-BRIEF.md Part C (product definition) and Part Q (final DoD).

Assess:

1. DOES IT SOLVE THE STATED PROBLEM? Not "does it implement the spec" — does
   a real company get the outcome they wanted? Walk through it as the buyer:
   deploy, point one base URL, see what's leaving, turn on masking safely.

2. THE CONTEXT-PRESERVATION TEST. This is the make-or-break requirement. Take
   five realistic business prompts containing sensitive data (a customer
   apology email, a support ticket triage, an invoice question, a code review
   with credentials, a meeting summary with names and dates). Mask each one.
   Then judge: would a model still produce a good answer from the masked
   version? Where the answer degrades, say exactly what was lost and why.
   Specifically verify that date intervals survived and that the same person
   kept the same name across turns.

3. THE ADOPTION TEST. Would a cautious security team actually turn this on in
   production? Check that shadow mode genuinely lets them measure before
   enforcing, and that nothing forces an all-or-nothing rollout.

4. THE NON-ENGINEER TEST. Could a compliance officer configure the mask/allow
   policy without help? Watch for anywhere the UI leaks implementation
   concepts (confidence thresholds, recognizer names, regex) without
   explaining them in plain language.

5. SCOPE DISCIPLINE. Flag anything built that isn't in the milestone, and
   anything in the milestone that was quietly skipped.

6. HONEST GAPS. List what a user would reasonably expect that this does not
   yet do, and confirm the docs say so.

Verdict: ACCEPT / ACCEPT WITH FIXES / REJECT, with the reasoning. If you'd
be embarrassed to demo this to a security team, say so plainly.
```

---

# PART C — PRODUCT DEFINITION

## C.1 The pitch

**Frostglass is a self-hosted AI gateway that stops sensitive data from leaving your company inside AI prompts — without breaking the prompt.**

Companies have bought enterprise AI. Their whole team now pastes work into it. Nobody knows what is going out. Network firewalls cannot read prompt *content*, so there is a total blind spot between the employee's keyboard and the vendor's API.

Frostglass sits in the middle. Every prompt passes through it. It detects sensitive values, replaces them with realistic stand-ins that preserve meaning, forwards the safe version, and swaps the real values back into the response so the employee never notices. Everything is logged — who sent what, what was masked, what was blocked, and why — and the whole policy is controlled from a dashboard by people who don't write code.

## C.2 Why "Frostglass"

Frosted glass lets shape and light through but hides the detail behind it. That is precisely the product: the model still sees *a person, a date, an amount, a customer* — but never the real values. **Preserving context while removing specifics is the entire technical thesis.** Every design decision defers to it.

## C.3 Users

- **Primary:** a security/IT/platform engineer at a 50–5,000 person company who has been asked "can you prove we aren't leaking customer data into that thing?"
- **Secondary:** compliance/DPO staff who need an audit trail and who need to *configure* masking without writing code.
- **Tertiary:** individual developers wanting a local privacy proxy in front of their own AI usage.

## C.4 Success criteria for v1.0

- `docker compose up`, repoint one base URL, and within an hour see what the team is actually sending to AI vendors.
- Masking can be turned on gradually — **shadow mode first** — without breaking a single workflow.
- A non-engineer can change what gets masked from the dashboard.
- **Masked prompts still produce good answers.** A tool that redacts everything into `[REDACTED]` and ruins responses gets uninstalled in a week.

## C.5 Explicit non-goals for v1

Do not build these. They are scope traps.

- Model hosting, fine-tuning, or training
- A general-purpose API gateway for non-AI traffic
- Agent orchestration or MCP governance
- Browser extension (M9, optional)
- Multi-region HA, sharding, or anything beyond single-instance + Postgres
- Mobile apps

---

# PART D — NAMING AND REPOSITORY METADATA

## D.1 Repository name

**Primary: `frostglass`**

**Verify availability before committing** — check all four:
```
github.com/search?q=frostglass
pypi.org/project/frostglass
npmjs.com/package/frostglass
frostglass.dev / frostglass.io
```

Fallbacks in order: **`cloakroom`** (you check your sensitive data at the door), **`maskwall`**, **`obscura-gateway`**, **`chaffproxy`**.

**Names already occupied in this exact category — do not use:** `veilgate` (Apache-2.0 security reverse proxy on GitHub + veilgate.dev), `promptguard` (existing LiteLLM guardrail provider), `llm-guard` (Protect AI), `presidio` (Microsoft), `aegis` (NVIDIA), `checkpoint` (Check Point Software).

## D.2 The honest note on discoverability

A repo name does not generate search traffic. `presidio`, `bifrost`, `portkey`, and `lakera` all rank well with non-descriptive names. What gets indexed is **the repo description, the GitHub topics, and the first two lines of the README**. The name should be memorable and unique; the *description* carries the keywords.

## D.3 Exact metadata to set

**Description** — use verbatim:
> Self-hosted AI gateway and DLP proxy that detects and masks PII, secrets, and confidential data in LLM prompts before they leave your network. Context-preserving redaction, policy dashboard, and full audit trail for OpenAI, Anthropic, Gemini, and local models.

**Topics** — add all:
```
llm  ai-gateway  dlp  pii  pii-redaction  data-loss-prevention  llm-security
ai-security  privacy  gdpr  hipaa  compliance  proxy  openai  anthropic
self-hosted  presidio  guardrails  observability  llmops
```

**README above the fold must contain:** the one-line description, the architecture diagram, a 30-second quickstart, and a dashboard demo GIF. The GIF drives more stars than any other single asset.

## D.4 Competitive honesty — put this in the README

Baseline PII redaction already exists: Microsoft Presidio (which we build on), LLM Guard, Lakera, Kong AI Gateway, Cloudflare AI Gateway DLP, Bedrock Guardrails. **Do not claim to have invented prompt redaction.**

Frostglass's actual differentiators, which must not be compromised:

1. **Context-preserving pseudonymization by default**, not `[REDACTED]`.
2. **Non-engineer policy control** — a dashboard, not a YAML file only an SRE can edit.
3. **Shadow mode** — measure before enforcing, removing all adoption risk.
4. **A real decision trace** — every block answers "why", down to the rule that fired.
5. **Secure by design** — the proxy sees every prompt in the company, so the threat model is a feature, not paperwork.

---

# PART E — GIT STRUCTURE AND WORKFLOW

## E.1 Branching model

Trunk-based with milestone branches. No `develop` branch — it adds ceremony without benefit at this size.

```
main ────●────●────●────●────●────●──▶  always releasable, protected
          \      \      \      \
           m0     m1     m2     m3       one branch per milestone
```

- `main` — always releasable, protected, never committed to directly.
- `m{N}-{slug}` — milestone branches, e.g. `m3-masking-engine`.
- `fix/{slug}` — for review-gate findings that come back after a merge.
- Branches are deleted after merge.
- **Squash-merge** milestone PRs so `main` history reads as one commit per milestone.

## E.2 Branch protection on `main`

Configure in M0:
- Require a pull request before merging
- Require all status checks to pass: `lint`, `typecheck`, `test`, `detection-accuracy`, `build-dashboard`, `pip-audit`
- Require the branch to be up to date before merging
- Require conversation resolution
- No force pushes, no deletions
- Signed commits (recommended)

## E.3 Commit convention

```
<type>(<scope>): <subject>

[body]

[footer]
```

Types: `feat` `fix` `docs` `test` `refactor` `perf` `chore` `sec`
Scopes: `gateway` `detection` `masking` `policy` `audit` `admin` `dashboard` `db` `ci` `docs`

```
feat(masking): add constant-offset date shifting

Dates now shift by a per-session constant so intervals between them
survive masking. Independent randomisation silently corrupted any
temporal reasoning in the response.

Refs: M3, AC-M3-04
```

## E.4 Pull request template

Create `.github/pull_request_template.md`:

```markdown
## Milestone
M[N] — [name]

## What this does

## Definition of Done
<!-- Quote each DoD item from Part K and state how it is satisfied -->
- [ ] ...

## Acceptance tests
<!-- List the AC-* IDs covered and where the tests live -->

## Self-check
- [ ] All DoD items met and evidenced above
- [ ] All acceptance test IDs for this milestone exist and pass
- [ ] ruff check + ruff format --check pass
- [ ] mypy passes on strict modules
- [ ] Coverage meets the Part L.3 gate
- [ ] CHANGELOG.md updated
- [ ] STATUS.md updated
- [ ] No secrets, keys, or real personal data committed
- [ ] Assumptions recorded as ADRs

## Review gates run
<!-- Which Part B gates were run, and the verdicts -->

## Known gaps
<!-- Anything deliberately deferred, with the issue number -->
```

## E.5 `.gitignore` essentials

```gitignore
__pycache__/
*.py[cod]
.venv/
venv/
.env
.env.local
*.db
*.sqlite3
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage
node_modules/
.next/
dist/
build/
*.egg-info/
.DS_Store
/data/
/logs/
*.pem
*.key
```

`.env` must be ignored from the very first commit. Verify with `git check-ignore -v .env`.

## E.6 `CODEOWNERS`

```
*                       @your-github-handle
/frostglass/masking/    @your-github-handle
/frostglass/detection/  @your-github-handle
/SECURITY.md            @your-github-handle
/.github/workflows/     @your-github-handle
```

Masking and detection are the correctness-critical modules. They always get an owner review.

## E.7 Full repository tree

```
frostglass/
├── BUILD-BRIEF.md                    # this document
├── STATUS.md                         # agent resume contract (Part A.1)
├── README.md
├── LICENSE                           # Apache-2.0
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── docker-compose.yml
├── Dockerfile
├── Makefile                          # make dev / test / lint / eval-detection
├── pyproject.toml
│
├── .github/
│   ├── CODEOWNERS
│   ├── pull_request_template.md
│   ├── dependabot.yml
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug.yml
│   │   ├── feature.yml
│   │   └── detector_request.yml
│   └── workflows/
│       ├── ci.yml                    # lint, typecheck, test, coverage
│       ├── detection-accuracy.yml    # golden corpus scoring gate
│       ├── codeql.yml
│       ├── pip-audit.yml
│       └── release.yml               # tag → build, SBOM, sign, publish
│
├── frostglass/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app factory, middleware wiring
│   ├── config.py                     # Pydantic Settings: env + YAML
│   ├── errors.py                     # typed error envelope
│   │
│   ├── gateway/
│   │   ├── routes_openai.py          # /v1/chat/completions, /v1/embeddings
│   │   ├── routes_anthropic.py       # /v1/messages
│   │   ├── extract.py                # walk + replace text in payloads
│   │   ├── auth.py                   # virtual keys → principal
│   │   ├── budget.py                 # spend + rate limiting
│   │   ├── pipeline.py               # the 13-step lifecycle (Part F.2)
│   │   └── providers/
│   │       ├── base.py               # Provider protocol
│   │       ├── openai.py
│   │       ├── anthropic.py
│   │       ├── gemini.py
│   │       ├── ollama.py
│   │       └── mock.py               # test double — never calls the network
│   │
│   ├── detection/
│   │   ├── engine.py                 # orchestrate layers, merge spans
│   │   ├── models.py                 # Finding, DetectionContext
│   │   ├── layer_structural.py       # regex + checksums
│   │   ├── layer_secrets.py          # key formats + entropy
│   │   ├── layer_dictionary.py       # Aho-Corasick term matching
│   │   ├── layer_ner.py              # Presidio + spaCy
│   │   └── recognizers/
│   │       ├── __init__.py
│   │       └── custom.py
│   │
│   ├── policy/
│   │   ├── engine.py                 # (entity, confidence, scope) → action
│   │   ├── models.py                 # Rule, RuleSet, Scope, Action
│   │   ├── loader.py                 # YAML + DB-backed, versioned
│   │   └── precedence.py
│   │
│   ├── masking/
│   │   ├── engine.py                 # apply actions to spans
│   │   ├── surrogates.py             # format-preserving generator per type
│   │   ├── consistency.py            # stable surrogate per value per scope
│   │   ├── vault.py                  # encrypted surrogate ↔ original store
│   │   └── restore.py                # response restoration + stream buffer
│   │
│   ├── audit/
│   │   ├── recorder.py
│   │   ├── trace.py                  # DecisionTrace
│   │   └── retention.py              # TTL purge job
│   │
│   ├── suggestions/
│   │   └── engine.py                 # auto-mask suggestions (M7)
│   │
│   ├── admin/
│   │   ├── routes_stats.py
│   │   ├── routes_requests.py
│   │   ├── routes_policies.py
│   │   ├── routes_detectors.py
│   │   ├── routes_dictionaries.py
│   │   ├── routes_suggestions.py
│   │   ├── routes_access.py
│   │   ├── routes_settings.py
│   │   └── rbac.py
│   │
│   ├── db/
│   │   ├── models.py
│   │   ├── session.py
│   │   └── migrations/               # alembic
│   │
│   └── observability/
│       ├── metrics.py                # Prometheus
│       ├── tracing.py                # OpenTelemetry
│       └── logging.py                # structlog
│
├── dashboard/                        # Next.js app
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                  # Overview
│   │   ├── requests/
│   │   ├── blocked/
│   │   ├── policy/
│   │   ├── detectors/
│   │   ├── suggestions/
│   │   ├── access/
│   │   └── settings/
│   ├── components/
│   ├── lib/api.ts
│   ├── styles/tokens.css             # the design tokens in H.6.1
│   ├── package.json
│   └── tailwind.config.ts
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_detection_*.py
│   │   ├── test_surrogates.py
│   │   ├── test_consistency.py
│   │   ├── test_restore_stream.py    # AC-M3-03 — the critical one
│   │   ├── test_policy_precedence.py
│   │   └── test_extract.py
│   ├── integration/
│   │   ├── test_lifecycle.py
│   │   ├── test_streaming.py
│   │   ├── test_shadow_mode.py
│   │   └── test_no_raw_values_in_db.py   # AC-M5-03
│   ├── e2e/
│   │   ├── test_sdk_compat.py
│   │   └── dashboard/                # Playwright
│   ├── load/
│   │   └── locustfile.py
│   └── corpus/                       # golden detection corpus — SYNTHETIC ONLY
│       ├── labelled/
│       ├── adversarial/
│       ├── clean_control/
│       └── score.py
│
├── policies/
│   ├── default.yaml
│   └── examples/
│       ├── healthcare.yaml
│       ├── fintech.yaml
│       └── software.yaml
│
├── deploy/
│   └── helm/
│
└── docs/
    ├── index.md
    ├── quickstart.md
    ├── architecture.md
    ├── policy-reference.md
    ├── masking-modes.md
    ├── detectors.md
    ├── threat-model.md
    ├── deployment.md
    ├── api.md
    └── decisions/                    # ADRs
        └── 0001-example.md
```

---

# PART F — SYSTEM ARCHITECTURE

## F.1 High-level

```
                                   ┌──────────────────────────┐
  employee apps / SDKs / scripts   │       DASHBOARD          │
  (OpenAI + Anthropic SDKs — just  │  Next.js → Admin API     │
   change base_url)                └────────────┬─────────────┘
            │                                   │
            ▼                                   ▼
  ┌───────────────────────────────────────────────────────────┐
  │                      FROSTGLASS                            │
  │                                                            │
  │  ┌──────────┐   ┌───────────┐   ┌────────┐   ┌──────────┐ │
  │  │ Gateway  │──▶│ Detection │──▶│ Policy │──▶│ Masking  │ │
  │  │ auth,    │   │ 4 layers  │   │ engine │   │ engine   │ │
  │  │ routing, │   └───────────┘   └────────┘   └────┬─────┘ │
  │  │ budget   │                                     │       │
  │  └────▲─────┘                                     ▼       │
  │       │                                     ┌──────────┐  │
  │  ┌────┴───────┐                             │  Vault   │  │
  │  │ Restoration│◀────────────────────────────│ Redis    │  │
  │  │ + stream   │                             │ AES-GCM  │  │
  │  │   buffer   │                             │ TTL      │  │
  │  └────┬───────┘   ┌──────────────────┐      └──────────┘  │
  │       │           │  Audit + traces  │──▶ Postgres        │
  │       │           └──────────────────┘                    │
  └───────┼────────────────────────────────────────────────────┘
          ▼
  ┌────────────────────────────────────────────┐
  │ Providers: OpenAI · Anthropic · Gemini ·    │
  │ Azure OpenAI · Ollama / vLLM (local)        │
  └────────────────────────────────────────────┘
```

## F.2 Request lifecycle — implement exactly this order

```
 1. Receive     POST /v1/chat/completions   (OpenAI-compatible)
                POST /v1/messages           (Anthropic-compatible)
 2. AuthN/Z     Resolve virtual key → user, team, allowed models, budget
 3. Budget      Reject early if over spend (402) or rate (429)
 4. Extract     Pull EVERY text field: system prompt, all messages
                (including multi-part content arrays), tool definitions,
                tool call arguments, tool results
 5. Detect      Run layers 1→4, merge overlapping spans, assign confidence
 6. Decide      Policy engine: each finding → allow | pseudonymize | tag |
                hash | block. Build the DecisionTrace
 7. Shadow?     If the team is in shadow mode: log the decision AND the
                counterfactual, forward the ORIGINAL payload unmodified,
                skip steps 8–9
 8. Block?      If any action == block → 403 with a structured reason.
                NEVER echo the sensitive value back in the error
 9. Mask        Replace spans with surrogates; write surrogate→original to
                the vault, keyed by consistency scope
10. Forward     Send to provider; preserve streaming if requested; apply
                fallback chain on 5xx/timeout
11. Restore     Swap surrogates back to originals in the response, including
                across SSE chunk boundaries (H.3.5)
12. Audit       Persist metadata + decision trace. Raw content ONLY if
                content capture is explicitly enabled — and then masked only
13. Return      Response + X-Frostglass-* headers
```

## F.3 Failure modes

Configurable via `FG_FAILURE_MODE`, **default `fail_closed`**:

| Failure | fail_closed (default) | fail_open |
|---|---|---|
| Detection engine throws | 503, request rejected | forward unmodified, log CRITICAL |
| Vault unreachable | 503, request rejected | forward unmodified, log CRITICAL |
| DB unreachable | serve traffic, buffer audit to disk, alert | same |
| Provider timeout | try fallback chain, then 504 | same |

Regulated deployments run fail-closed. The default must never be the one that silently leaks.

---

# PART G — PRESCRIBED TECH STACK

Do not substitute without an approved issue.

**Backend**
- Python 3.11+, **FastAPI**, uvicorn
- **httpx** (async) with connection pooling
- **Pydantic v2** for all schemas
- **Microsoft Presidio** (`presidio-analyzer`, `presidio-anonymizer`) as the detection base
- **spaCy** `en_core_web_lg` for NER — swappable via config
- **Faker** for surrogates, seeded deterministically
- **pyahocorasick** for dictionary matching
- **phonenumbers** for phone validation
- **cryptography** for AES-GCM vault encryption
- **SQLAlchemy 2.x** + **Alembic**
- **Postgres** in production, **SQLite** for dev — code must work on both
- **Redis** for vault, rate limits, cache; in-memory fallback for dev

**Dashboard**
- **Next.js 14+ (App Router)**, TypeScript, **Tailwind CSS**, **shadcn/ui**
- **Recharts** for charts, **TanStack Table** for the request explorer
- Server components for reads; the dashboard talks only to the Admin API, never to the DB

**Ops**
- **OpenTelemetry** traces, **Prometheus** metrics at `/metrics`
- **structlog** JSON logging
- **Docker** + **docker-compose**; **Helm** chart in M8

**Quality**
- `pytest` + `pytest-asyncio`, `ruff`, `mypy`, `pre-commit`
- GitHub Actions CI

---

# PART H — COMPONENT SPECIFICATIONS

## H.1 Gateway

**Responsibility:** be a drop-in replacement for the provider's API so existing code changes one line.

**Requirements**
- OpenAI-compatible `POST /v1/chat/completions` and `/v1/embeddings`; Anthropic-compatible `POST /v1/messages`. Request/response shapes and error envelopes must match upstream exactly.
- **Streaming (SSE) is mandatory.** Most real usage streams. If streaming breaks, the product is unusable.
- **Virtual keys**: clients authenticate with a Frostglass key (`fg-live-...`), never the vendor key. Vendor keys live only in server config. A leaked client key cannot bill the vendor account and is revocable instantly.
- Each key resolves to `{user, team, allowed_models, monthly_budget, rate_limit, shadow_mode}`.
- **Multi-provider routing + fallback**: model alias → provider chain; on 5xx/timeout, fail over and record `fallback_used`.
- **Budget and rate limits** per key and per team. Over budget → `402`; over rate → `429` with `Retry-After`.
- **Response headers on every call:** `X-Frostglass-Request-Id`, `X-Frostglass-Action` (`allowed|masked|blocked|shadow`), `X-Frostglass-Entities`, `X-Frostglass-Policy-Version`.

**Critical — `extract.py`:** sensitive data hides in more than `messages[].content`. You must walk *and be able to replace text in*: the system prompt, every message including multi-part content arrays, **tool/function definitions**, **tool call arguments**, and **tool results**. Missing tool payloads is the single most likely real-world leak. Write an explicit test for each location.

**DoD:** unmodified OpenAI and Anthropic SDKs, pointed at Frostglass with only `base_url` changed, complete streaming and non-streaming calls including tool use.

---

## H.2 Detection engine

**Responsibility:** find sensitive spans with a confidence score, fast.

Four layers, run in order, results merged.

**Layer 1 — Structural (highest precision, always on)**
Regex plus validation. Never rely on regex alone where a checksum exists.
- Credit cards (**Luhn**), IBAN (mod-97), SSN, national IDs, phone numbers (`phonenumbers`), email, IP/MAC, postal codes, dates, monetary amounts.
- Confidence `0.95` when a checksum passes, `0.6` on pattern alone.

**Layer 2 — Secrets**
- Known formats: AWS (`AKIA...`), GitHub (`ghp_`, `github_pat_`), Slack, Stripe, OpenAI/Anthropic keys, JWTs, `-----BEGIN * PRIVATE KEY-----`, connection strings with embedded passwords.
- Plus Shannon-entropy heuristics on long alphanumeric tokens, with an allowlist suppressing hashes and UUIDs that aren't secrets.
- **Secrets default to `block`, not mask.** A leaked credential is categorically worse than a leaked name.

**Layer 3 — Dictionary (company-specific, uploaded via dashboard)**
- Customer names, project codenames, employee directory, internal hostnames, unreleased products.
- **Aho-Corasick** for O(n) multi-pattern matching. Do not loop regexes over a large term list.
- Case-insensitive, optional word-boundary and fuzzy (edit distance ≤ 1) matching, configurable per list.
- **This layer holds most of the actual company value.** Make CSV upload trivially easy.

**Layer 4 — NER (statistical, lowest precision)**
- Presidio + spaCy for `PERSON`, `LOCATION`, `ORGANIZATION`, `NRP`, `MEDICAL`.
- Configurable confidence floor, default `0.6`. Expect false positives — the policy engine, not the detector, decides what to do about them.

**Span merging:** highest confidence wins; tie → more specific entity type; tie → longer span. Never emit overlapping spans; the masking engine assumes disjoint, sorted spans.

**Interface**
```python
@dataclass(frozen=True)
class Finding:
    entity_type: str  # "EMAIL_ADDRESS", "CREDIT_CARD", "CUSTOMER_NAME"
    start: int
    end: int
    confidence: float  # 0.0–1.0
    detector: str  # "structural.luhn", "dictionary.customers"
    value_hash: str  # sha256(value + tenant_salt) — NEVER the raw value
```

**`Finding` must never carry the raw matched value.** Only offsets (to act on it) and a salted hash (to correlate without storing). This one constraint is what stops the audit log becoming the leak.

---

## H.3 Masking engine — the core of the product

Read this section twice. It decides whether anyone keeps using Frostglass.

### H.3.1 The problem

Naive redaction destroys the prompt:

> `Draft an apology to [REDACTED] about the [REDACTED] delay on order [REDACTED].`

The model cannot write a good reply. Users disable the tool.

Frostglass produces:

> `Draft an apology to Marcus Feld about the Q3 delay on order 4471-2290.`

Same shape, same readability, same reasoning surface — different values. The response comes back and real values are swapped in before the user sees it.

### H.3.2 Masking modes

| Mode | Behaviour | Reversible | Use for |
|---|---|---|---|
| `allow` | pass through untouched | n/a | non-sensitive types |
| `pseudonymize` | **default** — realistic, type-consistent surrogate | ✅ | names, emails, phones, addresses, orgs, accounts |
| `tag` | `<PERSON_1>`, `<CARD_2>` | ✅ | when even a fake value is unwanted |
| `hash` | deterministic salted token | ❌ | analytics correlation, no restoration needed |
| `block` | reject the whole request | n/a | secrets, credentials, regulated data classes |

### H.3.3 Surrogate generation — format preservation

Surrogates must be **type-valid, same-shape, and obviously not the original**. One generator per type in `surrogates.py`:

| Entity | Rule |
|---|---|
| `PERSON` | Faker name; preserve token count (first vs. first+last) and capitalisation style |
| `EMAIL_ADDRESS` | `first.last@example-corp.com`; preserve local-part shape (dotted vs. single token) |
| `PHONE_NUMBER` | same country code and format mask; use officially reserved test ranges (e.g. `555-01xx` US) |
| `CREDIT_CARD` | same issuer prefix and length, **passes Luhn**, from documented test-card ranges |
| `DATE` / `DATE_TIME` | **shift by a constant per-session offset — never randomise independently** |
| `MONEY` / `NUMBER` | preserve magnitude bucket and precision (`$1,240.50` → `$1,180.25`, never → `$3`) |
| `LOCATION` | same granularity (city→city, country→country) |
| `ORGANIZATION` | plausible company name, same legal suffix (`Ltd`, `Inc`) |
| `ACCOUNT` / `ID` | same length and charset class |
| Dictionary terms | operator-supplied replacement if given, else a stable generated token |

**The date rule is not optional.** Independently randomised dates silently corrupt every "how long between X and Y" answer, and the user will never know it happened.

**Recursion guard:** a generated surrogate must not itself trigger a detector into a re-masking loop. Mark surrogate spans as immune within the same request.

### H.3.4 Consistency and the vault

**Consistency scope** (configurable, default `session`):

- `request` — same value → same surrogate within one call. Safest.
- `session` — stable across a conversation. **Default.** Required for multi-turn coherence; without it "Marcus" becomes "David" on turn two and the model gets confused.
- `tenant` — stable across the whole org. Best coherence, **highest re-identification risk** — a stable mapping is a de-anonymisation oracle. Document loudly; never the default.

**Vault requirements**
- Key `(scope_id, value_hash)` → surrogate, plus the reverse map for restoration.
- **AES-GCM encrypted at rest**, key from env/secret manager, never in the DB.
- **TTL**, default 1 hour for `request`/`session`, configurable; purge on expiry.
- Redis in production, in-memory for dev.
- The vault, not the audit log, is the crown jewels. Treat it accordingly in Part M.

### H.3.5 Restoration — including streaming

Non-streaming is easy: replace surrogates with originals from the reverse map.

**Streaming is the hard part.** A surrogate like `Marcus Feld` can be split across SSE chunks (`"Mar"`, `"cus Fe"`, `"ld"`). Naive per-chunk replacement misses it and leaks the surrogate to the user, or half-restores.

**Required algorithm:**
1. Maintain a rolling tail buffer of length `L = max(len(s) for s in reverse_map)`.
2. On each chunk: append to buffer, run replacement across the buffer.
3. Emit only `buffer[:-L]` — the portion that cannot be the prefix of a pending surrogate. Hold back the final `L` characters.
4. On stream end, flush the remainder through replacement and emit.
5. Cap `L` to keep first-token latency within budget; if a surrogate would exceed the cap, shorten it at generation time.

**Test requirement (AC-M3-03):** split a known surrogate across three chunk boundaries **at every possible offset** and assert correct output each time.

---

## H.4 Policy engine

**Responsibility:** decide, per finding, what to do — and be able to explain it afterwards.

```yaml
version: 3
default_action: pseudonymize
shadow_mode: false

rules:
  - id: block-secrets
    entity_types: [AWS_KEY, GITHUB_TOKEN, PRIVATE_KEY, JWT, PASSWORD]
    action: block
    min_confidence: 0.7
    reason: "Credentials must never leave the network."

  - id: mask-customers
    entity_types: [CUSTOMER_NAME, PERSON]
    action: pseudonymize
    min_confidence: 0.6
    consistency: session

  - id: allow-internal-locations
    entity_types: [LOCATION]
    action: allow
    scope: { teams: [engineering] }
```

**Precedence — define once, document, never deviate:**
1. `block` always wins over any other matching rule.
2. More specific scope beats less specific: `user` > `team` > `model` > global.
3. Among equal specificity, the **more restrictive** action wins: `block` > `tag` > `hash` > `pseudonymize` > `allow`.
4. No match → `default_action`.

**Policy is versioned and immutable-on-write.** Every audit row records the `policy_version` that produced it, so "why was this blocked in March" stays answerable after the policy changed in April.

**Shadow mode** — per team. Detect, decide, log the decision *and the counterfactual*, then forward the **original, unmodified** payload. This is the adoption feature. **New teams default to shadow mode.**

**Dry-run endpoint** `POST /admin/policy/test` — accepts arbitrary text, returns findings, per-finding decision, the rule that fired, and the resulting masked text, with no provider call. The dashboard sandbox uses this.

---

## H.5 Audit and decision trace

**Default privacy posture: never store raw prompt content.** Store metadata, entity types, counts, offsets, salted hashes, and the decision trace. A DLP product whose own database is a plaintext archive of every company secret is a liability, not a control.

**Optional content capture** — off by default, per-team, requires an explicit admin toggle plus a confirmation dialog explaining the risk. Stores the **masked** payload only, encrypted, short TTL, RBAC-gated. **Never store the unmasked original. Ever.**

```python
@dataclass
class DecisionTraceEntry:
    entity_type: str
    detector: str  # which layer/recognizer fired
    confidence: float
    span: tuple[int, int]
    matched_rule_id: str | None
    action: Literal["allow", "pseudonymize", "tag", "hash", "block"]
    was_shadow: bool
    reason: str  # human-readable, shown in the dashboard
```

**Retention** — default 90 days for audit rows, 7 days for captured content. Nightly purge job. Surface retention settings in the dashboard; compliance teams will ask.

---

## H.6 Dashboard

Next.js app in `dashboard/`, talking only to the Admin API. This is the surface the buyer looks at, so it must feel finished.

### H.6.1 Design direction

**Subject and audience.** This is an *inspection instrument* for a security operations team — closer to a lab readout or a customs desk than to a SaaS marketing page. The characteristic thing in this product's world is the continuous stream of prompts crossing a boundary, and what happened to each one. Design for that, not for a generic admin template.

**The governing rule: colour means policy outcome and nothing else.** No decorative colour, no gradient washes, no accent colour on headings or links-as-ornament. Because red appears in exactly one circumstance, an operator can spot a blocked request across the room. This single constraint does more for usability than any chart.

**Colour tokens** (`styles/tokens.css`), dark by default with a light variant:

```css
--fg-canvas:      #0F1419;   /* cold slate, the base surface     */
--fg-raised:      #171D24;   /* panels, drawers, table headers   */
--fg-hairline:    #232B34;   /* borders and dividers             */
--fg-text:        #E4E9EE;   /* primary text                     */
--fg-muted:       #8A97A5;   /* secondary text, labels           */

/* signal — the ONLY colours in the interface */
--fg-blocked:     #E5484D;
--fg-masked:      #E8A33D;
--fg-shadow:      #4C8DF6;   /* observing, not enforcing         */
/* "allowed" has no colour — it is --fg-muted */
```

**Typography.** IBM Plex Sans for all interface text (open licensed, designed for technical products, has character without being decorative). IBM Plex Mono **only for machine values** — request IDs, hashes, span offsets, keys, code. Never mono for labels or headings; that is template chrome. Type scale 12/14/16/20/28. Sentence case everywhere — no tracked-out all-caps eyebrow labels.

**Layout.** Persistent left rail navigation; dense full-width data tables; detail opens in a right-hand drawer so the operator never loses their place in the list. Resist chopping content into identical rounded cards — cards are for genuine peers only.

**The Overview hero.** Not a big number with a gradient. Lead with a **live outcome ledger**: the last 200 requests as a dense horizontal strip of ticks, each coloured by outcome. It shows, in one glance, that traffic is flowing and what is happening to it — the most characteristic thing in this product's world. Numbers sit beneath it.

**Motion.** Only in response to user action — drawer open, row expand, save confirm. No entrance animations on page load.

**Quality floor, unannounced:** responsive to tablet width, visible keyboard focus, contrast-checked signal colours, `prefers-reduced-motion` respected, screen-reader labels on icon-only controls.

**Copy.** Plain language from the user's perspective. Buttons say what happens ("Save policy", not "Submit") and keep the same name through the flow. Errors say what went wrong and how to fix it — never vague, never apologising. Empty states invite an action rather than announcing "No data".

### H.6.2 Pages

**Page 1 — Overview**
Live outcome ledger (above). Requests today / 7d / 30d with sparkline. Percentage containing sensitive data. Counts blocked / masked / shadow. Top 10 entity types. Top teams and users by volume and flag rate. Spend by provider and model. A persistent banner while any team is in shadow mode: *"3 teams are in shadow mode — detections are logged but nothing is masked."*

**Page 2 — Requests explorer ("who is sending what")**
Virtualised table: timestamp, user, team, model, provider, action, entity-type chips, tokens, cost, latency. Filters on every column plus free-text and date range. Row click → detail drawer with the full **decision trace**: each finding, the detector that caught it, confidence, the rule that fired, the resulting action. Shows masked text if capture is on; otherwise a clear "content not captured (by policy)" state. CSV export, RBAC-respecting.

**Page 3 — Blocked and flagged ("what was stopped and why")**
Feed of blocked requests, newest first. Each entry leads with the reason in plain language: *"Blocked: AWS access key detected in message 2 (rule `block-secrets`, confidence 0.98)."* **Never display the offending secret** — type, position, and hash only. Per-entry actions: mark false positive, add exception rule, notify user. A false-positive rate widget — that number is how an operator knows whether to loosen policy.

**Page 4 — Policy editor (the mask/allow control)**
Must be usable by a compliance officer with no YAML.
- **Matrix view**: rows are entity types grouped as Identity / Financial / Health / Credentials / Company terms; columns are the five actions as radio buttons. One click changes a policy.
- Confidence slider per row with a live estimate: *"at 0.6, this matched 1,240 times in the last 7 days."*
- Scope selector: all teams / specific teams / users / models.
- **Live test sandbox** — paste a prompt, instantly see what is detected, what is masked, and exactly what the model would receive. Backed by `POST /admin/policy/test`. This builds trust faster than any documentation.
- **Diff and confirm before save**, with impact estimate ("this would have blocked 14 requests last week").
- Version history with one-click rollback. "Export as YAML" for GitOps users.

**Page 5 — Detectors and dictionaries (the auto-masker configuration)**
Toggle each built-in recognizer; per-detector confidence floor. **Custom term lists**: create a list, upload CSV or paste, choose matching mode (exact / word-boundary / fuzzy), action, and optional fixed replacement — this is how a company teaches Frostglass its own secrets. **Custom regex recognizers** with a built-in tester so a bad pattern cannot be saved. Per-detector stats: matches, false-positive reports, precision estimate.

**Page 6 — Suggestions (the auto-masker's proactive half)**
- **Unpoliced detections**: *"PERSON was detected 3,400 times last week and is not being masked. Mask it?"* One click creates the rule.
- **Recurring unknown patterns**: *"This 12-character pattern appeared 210 times. Add a recognizer?"*
- **Over-blocking warnings**: rules with high false-positive rates → suggest raising the threshold.
- **Context-loss warnings** — closes the loop on the core requirement: if a high-frequency type is set to `tag` or `block`, warn that it is likely degrading answer quality and recommend `pseudonymize`.
- Every suggestion is a card with evidence, the proposed rule, Apply and Dismiss.

**Page 7 — Access and budgets**
Users, teams, roles (`owner`, `admin`, `auditor`, `viewer`). Virtual key issue / rotate / revoke — show the full key once on creation, prefix only thereafter. Per-team budget, rate limit, allowed models, **shadow-mode toggle**.

**Page 8 — Settings**
Provider configuration and vendor keys (write-only fields; never render a stored key back to the browser). Retention periods. Content-capture toggle with explicit risk confirmation. SSO/OIDC. Vault encryption key status and rotation.

---

## H.7 Admin API

`/admin/*`, separate auth from the gateway (session/OIDC, not virtual keys), RBAC enforced **server-side on every endpoint**.

```
GET    /admin/stats/overview?range=7d
GET    /admin/requests?filters...&cursor=...
GET    /admin/requests/{id}
GET    /admin/requests/{id}/trace
GET    /admin/policies            GET /admin/policies/versions
POST   /admin/policies                     # create new version
POST   /admin/policies/{v}/activate
POST   /admin/policies/test                # dry-run sandbox
GET    /admin/detectors           PATCH /admin/detectors/{id}
GET    /admin/dictionaries        POST /admin/dictionaries   # + CSV upload
GET    /admin/suggestions
POST   /admin/suggestions/{id}/apply | /dismiss
POST   /admin/findings/{id}/false-positive
CRUD   /admin/users  /admin/teams  /admin/keys
GET    /admin/settings            PATCH /admin/settings
```

All list endpoints: cursor pagination, deterministic ordering, filters documented in OpenAPI. Publish the schema at `/admin/docs`.

---

# PART I — DATA MODEL

```
tenants(id, name, salt, created_at)

users(id, tenant_id, email, name, role, sso_subject, created_at, disabled_at)
teams(id, tenant_id, name, shadow_mode, monthly_budget_cents,
      rate_limit_rpm, allowed_models[], content_capture_enabled)
team_members(team_id, user_id)

api_keys(id, tenant_id, team_id, user_id, key_prefix, key_hash,
         name, created_at, last_used_at, revoked_at)

policies(id, tenant_id, version, yaml_source, created_by,
         created_at, activated_at, is_active)

detectors(id, tenant_id, name, kind, enabled, min_confidence, config_json)
dictionaries(id, tenant_id, name, match_mode, action,
             replacement, term_count, updated_at)
dictionary_terms(dictionary_id, term, replacement)

requests(id, tenant_id, team_id, user_id, ts, model, provider,
         action, blocked_reason, policy_version, shadow,
         prompt_tokens, completion_tokens, cost_cents,
         latency_ms, provider_latency_ms, status_code, fallback_used)

findings(id, request_id, entity_type, detector, confidence,
         span_start, span_end, value_hash, action_taken,
         matched_rule_id, false_positive_reported)

captured_content(request_id, masked_payload_encrypted, expires_at)  -- opt-in

suggestions(id, tenant_id, kind, evidence_json, proposed_rule_json,
            status, created_at, resolved_at)

audit_events(id, tenant_id, actor_user_id, action, target,
             before_json, after_json, ts)   -- admin actions, append-only
```

**Indexes — add these in the initial migration, not after the first performance complaint:**
`requests(tenant_id, ts DESC)` · `requests(tenant_id, team_id, ts DESC)` · `requests(tenant_id, action, ts DESC)` · `findings(request_id)` · `findings(entity_type, request_id)` · `dictionary_terms(dictionary_id, term)`

**`audit_events` is append-only.** Policy changes and content-capture toggles must never be editable or deletable through the application.

---

# PART J — CONFIGURATION

`.env.example`:
```bash
FG_DATABASE_URL=postgresql+asyncpg://frostglass:pass@localhost/frostglass
FG_REDIS_URL=redis://localhost:6379/0
FG_VAULT_ENCRYPTION_KEY=            # 32-byte base64 — REQUIRED, no default
FG_SECRET_KEY=                      # session signing
FG_TENANT_SALT=                     # value hashing

FG_OPENAI_API_KEY=
FG_ANTHROPIC_API_KEY=
FG_GEMINI_API_KEY=
FG_OLLAMA_BASE_URL=http://localhost:11434

FG_DEFAULT_POLICY=policies/default.yaml
FG_SHADOW_MODE_DEFAULT=true         # new teams start in shadow
FG_CONTENT_CAPTURE=false
FG_FAILURE_MODE=fail_closed
FG_AUDIT_RETENTION_DAYS=90
FG_CAPTURE_RETENTION_DAYS=7
FG_LOG_LEVEL=INFO
FG_OTEL_ENDPOINT=
```

**The app must refuse to start** if `FG_VAULT_ENCRYPTION_KEY` or `FG_TENANT_SALT` is missing or set to a known default. Fail loudly at boot rather than silently running insecure.

Ship three ready-made policies in `policies/examples/`: `healthcare.yaml` (blocks health identifiers), `fintech.yaml` (blocks account and card data), `software.yaml` (blocks credentials, masks customer names). They double as documentation and adoption on-ramps.

---

# PART K — MILESTONES

Each milestone: one branch, one PR, tests included, `STATUS.md` and `CHANGELOG.md` updated, review gates run before merge.

## M0 — Repository foundation
**Branch:** `m0-foundation`

Tasks: full directory tree (E.7) · `pyproject.toml`, ruff, mypy, pre-commit · Apache-2.0 `LICENSE`, README skeleton, `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY.md` · `STATUS.md` · `.gitignore`, `CODEOWNERS`, PR template, issue templates · GitHub Actions: lint → typecheck → test on 3.11 and 3.12, CodeQL, pip-audit · branch protection on `main` · `Dockerfile` + `docker-compose.yml` (app + postgres + redis) · `Makefile` · FastAPI boots, `GET /health` returns `{"status":"ok","version":...}`.

**DoD:** `docker compose up` → `/health` responds. CI green on a trivial PR. `git check-ignore -v .env` confirms `.env` is ignored.
**Gates:** B.6

## M1 — Pass-through gateway
**Branch:** `m1-gateway`

Tasks: OpenAI + Anthropic routes with response fidelity · **SSE streaming end to end** · `extract.py` covering messages, system, multi-part content, tool definitions, tool calls, tool results · virtual key auth and principal resolution · provider registry + fallback chain · mock provider for tests · budget and rate limiting · Prometheus `/metrics`, OTel traces, structlog · `X-Frostglass-*` headers.

**Acceptance:** `AC-M1-01` unmodified OpenAI SDK works with `base_url` change only · `AC-M1-02` same for Anthropic SDK · `AC-M1-03` streaming completes and matches non-streaming content · `AC-M1-04` tool-call payloads round-trip · `AC-M1-05` over-budget → 402, over-rate → 429 · `AC-M1-06` provider 500 triggers fallback and records it.

**DoD:** all AC pass; **no live vendor calls in CI**.
**Gates:** B.1, B.3, B.5

## M2 — Detection engine
**Branch:** `m2-detection`

Tasks: four layers · span merging · custom Presidio recognizers · Aho-Corasick dictionary matching · golden corpus in `tests/corpus/` · `make eval-detection` scoring harness printing per-entity precision/recall.

**Acceptance:** `AC-M2-01` accuracy targets in L.2 met · `AC-M2-02` deterministic path adds ≤ 25 ms p95 · `AC-M2-03` no `Finding` anywhere carries a raw value · `AC-M2-04` 5,000-term dictionary matches in O(n).

**DoD:** all AC pass; CI prints the accuracy table on every run.
**Gates:** B.1, B.2

## M3 — Masking engine
**Branch:** `m3-masking-engine`

Tasks: five modes · per-type format-preserving surrogates · consistency scopes · encrypted vault with TTL · restoration including the streaming buffer algorithm (H.3.5) · recursion guard.

**Acceptance:** `AC-M3-01` round trip — mask → mock provider → restore produces output identical to unmasked for non-sensitive portions · `AC-M3-02` identity stable across a 5-turn conversation · **`AC-M3-03` stream-split restoration correct at every offset of a multi-token surrogate** · `AC-M3-04` date intervals preserved under shifting · `AC-M3-05` surrogates never re-trigger masking · `AC-M3-06` vault contents unreadable without the key.

**DoD:** all AC pass.
**Gates:** B.1, B.2, B.3

## M4 — Policy engine and shadow mode
**Branch:** `m4-policy`

Tasks: rule model, YAML loader, DB-backed versioned policies · precedence exactly as H.4 · shadow mode per team · `POST /admin/policy/test`.

**Acceptance:** `AC-M4-01` precedence unit tests cover every ordering pair · `AC-M4-02` shadow mode provably forwards the original payload while logging the counterfactual · `AC-M4-03` policy version recorded on every request · `AC-M4-04` dry-run returns findings, decisions, rule IDs, and masked text with no provider call.

**DoD:** all AC pass.
**Gates:** B.1, B.2, B.7

## M5 — Audit and Admin API
**Branch:** `m5-audit-admin`

Tasks: persist requests, findings, decision traces · optional encrypted content capture, off by default · retention purge job · all Admin API endpoints with pagination, RBAC, OpenAPI · append-only `audit_events`.

**Acceptance:** `AC-M5-01` 10k synthetic requests, every list endpoint p95 < 300 ms · `AC-M5-02` RBAC enforced server-side on every endpoint · **`AC-M5-03` with capture disabled, an automated test seeds known corpus values and confirms none appear in any DB column** · `AC-M5-04` retention job purges on schedule · `AC-M5-05` no IDOR — user A cannot fetch user B's request.

**DoD:** all AC pass.
**Gates:** B.1, B.3, B.5

## M6 — Dashboard
**Branch:** `m6-dashboard`

Tasks: pages 1–4 and 7–8 · design tokens from H.6.1 · OIDC or local sessions, RBAC-aware UI · loading/empty/error/permission states everywhere · dark and light modes.

**Acceptance:** `AC-M6-01` a new user with no docs can find who sent the most flagged prompts this week · `AC-M6-02` and can change PERSON from `allow` to `pseudonymize` with a preview before saving · `AC-M6-03` requests table stays responsive at 100k rows · `AC-M6-04` full keyboard navigation of the policy editor · `AC-M6-05` colour appears only for policy outcomes.

**DoD:** all AC pass.
**Gates:** B.1, B.4, B.7

## M7 — Detectors UI, dictionaries, suggestions
**Branch:** `m7-suggestions`

Tasks: pages 5 and 6 · CSV dictionary upload · custom regex builder with tester · suggestions engine covering unpoliced detections, recurring unknown patterns, over-blocking, and **context-loss warnings** · false-positive reporting loop.

**Acceptance:** `AC-M7-01` 5,000-term CSV uploads in < 10 s and masks on the next request · `AC-M7-02` at least three suggestion kinds generate real cards from seeded data · `AC-M7-03` an invalid regex cannot be saved · `AC-M7-04` context-loss warning fires when a high-frequency type is set to `tag` or `block`.

**DoD:** all AC pass.
**Gates:** B.1, B.4, B.7

## M8 — Hardening, docs, 1.0 release
**Branch:** `m8-release`

Tasks: full Part M threat-model review and fixes · dependencies pinned with hashes, SBOM, signed artifacts · load test to Part N targets · all docs written · Helm chart · published image · README with diagram, quickstart, and dashboard GIF · ten `good first issue` items · `v1.0.0` tag.

**Acceptance:** `AC-M8-01` a stranger goes from `git clone` to a working masked request in under 10 minutes using only the README · `AC-M8-02` every Part N target met and measured · `AC-M8-03` every Part M threat has an implemented mitigation · `AC-M8-04` `pip-audit` clean, SBOM generated, release signed.

**DoD:** all AC pass; every Part Q item satisfied.
**Gates:** **all seven**

## M9 — Optional extensions (only after v1.0 is tagged)
Choose by user demand, not enthusiasm.
- **Browser extension** — intercepts prompts typed into web chat UIs that the network proxy cannot see. Highest value, highest maintenance.
- **Semantic cache** — returns cached responses for near-duplicate queries; meaningful savings on repetitive traffic. Tune the similarity threshold conservatively: a false-positive cache hit returns a *wrong answer*, and cache-collision attacks against semantic caches are documented.
- **Prompt-injection detection** as an inbound guardrail.
- **Local-model routing** — send low-sensitivity traffic to Ollama/vLLM instead of a vendor.

---

# PART L — TESTING STRATEGY

## L.1 Layers
- **Unit** — detectors, surrogate generators, policy precedence, stream restoration. Fast, no I/O.
- **Integration** — full lifecycle against the **mock provider**. Never call real vendor APIs in CI.
- **E2E** — docker-compose stack, real SDK clients, Playwright for the dashboard's critical paths.
- **Load** — Locust; 200 rps sustained.

## L.2 The golden corpus

`tests/corpus/` holds labelled synthetic documents with ground-truth spans. **Synthetic or public test data only — never real personal data in this repository.**

Cover: emails, support tickets, code with credentials, invoices, medical-style notes, meeting transcripts, multilingual text, and adversarial cases (obfuscated emails, spaced card numbers, unicode homoglyphs, names inside code identifiers). Include a **clean control set** with no sensitive data, to measure false positives.

**Targets that gate the M2 PR:**

| Metric | Target |
|---|---|
| Recall — structured types (card, SSN, keys, IBAN) | ≥ 0.98 |
| Recall — dictionary terms | ≥ 0.99 |
| Recall — NER types (person, location, org) | ≥ 0.85 |
| Precision — overall | ≥ 0.90 |
| False-positive rate on the clean control set | ≤ 0.02 |

CI prints this table on every run so regressions are visible in the PR diff.

## L.3 CI gates

Every PR must pass: `ruff check` + `ruff format --check` · `mypy` strict on `detection/`, `masking/`, `policy/` · `pytest` with **≥ 80% coverage on `masking/` and `policy/`** (the correctness-critical modules) · the detection accuracy suite · `pip-audit` · dashboard `tsc --noEmit` and `next build`.

---

# PART M — SECURITY AND THREAT MODEL

**Frostglass sees every prompt in the company. It is the highest-value target in the network it is deployed into.** Write `docs/threat-model.md` in M8 covering at minimum:

| Threat | Required mitigation |
|---|---|
| Vault compromise → mass de-anonymisation | AES-GCM at rest, key outside the DB, short TTL, aggressive purge, rotation support |
| Audit DB becomes a plaintext archive of company secrets | Capture off by default; store hashes and offsets only; opt-in capture stores *masked* payloads, encrypted, short TTL |
| Leaked virtual key | Keys hashed at rest, prefix-only display, instant revoke, per-key rate limit and budget |
| Vendor key exfiltration | Vendor keys never leave the server, never returned by any API, write-only in the UI |
| Supply-chain compromise (the March 2026 LLM-proxy incident is the reference case) | Pinned dependencies with hashes, `pip-audit` in CI, SBOM, signed releases, minimal base image, Dependabot |
| Prompt injection causing the response to echo masked values | Restoration substitutes only surrogates present in *our* reverse map; never regex-search the response for sensitive-looking data |
| SSRF via provider base-URL config | Allowlist provider hosts; block private IP ranges unless explicitly permitted for local models |
| Privilege escalation in the dashboard | RBAC server-side on every Admin endpoint; `auditor` reads traces but cannot change policy |
| IDOR on request/finding lookups | Every query scoped by tenant and permission, never by ID alone |
| Timing side-channels on key or hash checks | Constant-time comparison |
| Insider misuse of the dashboard | `audit_events` append-only; policy changes and capture toggles logged with actor identity |
| Detection failure leaking data | `FG_FAILURE_MODE=fail_closed` by default; verify with a fault-injection test |

Ship `SECURITY.md` with a disclosure address and a stated response window. For a security tool, this is table stakes.

---

# PART N — PERFORMANCE TARGETS

Enforced by the M8 load test and gate B.5.

| Metric | Target |
|---|---|
| Added p95 latency — deterministic detection | ≤ 25 ms |
| Added p95 latency — with NER | ≤ 120 ms |
| Added time-to-first-token — streaming | ≤ 100 ms |
| Sustained throughput — single instance | ≥ 200 rps |
| Dashboard list endpoints p95 @ 100k rows | ≤ 300 ms |
| Memory — steady state with `en_core_web_lg` | ≤ 1.5 GB |

If NER exceeds budget, run it asynchronously in shadow and enforce only deterministic detectors inline. Record the tradeoff as an ADR.

---

# PART O — OPEN-SOURCE HOUSEKEEPING

- **License:** Apache-2.0. The patent grant matters for enterprise adoption; MIT does not provide one.
- **CONTRIBUTING.md:** dev setup, running tests, commit conventions, PR expectations, and how to add a detector — make that the documented easy first contribution.
- **CODE_OF_CONDUCT.md:** Contributor Covenant.
- **Issue templates** plus at least ten real `good first issue` items before launch.
- **Docs site:** MkDocs Material or Docusaurus from `docs/`, published to GitHub Pages.
- **Releases:** semantic versioning, generated notes, signed artifacts, images to GHCR.
- **README must contain:** one-line description, architecture diagram, 30-second quickstart, dashboard GIF, feature list, an honest comparison against Presidio / LLM Guard / Kong / Cloudflare, and a clear statement of what Frostglass does *not* do.

---

# PART P — RISKS AND HONEST CAVEATS

Put these in the README. A security tool that oversells itself loses trust the first time it misses something.

1. **Detection is probabilistic and will never be perfect.** NER misses names; regex misses obfuscation. Frostglass reduces risk substantially; it does not eliminate it. Publish the corpus results so users can judge for themselves.
2. **Masking can still change model behaviour.** Pseudonymization preserves far more than redaction, but not everything. Surface this through the context-loss warnings rather than pretending it doesn't happen.
3. **`tenant`-scope consistency is a de-anonymisation risk.** A stable global mapping, leaked alongside outputs, is an oracle. Default to `session`; warn in the UI when someone selects `tenant`.
4. **The proxy is a single point of failure and of compromise.** Document failure behaviour; default to fail-closed.
5. **This is not legal compliance.** Frostglass is a technical control supporting GDPR/HIPAA programmes. It does not make anyone compliant. Never imply otherwise in the README or the UI.
6. **The category is crowded.** Do not compete on having a proxy. Compete on context-preserving masking, non-engineer policy control, and the audit trail.

---

# PART Q — FINAL DEFINITION OF DONE

Frostglass v1.0 is done when **all** of the following hold:

1. `git clone && docker compose up` produces a working gateway and dashboard in under 10 minutes, following only the README.
2. Unmodified OpenAI and Anthropic SDKs work by changing `base_url` alone — streaming, non-streaming, and tool calls.
3. Detection meets every accuracy target in L.2, and CI prints the table on every run.
4. All five masking modes work; restoration is correct across streaming chunk boundaries **at every split offset**; identities stay stable across a multi-turn conversation; date intervals survive masking.
5. A non-engineer can change the mask/allow policy for any entity type from the dashboard, preview the effect in the sandbox before saving, and roll back.
6. The dashboard answers, for any request: who sent it, what was detected, what action was taken, and which rule caused it.
7. Shadow mode lets a team run with full logging and zero payload modification.
8. Custom dictionaries and custom regex recognizers can be added entirely through the UI.
9. The suggestions engine produces real, actionable cards — including context-loss warnings.
10. With content capture disabled, an automated test confirms no raw sensitive value from the corpus exists anywhere in the database.
11. Every threat in Part M has a documented, implemented mitigation, and gate B.3 returns "safe to release publicly: yes".
12. Every Part N target is measured and met.
13. Docs, Helm chart, published image, signed `v1.0.0` release, and ten `good first issue` items exist.
14. CI is green on `main`, coverage gates hold, and `STATUS.md` shows every milestone merged.

---

**Execute M0 → M8 in order. Run the Part B review gates before merging each milestone. Do not begin M9 until v1.0 is tagged.**
