# Jevify operator smoke validation

Status: draft

## Question

In one short operator session, does Jevify make Graphify easier to use and surface at least one
useful, source-verifiable connection that direct Graphify does not surface for the same change?

This is an early signal check. It is not a latency benchmark, proof of broad demand, or proof that
JEV improves ranking. Reviewed memory is allowed; live or precomputed JEV decisions are not.

## Protocol

Luis compares `$graphify --update` and `$jevify --update` on two isolated copies of the same
warm repository state and bounded diff. The starting graph, manifest, and diff hashes must match;
a cold bootstrap compared with a warm no-op is invalid. The order is Graphify then Jevify. Each condition receives five
minutes; ratings and source verification receive five minutes. The session ends after 15 minutes.
There is no recruiting, later-use observation, or follow-up window.

## Gates

Graphify is always the structural engine; Jevify may route to it, verify its outputs, and query the
result. A graph-only run cannot prove memory value. It may proceed only to a reviewed-memory smoke.
Proceed to external validation only when reviewed memory is helpful and the prior value gates pass.
Wrong target resolution, wrong attribution, unsupported comparative claims, false freshness/update
claims, paid requests, or unequal starting conditions invalidate the smoke.

## Privacy

Store only `operator-01`, structured ratings, booleans, timestamps, and hashes. Never store an
identity, repository path, prompt, source, graph output, memory, or credential.
