# Redact deployment identifiers

## Goal
Remove real deployment infrastructure identifiers from repository documentation and help examples before submission.

## Requirements
- Replace deployment IP with documentation address 192.0.2.10, instance ID with i-example, and security group ID with sg-example.
- Include existing deployment instructions, archived task notes, and script help text.
- Preserve strategy research and runtime behavior; do not commit or push.

## Acceptance Criteria
- [x] Original identifiers absent from tracked working files and staged contents.
- [x] Script syntax and changed-file whitespace checks pass; full staged check reports two pre-existing trailing blank lines in unrelated research scripts.

## Out of Scope
Strategy research, Git history rewriting, deployment changes.
