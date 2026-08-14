# Omni Web Sprint 6

Sprint 6 adds defensible engagement planning and objective-level assessment
execution to the multi-framework platform.

## Planning and team

- Engagement start/end dates, scope boundaries, locations, and sampling
  methodology are maintained in the Assessment Plan.
- Organization members are assigned as Lead Assessor, Assessor, Quality
  Reviewer, or Subject-Matter Expert.
- Sampling records capture population, population size, sample size, selection
  method, rationale, selected items, and linked assessment objectives. A sample
  cannot exceed its population.

## Objective execution

- The CMMC seed loads 320 assessment objectives and 1,556 potential Examine,
  Interview, and Test procedures from Omni's compiled public source data.
- New and existing control results are hydrated with objective-level result
  records without overwriting assessment work.
- Each objective captures status, conclusion/notes, assessor, assessment time,
  and many linked evidence artifacts.
- Interview sessions capture schedule, location/link, participants, interviewer,
  objectives, notes, and completion.
- Test executions capture the objective, procedure, performer, date/time, steps,
  expected and actual results, outcome, and evidence.
- Control status is derived conservatively: any NOT MET objective makes the
  control NOT MET; any remaining unassessed objective keeps it NOT ASSESSED; all
  MET results produce MET; and an entirely N/A set produces NOT APPLICABLE.
- Execution can be filtered by framework and assessment method, and progress is
  visible by objective status and assessor.

## Quality review and locking

- Quality review supports Not Started, In Review, Approved, and Changes Required
  with reviewer notes.
- Final sign-off requires Approved quality review and completion of every loaded
  assessment objective.
- Sign-off records the assessor and timestamp, marks the assessment Complete,
  and locks planning, frameworks, control results, objective results, evidence,
  remediation, milestones, and owner assignments.
- Only an organization Administrator can reopen a locked assessment. A meaningful
  justification is mandatory and actor, timestamp, and reason are audited.

## Reporting

The web-bound workbook includes an Objective Results sheet with framework,
native requirement/objective IDs, text, result, notes, assessor, timestamp,
evidence, and Examine/Interview/Test objects. Completed report readiness treats
unassessed loaded objectives as blockers.

All engagement plans, participants, samples, interviews, test records, and
objective conclusions are organization runtime data and must never be committed
to the public repository. Tests use synthetic records only.
