# Lessons

`upstream/` is read-only, so lessons that an upstream skill would write back
into its own files land here instead. One entry per lesson: date, the job, what
went wrong, what fixed it, and which skill (`<key>/<name>`) it concerns. Entries
that keep recurring are worth an issue or pull request on the upstream
repository, or a routing change in `registry/capabilities.yaml`.
