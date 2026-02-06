1. Improve DB performance:
    a. Reuse DB connections instead of creating new ones for each request.
    b. Improve indexing on frequently queried fields. Full timestamp is not needed for indexing, so consider indexing only the date part of the timestamp.

2. Coloring timesheet per glucose numbers.
