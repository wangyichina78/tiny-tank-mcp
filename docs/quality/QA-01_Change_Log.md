# QA-01 Change Log

**Question it answers:** what changed, when, why, and in which version?

The change log is the human-readable history of a product, written for the people who use, review or support it, not for the developers who built it. Commit history records every keystroke. The change log records what matters to readers. A reviewer should be able to read it and know what's different between two versions without reading code.

## 1. Where it lives

One file, `CHANGELOG.md`, in the project root, newest entry at the top. It's committed with the change it describes, in the same pull request, so code and log can't drift apart.

## 2. Versioning

Give every release a version, and use the same version in the change log, the artifact name, the evidence files and the findings register.

- **Semantic versioning** (`MAJOR.MINOR.PATCH`, such as `1.4.2`) for anything others depend on:
  - **MAJOR** for breaking changes to an interface;
  - **MINOR** for new capabilities that are backward compatible;
  - **PATCH** for fixes.
- **Date plus commit** (`2026-10-23_9af84d6`) is enough for internal tools and reference packages.

## 3. What every entry contains

```markdown
## [1.3.0] — 2026-10-19

### Added
- Three read-only tools: `list_tanks`, `get_inspection_history`, `get_tank_readings`.

### Changed
- Tool definition pin now covers all four tools. Re-pin approved by <name> (QA-02).

### Fixed
- Validation errors no longer repeat the caller's input to the agent (finding F3, tests SEC-02 wrong-type cases).

### Security
- See Fixed above. Confirmed on the live deployment before the fix.

### Removed
- (none)

Verification: regression 79/79 · security black-box 21/21 · release check <report file>
Approved by: <name> · Change: <ticket or PR link>
```

Use these headings, and include only those that apply:

| Heading | Use for |
|---|---|
| Added | New capabilities |
| Changed | Changes to existing behaviour, including interface and contract changes |
| Deprecated | Things that still work but will be removed, with a date |
| Removed | Things taken out |
| Fixed | Defect fixes. Always name the finding ID (QA-04) |
| Security | Anything security-relevant, even if also listed under Fixed |

## 4. Writing an entry, step by step

1. **Write it while making the change,** not at release time. Add it under an `## [Unreleased]` heading at the top.
2. **Describe the effect on the reader,** not the code: "Validation errors no longer repeat the caller's input", not "Override call_tool in TinyTankServer."
3. **Link the evidence:** finding IDs, test IDs, report files.
4. **Record decisions that changed the plan,** such as a test deleted, a check skipped, or a risk accepted, with the reason and who decided.
5. **At release,** rename `[Unreleased]` to the version and date, and add the verification line and approver.

## 5. Rules

**R1. No release without a change log entry.** The release checklist (QA-02) checks for it.

**R2. Never rewrite history.** If an entry was wrong, add a correction in a later entry. *Example:* "Correction: the smoke test runs 18 checks, not 17 as stated for 1.3.0."

**R3. Rollbacks are entries too:** `## [1.3.1] — rolled back to 1.3.0 on <date>: <reason, finding ID>`.

**R4. No secrets, personal data or internal-only names** in the log, if the log travels with the product.

## 6. Change log versus the other records

| Record | Audience | Content |
|---|---|---|
| Commit messages | Developers | Every change, with technical detail |
| `CHANGELOG.md` | Users, reviewers, support | What changed per version, in plain words |
| Findings register (QA-04) | Owner, security | Every defect and risk, and its lifecycle |
| Evidence files (QA-03) | Auditors, approvers | Proof that the tests were run, and their results |
