We have 5 microservices that need to communicate. The following constraints are non-negotiable:

1. Services can be deployed in different geographic regions — network latency is variable
   and unpredictable (50ms–500ms between regions).
2. Message order must be preserved per-user (two messages from the same user must arrive
   in the order they were sent).
3. Occasional service downtime (up to 15 minutes) must not cause message loss.
4. Infrastructure budget: under $200/month total.
5. Peak throughput: approximately 10,000 messages per hour.

Design a messaging architecture for this system.
Write your proposal to `design.md`.

Your proposal must include:
1. The chosen messaging pattern with your reasoning (why this pattern, why not the alternatives)
2. A sequence diagram showing a happy-path message flow, drawn as ASCII art
3. A failure-mode analysis: for each of the 5 constraints above, describe what happens
   when it is violated and how your architecture handles it

When the file is saved, respond with just: DONE
