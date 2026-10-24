# Ignore local strategy documents

## Goal

Keep all files under `docs/strategy/` locally while preventing Git from tracking new or currently staged strategy research documents.

## Requirements

- Add one repository ignore rule for `docs/strategy/`.
- Remove existing staged strategy documents from Git's index without deleting them from disk.

## Acceptance Criteria

- [x] `git check-ignore` reports strategy documents ignored.
- [x] `git status -- docs/strategy` is empty.
- [x] Existing files still exist locally.

## Out of Scope

- No changes to other user edits or tracked documentation.
