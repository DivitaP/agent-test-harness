# Harness meta-evaluation

Per-scorer pass rates for the demo suite under each injected failure mode.

| Mode | Test | process | evidence | output | verdict |
|---|---|---|---|---|---|
| none | direct study lookup by ID | 1.00 | 1.00 | 1.00 | PASS |
| none | math question uses calculator | 1.00 | n/a | 1.00 | PASS |
| none | topic search then detail fetch | 1.00 | 1.00 | 1.00 | PASS |
| none | search resilience under flaky upstream | 1.00 | n/a | 1.00 | PASS |
| vague_answers | direct study lookup by ID | 1.00 | 1.00 | 0.00 | FAIL |
| vague_answers | math question uses calculator | 1.00 | n/a | 0.00 | FAIL |
| vague_answers | topic search then detail fetch | 1.00 | 1.00 | 0.00 | FAIL |
| vague_answers | search resilience under flaky upstream | 1.00 | n/a | 0.00 | FAIL |
| answer_directly | direct study lookup by ID | 0.00 | 0.00 | 0.00 | FAIL |
| answer_directly | math question uses calculator | 0.00 | n/a | 0.00 | FAIL |
| answer_directly | topic search then detail fetch | 0.00 | 0.00 | 0.00 | FAIL |
| answer_directly | search resilience under flaky upstream | 0.00 | n/a | 0.00 | FAIL |
| flaky_search | direct study lookup by ID | 1.00 | 1.00 | 1.00 | PASS |
| flaky_search | math question uses calculator | 1.00 | n/a | 1.00 | PASS |
| flaky_search | topic search then detail fetch | 1.00 | 1.00 | 1.00 | PASS |
| flaky_search | search resilience under flaky upstream | 1.00 | n/a | 0.80 | FAIL |

- Injected-failure detection: 10/10 broken stages flagged
- Isolation: 16/16 healthy stages stayed green
- flaky_search reported as observed pass rates (statistical, run-dependent)
- answer_directly output is test-dependent by design: a correct ungrounded answer can pass the math rubric while grounded rubrics fail on fabrication
