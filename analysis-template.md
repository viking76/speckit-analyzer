---
description: "Analysis report template for speckit-analyzer"
---

# Analysis Report: [FEATURE NAME]

**Generated**: [DATE]
**Tasks File**: [PATH]
**Thresholds**: Complexity ≤ [X] | Context ≤ [Y] tokens

## Summary

- **Total Tasks**: [N]
- **Delegable**: [N] ([P]%)
- **Non-Delegable (Complexity)**: [N]
- **Non-Delegable (Context)**: [N]
- **Non-Delegable (Both)**: [N]
- **Critical Path**: [X] days
- **Parallelizable**: [Y] days

## Delegable Tasks

| Task | Complexity | Est. LOC | Context Tokens | Package |
|------|------------|----------|----------------|---------|
| T### | # | #,### | #,### | delegation_package/T###/ |

## Critical Path

[Task IDs in critical path order]

## Parallelization Opportunities

| Phase | Tasks | Days Saved | Risk |
|-------|-------|------------|------|
| # | T###, T### | #.# | low/medium/high |

## Threshold Analysis

See `threshold_analysis.md` for detailed threshold sweep results.

## Next Steps

1. Review delegable tasks for delegation to small LLMs
2. Check `delegation_package/T###/context.md` for minimal context
3. Adjust thresholds if needed: `/speckit.analyze --threshold complexity=X,context=Y`
