# Learning Evidence Phase 2 Protocol

Status: preregistered engineering and product protocol. Changes after the first participant enrols require a new
protocol version and must not rewrite earlier assignments or outcomes.

## Question and first concept

Can Sarce help a player recognise, retain and transfer **piece-safety / hanging-piece awareness** on unseen positions?

The first habit is: *Before choosing a move, what can my opponent safely take or threaten immediately?* The first
loop deliberately excludes Brilliant moves, opening theory, sacrifices and the nine style traits. No second learning
concept is added before the controlled pilot reaches its day-7 endpoint and the evidence decision is recorded.

## Claims and hypotheses

| Construct | Operational definition | Hypothesis |
| --- | --- | --- |
| Recognition | Correct independent response on unseen, unlabelled immediate items | The Sarce arm improves more from baseline than active control |
| Retention | Correct independent response on unseen items 6–9 days later | Day-7 balanced-accuracy change is at least 5 percentage points better |
| Structural transfer | Correct response on unseen, structurally distinct items at day 28 | Any retained gain is not confined to familiar board geometry |
| Real-game application | Verified avoidable errors divided by verified opportunities | Later post-game opportunities move in the expected direction |

The primary endpoint is the between-arm difference in baseline-to-day-7 change in held-out balanced accuracy. The
day-28 and real-game endpoints are secondary. Engagement, confidence and latency are never substitutes for learning.

## Item contract

The candidate bank contains clear positives, near-misses and no-immediate-danger controls across phases, geometries,
ratings and time controls. `family_key` groups exact and structurally related variants; one family cannot cross an
instruction and assessment partition for the same experiment.

A positive qualifies only when all of these hold:

1. It comes from a completed game or an approved curated pool.
2. The position asks an immediate material-safety question.
3. An opponent capture or forcing line nets at least one pawn after best recapture or causes at least 0.10 expected-
   points loss.
4. The line is sound under the versioned 1.5M-node, MultiPV-4 Stockfish contract.
5. The source move is not an intentional sacrifice with adequate compensation and the position is not already decided.
6. Human review finds the instructional question unambiguous.

Near-misses must name the decisive relation: recapture, hidden defender, pinned attacker, tactical counter or adequate
compensation. Detector thresholds change only with a new detector version. Accepted items preserve Stockfish version,
node budget, principal variation, material result, expected-points result and annotation history.

Before automatic serving, independently review a held-out subset with at least two chess-competent annotators. The
gate is at least 90% reviewed precision. Report raw agreement and Cohen's kappa; κ≥0.80 is the planning target. Recall
may remain low because false teaching labels are costlier than missed opportunities.

## Experience and partitions

The first prompt withholds the concept label: **What can your opponent safely take right now?** The player selects a
piece/square or “No immediate material danger,” then reports confidence from 1–5. Feedback explains the relation,
contrasts a near-miss and continues to an unseen item. The answer, motif name and explanation never appear before the
first response.

| Phase | Fixed count | Rules |
| --- | ---: | --- |
| Baseline | 18 | Balanced unseen positives, near-misses and controls; shown before naming the concept |
| Learning | 4 | Experimental arm uses own-game anchors where available; control receives conventional review |
| Immediate | 9 | Unseen, unlabelled assessment families |
| Day 7 | 18 | Unseen assessment, due days 6–9; primary endpoint |
| Day 28 | 18 | Structurally distinct assessment, due days 26–32; secondary endpoint |
| Real games | 30–50 games or four weeks | Post-game observation only; stratify bullet, blitz and rapid |

Protocol assessments have fixed schedules and never adapt to confidence. Scheduler v2 applies only to instruction:
incorrect, hinted or revealed answers return after one day; correct low-confidence novel answers after three days;
correct independent novel answers after seven days; correct independent delayed answers after 28 days. Confidence
alone can never establish a successful state.

## Participants, assignment and consent

- Qualitative pilot: 8–12 deliberately recruited adults spanning early beginners, developing players, faster/slower
  time controls, existing users and new users.
- Controlled pilot: 60–80 adult completers, approximately 30–40 per arm.
- Entry is invite-only and authenticated. Enrolment records protocol version, explicit consent and confirmation of age
  18 or older. Withdrawal stops new sessions without altering already collected audit records; account deletion follows
  the product privacy policy.
- Randomise once at player level and persist the 1:1 assignment. Item-level randomisation is forbidden because the
  taught habit can contaminate control items.
- Experimental arm: own-game anchor → active retrieval → explanation → contrast → unseen assessment → delayed retrieval.
- Active control: conventional review of the same underlying category, explanation/best line and equivalent study time.

## Analysis

The frozen export includes protocol/scoring/detector versions, assignment, item family and partition, exact presentation,
novelty, hints/reveals, response, correctness, latency and due-window status.

Use a deterministic player-level cluster bootstrap with 10,000 resamples within arm. Report the absolute percentage-
point day-7 effect, its 95% interval, both arm estimates and participant/item denominators. Secondary reports cover
immediate recognition, day-28 transfer, Brier calibration, correct-answer latency, hint dependence, completion and
voluntary return. Publish estimates whether favourable or not; do not describe this feasibility pilot as definitive
efficacy evidence.

Real-game transfer uses `verified avoidable errors / verified opportunities`, stratified by time control. Show no
personal transfer statement below 15 verified pre and 15 verified post opportunities, and no cohort estimate below
100 opportunities per arm.

## Decision gates

- **Go:** detector precision ≥90%; at least 80% of qualitative participants understand the unassisted prompt; day-7
  completion ≥70%; day-7 point estimate ≥+5 percentage points; the 95% interval does not establish meaningful harm.
- **Revise spacing:** immediate effect ≥+5 points but day-7 effect is below +5.
- **Revise representation:** day-7 recognition clears +5 but near-miss/day-28 structural transfer does not.
- **Stop or radically rethink:** with at least 60 completers, the day-7 estimate is non-positive and its 95% upper
  bound is below +5.

No UI or marketing copy may claim improved intuition, mastery or transfer before the corresponding gate is met. The
evidence review ends in an ADR that says go, revise or stop.
