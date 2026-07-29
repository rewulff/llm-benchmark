You are support engineering for the Kestrel sync agent. This directory holds the
project's document set: changelog, two configuration references, known issues, an
FAQ, meeting notes, a support playbook, a wiki page and three customer log excerpts.

Answer the four research questions below from these documents only. There is no
network access and no code to run — this is a reading task.

## Questions

**Q1.** Northwind Logistics reports that their nightly archive job fails. Which
Kestrel release introduced the defect they are hitting? Give the version number.

**Q2.** What is the documented workaround for that defect? Give the configuration
key and the value it has to be set to.

**Q3.** One of the three customers in the logs cannot be hit by this defect at all.
Which customer, and which agent version are they running?

**Q4.** Is the defect fixed? Name the release that is meant to carry the permanent
fix and the ticket id it is tracked under.

## What to watch out for

- No single document answers a question on its own. Every answer needs at least
  two documents combined.
- The documents were written at different times and some of them contradict each
  other. Older documents can describe behaviour that no longer exists. Check what
  version and what date a document was written against before you trust it.

## Output format (strict!)

Write your answers to a new file `answers.md` in this directory. Use exactly this
structure, one block per question:

```markdown
## Q1
Answer: <one single line, the fact itself, no hedging and no alternatives>
Sources: <comma separated file names that support this answer>

## Q2
Answer: ...
Sources: ...
```

- `Answer:` must be ONE line and must not offer a second possibility.
- `Sources:` lists only the documents that actually support the answer. Do not
  list a document you concluded is outdated.
- Do not modify any of the existing documents. Only create `answers.md`.

## Done

After writing `answers.md`, respond with just: DONE
Do not ask follow-up questions.
