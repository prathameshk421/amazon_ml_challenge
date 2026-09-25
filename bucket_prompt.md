# Agent Prompt — Maximize Bucketing Recall (Blocking Strategy Deep-Dive)

Scope: blocking/candidate-generation only. Do not build or tune a matcher tonight — this feeds one. Goal is explicitly recall-maximizing: over-retrieval is acceptable and expected (if the true answer is 5 matches, retrieving 10 candidates is a win, not a problem — the downstream ML model narrows it back down). Under-retrieval (missing the true match entirely) is the only real failure mode here, since nothing downstream can recover a match blocking never found.

Load all existing artifacts first (`artifacts/metrics/blocking*.json`, `artifacts/metrics/eda_*.json`, `artifacts/candidates/*.parquet`) and treat every number in them as ground truth to build on, not to re-derive. Cite the specific artifact/number when you use it.

---

## LOCKED, DO NOT RE-LITIGATE

- Ranked idf-weighted union (exact + name-token df≤20K + trigram df≤8000 + addr-token + metaphone×0.2), top-K truncation, is the correct architecture. Naive per-signal top-N union was already tested and rejected (6300+ candidates/query — infeasible). Do not propose going back to separate top-N buckets per signal.
- BK-tree and pure edit-distance-automaton blocking are already tested and rejected at this pool scale (10.3M records) — per-query cost scales with pool size, doesn't serve the required query volume in time. Trigram+token index already covers the same recall function more scalably (component attribution 0.44 from trigram alone, higher in combination). Do not re-attempt automaton-based blocking as a primary method — you may mention it only if you find a specific narrow case it uniquely helps that nothing else covers, with a number to prove it.
- Attribution of currently recovered true pairs by source (top-500 config): address-token 0.95, name-token 0.76, phonetic 0.68, trigram 0.44, exact 0.30. Phonetic has 0 EXCLUSIVE recoveries (pairs found only via phonetic, no other signal voting) — it's currently kept because it's harmless to ranking, not because it's pulling unique weight.
- K=150 gives pair recall 0.922 / entity recall 0.987. K=250 gives 0.935/0.991. K=500 gives 0.947/0.994.

---

## PHASE 1 — Push K higher, with an actual compute-recall curve (budget: 45 min - 1 hr)

- Given the explicit instruction to bias toward over-inclusion, K=150 is probably too conservative. Re-run the ranked-union blocking at K=250, K=500, K=1000 (and beyond if compute allows) on the same 10,000-query eval set used last time, for direct comparability.
- Report pair recall, entity recall, avg candidates/query, and wall-clock/compute cost at each K, as a table plus a simple recall-vs-K curve (even ASCII/text description is fine if no charting available).
- Identify the point of diminishing returns (where an additional 2x candidates buys <0.5pp recall) — but do NOT necessarily recommend stopping there; given the explicit "10 is fine if 5 is correct" instruction, argue for the highest K that stays within a defensible downstream compute budget, and state that budget assumption explicitly (e.g. "assuming the matcher can score up to N million pairs tonight/tomorrow, K=X is affordable").
- Recommend a new default K, with the recall/compute tradeoff numbers to justify it, replacing K=150.

**Output**: `bucketing_k_sweep_report.md`.

---

## PHASE 2 — Adaptive K for chain-heavy entities (budget: 45 min - 1 hr)

This addresses a specific, named risk from earlier EDA that was flagged but never measured: entities whose normalized name recurs across many S1 entities (chain clusters — e.g. 'primary care group' ×253) may get their true match crowded out of a fixed top-K by same-name competitors, even though the ranking score for the true match is still reasonably high.

- Pull the chain-cluster list (normalized S1 names occurring in ≥2 S1 entities — 180,422 such names covering 881,492 entities per last night's numbers). Take a representative sample across cluster sizes (some small 2-3 member clusters, some large 10+, and the extreme cases like the x253/x251 examples).
- For each sampled entity, check: at what rank (not just in/out of top-150) does its true match actually land in the FULL ranked candidate list (before truncation)? Report the rank distribution for chain-cluster entities vs non-chain entities, side by side.
- If chain-cluster entities show a measurably worse rank distribution (true match sitting further down the ranked list on average) than non-chain entities, quantify it and propose an adaptive rule: e.g. "entities whose normalized name appears in ≥N other S1 entities get K_expanded instead of the global K" — pick N and K_expanded based on what the rank-distribution data actually shows, not a round-number guess.
- Report the recall improvement and candidate-count cost of the adaptive rule specifically for chain entities, and the cost impact on the overall pipeline (chain entities are ~40% of S1 by earlier EDA, so this isn't a tiny edge case — quantify the real overall compute delta).

**Output**: `chain_adaptive_k_report.md` — rank-distribution comparison, proposed adaptive rule with numbers, overall cost impact.

---

## PHASE 3 — Untested candidate bucket keys: postal-code and domain-derived (budget: 45 min - 1 hr)

Two signals exist in the feature set (a_postal) or noise catalog (domain-name pattern, 1,757 positives in the noise catalog) but have NOT been tested as blocking/bucketing keys the way exact-name, token, trigram, address-token, and phonetic were. Test them the same way phonetic was tested — specifically for EXCLUSIVE retrieval contribution (pairs found ONLY via this key, that nothing else in the current union would have found), not just standalone recall.

- **Postal-code exact-match bucket**: build an index keyed on extracted postal code (where present — note the missingness rate from earlier EDA, ~3.3% of pool records lack addresses entirely, and check what fraction of the rest have a parseable postal code). Run the same exclusivity test used for phonetic: of all true pairs recovered by the CURRENT ranked-union config, how many were found ONLY via postal-code match (no other signal voting for that pair)? Report the number, same format as the phonetic result (which was 0/34,745).
- **Domain-name-derived bucket**: extract domain-like substrings from business_name where present (per the noise catalog pattern — e.g. "phaedrazengpegasus.com" style entries). Build a simple key (e.g. normalized domain string, or extracted core token from the domain) and run the same exclusivity test.
- For whichever of these two (if either) shows a non-trivial exclusive contribution (i.e. actually recovers true pairs nothing else finds), propose how to fold it into the existing ranked-union score (what weight, roughly, based on its contribution size) rather than as a separate standalone bucket.
- If both come back near-zero exclusive contribution (like phonetic did), report that clearly as a negative result — that's still useful, it means the current 5-signal union is already close to saturating what indexable-key blocking alone can find, and the actual unclosed gap (below) is where remaining effort belongs.

**Output**: `untested_bucket_keys_report.md` — exclusivity numbers for both, recommendation on whether either is worth adding.

---

## PHASE 4 — The actual unrecovered gap: transliteration/cross-script (budget: 1-1.5 hr, this is likely the highest-value phase)

Earlier EDA already identified that the ~1-1.5% of entities NOT recovered even by the best current config (top-500) are dominated by one pattern: native-script pool names (Devanagari/Gujarati/Tamil) with zero shared Latin tokens against the S1 reference name. None of the current bucket keys (exact/token/trigram/address-token/phonetic — all operating on Latin-script tokens) can find these by construction — this isn't a tuning problem, it's a structural blind spot in the current bucketing approach.

- Quantify precisely: of the full validation set, how many true pairs fall into this specific pattern (non-Latin pool name vs Latin S1 name, effectively zero raw token overlap)? Get an exact count/percentage, not just the illustrative examples from before.
- Explore (but time-box to the budget above — this is exploratory, not required to ship tonight) a supplementary blocking channel specifically for this pattern:
  - Option A: a simple transliteration/romanization step (rule-based or a small open, permissively-licensed transliteration library if one exists and is genuinely local/offline — check license and flag if uncertain, do not use anything that phones out to an external API) applied to non-Latin pool names before running them through the EXISTING token/trigram index — i.e. don't build a new indexing mechanism, just extend the existing one's input normalization to cover this case.
  - Option B: if a lightweight approach isn't feasible tonight, at minimum quantify the ceiling precisely and document it clearly as a known, structural, and currently-accepted gap — with the exact percentage — so it's a documented decision, not a silent miss.
- Whatever you attempt, report before/after recall specifically on the non-Latin-name subset, not just overall (overall recall barely moves since this is a small subset — the subset-specific number is what shows whether the attempt actually worked).

**Output**: `transliteration_gap_report.md` — exact gap size, what was attempted, before/after numbers on the affected subset specifically.

---

## PHASE 5 — Consolidated bucketing recommendation (budget: 20-30 min, do not skip)

Write `bucketing_strategy_final.md`:

1. Recommended final config: which signals, what weights/formula, what K (or adaptive K rule), with the recall/compute numbers that justify each choice.
2. Explicit statement of the new expected pair recall / entity recall / avg candidates per query under the recommended config, compared to the old K=150 baseline (0.922/0.987/150).
3. Which of the two untested bucket keys (postal, domain) made the cut, if any, and why.
4. Status of the transliteration gap: closed / partially closed / accepted-as-known-limitation, with the number.
5. Explicit downstream cost estimate: given the new avg-candidates-per-query, roughly how many total (S1 entity × candidate) pairs will the matcher need to score — this is the number that determines whether tomorrow's matching pipeline is actually feasible at the recommended K, so get this right, don't hand-wave it.

---

## OTHER THINGS WORTH CHECKING IF TIME REMAINS (lower priority, only if the above is done early)

- Whether the union score formula's fixed weights (exact +100, phonetic ×0.2, etc.) are actually close to optimal, or whether a quick data-driven reweighting (e.g. logistic regression predicting true-match from the raw component scores, on a holdout slice) would meaningfully improve the recall-per-candidate efficiency of the ranking — this could let you hit the same recall at a lower K, which matters a lot given the downstream compute concern in Phase 5, item 5.
- Whether blocking recall differs meaningfully between S2 and S3 pools specifically (if the EDA closeout run from earlier found a source asymmetry, check whether it also shows up here in blocking recall, not just in raw signal AUC).
- Whether a two-stage blocking approach (cheap wide net first — e.g. token-only — then re-rank the wide net with the full formula) could hit the same recall at lower total compute than scoring the full formula against the whole pool directly. Only explore this if Phase 1's cost numbers suggest the full-formula approach is actually a bottleneck.

---

## RULES

- Every recommendation needs a number from actually running it, not an assumption carried over from a similar-sounding earlier test.
- Stay in blocking/candidate-generation scope — no matcher/model work tonight.
- No external API calls, no internet-sourced augmentation, including for any transliteration step attempted in Phase 4 — local/offline only, and flag license/compliance status of anything used.
- Write each phase's report as you finish it.