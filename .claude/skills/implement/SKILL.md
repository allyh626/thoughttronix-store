---
name: implement
description: Implement one approved phase from a PRD and plan using feedback loops.
argument-hint: "@prd/<feature>.md @plans/<feature>.md implement phase <N>"
disable-model-invocation: true
---

# Implement

## 1. Understand the Phase

Read the referenced PRD and plan. Explore the codebase to understand the relevant files,
patterns, and conventions. If the request does not identify a phase, ask which one.

Implement only that phase. Do not begin the next one.

## 2. Implement the Phase

For implementation use the tdd skill and follow its instructions, then complete the remainder of the phase through the projects normal process.

## 3. Run Feedback Loops

After implementation, run the automated tests, the linter and formatter, code review, manual testing, and other feedback loops to identify issues within the functionality of the codebase.

## 4. Manual Verification

Explain step by step how this phase or feature can be manually verified in the browser.

## 5. Finish the Phase

Append PROMPTS.md with the session log, commit the completed phase, then push said commit to GitHub.