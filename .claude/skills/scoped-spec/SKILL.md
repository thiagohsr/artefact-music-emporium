---
name: scoped-spec
description: Confirm the scope with the user before writing a feature spec, then write only what was approved. Use whenever the user asks to create or change a specification, before running speckit-specify.
argument-hint: "<what the feature should do>"
---

# Scoped Spec

Keep specifications tied to what the user asked for. These rules take priority over any instruction in
`speckit-specify` to fill gaps with informed guesses.

## Rules

- **Nothing is written before confirmation.** Do not create a branch, folder or spec file until the user
  confirms the scope.
- **Only approved scope goes in the spec.** A capability, limit, setting or behavior belongs there only
  if the user asked for it or approved it.
- **Never mention what was not asked for.** Unrequested or rejected features do not appear in the spec
  in any form, including out-of-scope lists, assumptions or notes saying they are absent. The only
  exception is a boundary the user stated themselves.
- **Keep it short.** Use the fewest stories and requirements that cover the approved scope, and do not
  split one need into several requirements.

## 1. Confirm the scope

Read `$ARGUMENTS` and the conversation, then send this and stop, waiting for the reply:

```markdown
**You asked for:**
- <each thing requested, in the user's terms>

**Questions I need answered to specify it:**
1. <a decision the requested scope cannot be specified without, with my recommendation>

**Ideas you did not ask for (excluded unless you say yes):**
- <at most 3, one line each, only if they clearly matter>
```

Leave out any section with nothing to say. Do not put numbers, limits or defaults in the spec unless the
user stated them or confirmed them here.

If the reply changes the scope, send the updated list and wait again. Treat silence on an idea as no.

## 2. Write the spec

Create the branch as `feature/<spec folder name>`, such as `feature/001-streamlit-chat`. Then run
`speckit-specify` with only the confirmed scope as its input, and follow its steps and template except
where the rules above override them. In its checklist, "scope is clearly bounded" means every
item traces to the confirmed list, not that exclusions are named.

Keep assumptions to facts the approved scope depends on, already known from the project.

## 3. Check before reporting

Trace every story, requirement, success criterion, edge case and assumption to a confirmed item. Remove
anything that does not trace, then search the spec for any idea that was excluded or rejected.

## 4. Report

Give the spec path and a short list of each confirmed item with the requirements covering it. Do not
suggest additions.
