# ADR-0012: Learning Evidence and Progress Semantics

## Status

Accepted

## Context

Sarce can reconstruct games, classify moves, describe style and generate drills. It cannot yet support the stronger
claim that a player learned from those experiences. A style observation, a successful repeated drill and a durable
ability on unseen positions are different facts.

ADR 0001 made Brilliant % the universal headline because Sarce began as a Tal-style identity product. That remains
a legitimate optional style goal, but it cannot represent improvement in an unrelated concept such as piece safety.
A player can learn to notice hanging pieces without producing more sacrifices.

## Decision

1. Sarce recognises two related but distinct domains:
   - **Playing identity** describes how a player tends or intends to play, including Brilliant %, style traits and
     optional reference-player goals.
   - **Learning evidence** describes demonstrated recognition, delayed retention and transfer on versioned items.
2. **Brilliant remains a first-class move tier.** Brilliant % remains prominent for players who choose that style
   goal, but is not a universal progress score.
3. Sarce presents no single number that collapses style, skill, rating and learning.
4. A style observation is not learning evidence. A training response is not transfer evidence unless its assessment
   item was unseen, unlabelled and excluded from instruction.
5. **Recognised** means a correct independent response on an unseen, unlabelled item under a versioned assessment
   contract.
6. **Retained** means recognised performance after a defined delay, initially seven days, on an unseen item.
7. **Transferred** means success on structurally distinct unseen items or, once denominators are adequate, comparable
   later real-game opportunities.
8. Confidence, Maia probabilities, Elo, repetition and style traits may supply context. None alone establishes
   attention, intent, recognition, understanding or learning.
9. Learning attempts are evidence records. Submitted answers are immutable; corrections append a superseding record.
   Learning state is a versioned, rebuildable projection.
10. Learning remains post-game. Personal game-derived items are private by default, and a shared item must be
    explicitly curated as global.
11. Learning claims expose evidence counts and uncertainty. No efficacy claim is made before held-out delayed evidence.

This ADR supersedes ADR 0001 decision 2 only. It narrows the universal-headline language in ADRs 0003 and 0005; their
style-focus and Home-screen decisions otherwise remain accepted.

## Consequences

### Positive

- Sarce can test modest educational claims without weakening its style identity.
- Held-out partitions prevent repeated puzzles from masquerading as transfer.
- Evidence can be recomputed when scoring or scheduling rules change.
- A beginner's progress is not forced into sacrificial-frequency language.

### Negative / trade-offs

- Product surfaces must keep style and learning summaries visually and semantically separate.
- A useful learning loop requires reviewed items, delayed follow-up and more instrumentation than confidence-only
  scheduling.
- Early evidence will often be sparse; the honest UI must sometimes say that no conclusion is available.

## Philosophy alignment

The engine remains a mirror rather than a judge, and Brilliant remains a first-class expression of playing identity.
The change broadens the constitution from recording how a player chooses to play to also recording what the player
has demonstrated they can see.

## Gates affected

- `test_philosophy_contracts.py` guards the two-domain boundary and learning terminology.
- `philosophy-check` keeps Brilliant present while rejecting universal-score and unsupported-learning copy.
- Learning migrations require RLS and explicit personal/global scope.
- Experiment and evidence changes follow [LEARNING_EVIDENCE_PROTOCOL.md](../LEARNING_EVIDENCE_PROTOCOL.md).
