# Jevify operator smoke validation

Status: draft

## Question

In one short operator session, does Jevify make Graphify easier to use and surface at least one
useful, source-verifiable connection that direct Graphify does not surface for the same change?

This is an early signal check. It is not a latency benchmark, proof of broad demand, or proof that
JEV improves ranking.

## Protocol

Luis compares `$graphify --update` and `$jevify --update` on two isolated copies of the same
repository state and bounded diff. The order is Graphify then Jevify. Each condition receives five
minutes; ratings and source verification receive five minutes. The session ends after 15 minutes.
There is no recruiting, later-use observation, or follow-up window.

## Gates

Proceed to external validation only when Jevify is preferred, scores at least `4/5`, scores higher
than Graphify, surfaces a Jevify-only useful connection verified in source, makes no false freshness
or update claim, and makes no paid request. Otherwise select `revise_or_extension` for a safe
completed smoke or `invalid_smoke` for incomplete or unsafe evidence.

## Privacy

Store only `operator-01`, structured ratings, booleans, timestamps, and hashes. Never store an
identity, repository path, prompt, source, graph output, memory, or credential.
