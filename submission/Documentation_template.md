# ML Challenge 2026: Business Entity Resolution Solution Template

**Team Name:** VadaPav  
**Team Members:** Prathamesh Kinagi, Ajinkya Jagdish Pathak, Aayush Kulkarni, Aarush Oak (Pune Institute of Computer Technology)  
**Submission Date:** 2026-09-26

---

## 1. Executive Summary

The pipeline has three stages, all trained only on the provided training data:

1. **Blocking.** An inverted index over 9 key families built from normalized text (name tokens, name
   trigrams, token pairs, consonant skeletons, concatenated names, address tokens and bigrams, name ×
   address cross keys). A learned logistic score plus per-channel quotas pulls about 290 candidates per
   S1 from the 10M-record pool.
2. **Candidate re-ranking.** A 35-feature LightGBM re-ranker cuts that list to a mean of **6.13
   candidates per test S1** (10,613,056 pairs, reduction ratio > 0.99999). On validation S1 this keeps
   a perfect-matcher F0.5 ceiling of 0.9928.
3. **Matching.** A 50-feature LightGBM pair classifier with isotonic calibration and a threshold chosen
   for macro F0.5. It scores **entity F0.5 0.9745** on a 20,000-S1 held-out slice, against 0.9460 when
   thresholding the re-ranker score alone.

Two key additions: Indic-script romanization inside normalization (752,869 train-pool names are in
Indic scripts while S1 is Latin-only), and a one-owner constraint (no pool record belongs to two S1
entities).

---

## 2. Methodology

### 2.1 Problem Analysis

Facts measured on the training data (scripts and JSON outputs are in the repository):

- **Sizes.**
  - Train: S1 2,206,821; S2 5,034,616; S3 5,285,603.
  - Test: S1 1,732,544; pool (S2 + S3) 9,969,589.
  - Ground truth: 7,638,365 links, up to 11 per S1; 5.59% of S1 are singletons.
  - No pool record is linked to two S1 entities.
  - Every true link joins records with the same country label.
- **Scripts.** S1 names and addresses are Latin-only. 752,869 train-pool names are written in 9 Indic
  scripts (Devanagari, Telugu, Kannada, Bengali, Tamil, Gujarati, Malayalam, Oriya, Gurmukhi), so plain
  lowercasing gives zero token overlap on those pairs. Romanized pool tokens are English words written
  phonetically ('praivet' → private, 'kansaltin' → consulting).
- **Missing fields.**
  - Addresses: 168,967 (S2) and 175,916 (S3) train-pool addresses are empty, and ≈ 87K more contain the
    literal `<NULL>`.
  - Postal codes: rare in the addresses. 5-digit tokens are mostly US house numbers.
- **Name noise.** Legal-suffix variation (Pvt / Private / Ltd / Limited / LLC / Corp), word-order
  transposition, accented or typo'd letters ('Límited', '5ervices'), DBA / trade names that share no
  token with the registered name.
- **Chains.** Many S1 share a name with other S1 (chains; branches of one brand). Only 24.7% of the
  true links of S1 in chains of 10 or more share the exact name, so name-only keys cannot separate branches.
- **France.** It appears only in test. The pipeline contains no country-specific rules: country is an
  open-set string, used only as a same / different / unknown feature.

### 2.2 Solution Strategy

**Approach Type:** Blocking + learned re-ranker + pairwise classifier (three stages).  
**Core Innovation:** Unsupervised, language-agnostic normalization: Indic romanization, a
train-learned transliteration dictionary, and per-country address-abbreviation mining on the unlabeled
pool. This feeds an inverted index whose candidate list a learned re-ranker shrinks to about 6 per S1
before a calibrated LightGBM matcher decides with an F0.5-optimized rule.

**Validation protocol.**
- Train S1 is split 80 / 20 (seed 42, stratified by country × singleton). The 20% (441,363 S1) is used
  only for scoring.
- The 80% is cut into disjoint slices, each used for exactly one purpose: stage-1 tuning (10K),
  confirmation (10K), stage-1 model (20K), re-ranker training (50K), re-ranker cut (20K), matcher
  training (180K), matcher confirmation (20K).
- S2 and S3 are never split; every query searches the full pool.

---

## 3. Candidate Generation (Blocking)

- **Text normalization (both sides, identical code):**
  1. Unicode NFC.
  2. Drop format characters.
  3. Rule-based romanization of the 9 Indic scripts (stdlib `unicodedata` + fixed tables).
  4. Accent folding and casefolding.
  5. `&` → `and`; punctuation removal.
  6. Letter / digit splitting in addresses.
  7. Fixed abbreviation maps.
  8. Per-country address-abbreviation mining on the unlabeled pool (e.g. French `r` → `rue` found
     without any French rules).
  9. A transliteration dictionary learned from train-S1 pairs. It raised the share of Indic pool
     tokens that match an S1 token from 0.27 to 0.45.
- **Blocking keys used (9 families, 64-bit hashed, CSR postings, memory-mapped):**
  - EN: exact normalized name.
  - NT: name tokens.
  - NG: name character trigrams.
  - NP: pairs among the first 8 name tokens.
  - SP: consonant-skeleton pairs (typos and transliteration).
  - NC: concatenated name with data-mined edge tokens stripped (`happy nails llc` ≈ `happynails`).
  - AT / AB: address tokens / bigrams.
  - XK: name skeleton × rare address token, which reaches chain branches.
  - Keys with document frequency above a fraction of the pool are capped. These fractions were tuned
    in experiments E1–E3.
- **Stage 1:** a logistic model over per-family match scores ranks the union of postings. A quota
  union keeps LEARN 150 + ADDR 50 + PAIR 100 + XK 50 + CAT 20. On a tuning slice this reached a mean of
  291 candidates per S1 with an F0.5 ceiling of 0.9957 and entity recall 0.9993 (experiment E4, 486
  quota configurations).
- **Stage 2 (last filter; its output is `candidate_pairs.tsv`):**
  - LightGBM on 35 cheap features: family scores, coverage, stage-1 ranks, rapidfuzz name and address
    ratios, skeleton Jaccard, postal agreement, country agreement.
  - Trained on 50,000 train S1 (9.95M candidate rows).
  - Cut rule: keep rank ≤ 5, or p ≥ 0.05 and rank ≤ 60. Chosen on a separate 20,000-S1 slice as the
    smallest mean size that loses ≤ 0.002 F0.5 ceiling.
- **Candidate pairs generated:** 10,613,056 for the 1,732,544 test S1. Mean 6.13 per S1, 0 empty lists.
- **How true matches are kept (measured on the 441,363 validation S1, scored once):**
  - Entity recall 0.9984 (S1 with at least one true match among its candidates).
  - Pair recall 0.9755.
  - Perfect-matcher F0.5 ceiling 0.9928.
  - Mean 5.43 candidates per S1.
  - Weakest segment: S1 in chains of 10 or more, ceiling 0.980.

---

## 4. Matching Model

**Input:** exactly the rows of `candidate_pairs.tsv`, plus normalized text from stage 1.

**Features used (50; missing information is NaN, never 0):**
- **Name features:** rapidfuzz token-set, token-sort, plain and partial ratios; Jaro-Winkler on the
  sorted token concatenation; token Jaccard; IDF-weighted token Jaccard and coverage in both
  directions (IDF from pool document frequency, unsupervised); IDF of the rarest token missing on each
  side; equality exact, after removing data-mined edge tokens, and without spaces; acronym match; first
  token equality; longest shared token; consonant-skeleton Jaccard; token counts.
- **Address features:** token-set / token-sort ratios; IDF-weighted Jaccard; rarest missing token
  IDF; numeric-token Jaccard and one-sided number counts; shared vs conflicting numbers of 3 or more
  digits; house-number (first number) agreement; empty-address pattern.
- **Other:**
  - The stage-2 score and rank.
  - Country same / different / unknown; source (S2 / S3); romanized-from-Indic flag; S1 chain size.
  - List context per S1: list size, gap to the best score and to the next score, sum of scores, rank of
    this candidate by name and address similarity, best name similarity among the other candidates,
    number of look-alike candidates.

**Model type:** LightGBM, binary logloss, no class reweighting (the positive rate inside candidate
lists is 0.62).
- 5-fold GroupKFold by S1 on 180,000 train S1 (975,699 rows).
- Each fold early-stops on 10% of its own training S1, at 1,906 – 2,714 rounds.
- Inference averages the 5 fold models.
- Isotonic calibration is fitted on out-of-fold predictions.

**Threshold selection method:**
- Rules compared on out-of-fold predictions for the 180,000 training S1, using macro F0.5 with
  singletons included:
  - a global threshold on calibrated p (0.05 – 0.95, step 0.01);
  - an exact expected-F0.5-optimal top-k per S1 (Poisson-binomial);
  - each of the above with and without a one-owner filter (a pool record kept only for the S1 that
    gives it the highest p).
- Chosen: threshold 0.70 + one-owner filter. The expected-F0.5 rule scored only 0.0002 higher, below
  its required 0.001 gain.
- Nothing was tuned on the confirmation slice or on validation S1.

---

## 5. Results & Error Analysis

- **F_0.5 score (macro, all S1 including singletons):**

| Set | Matcher | Stage-2 score alone (threshold from training slice) | Ceiling |
|---|---|---|---|
| Matcher training slice, out-of-fold (180,000 S1) | 0.9741 | 0.9466 | ≈ 0.993 |
| Matcher confirmation slice (20,000 S1, untouched) | **0.9745** | 0.9460 | 0.9928 |

On the confirmation slice:
- pair precision 0.992; recall within candidates 0.971; singletons correctly empty 97.8%.
- By segment: US 0.978; India 0.970; S1 with exactly one true match 0.910; S1 in chains of 10 or more 0.960.
- Loss (1 − F0.5 = 0.0255) splits into: missed matches present in the candidates 0.0122; blocking
  misses 0.0063; wrong merges on matched S1 0.0051; wrong merges on singletons 0.0013; both 0.0008.
- France has no labels, so its quality is not measured. On test, its predicted-list size (3.28 per S1)
  and empty share (5.6%) match US and India.

- **Common false positives (wrong merges), from out-of-fold predictions:**
  - Branches of one brand at a different house number on the same street
    ("Mcallister Group, 17 Salem Road" vs "24 Salem Rd").
  - Near-identical names that are different entities ("DHL Hotel Limited" vs "IHL Hotel Límited").
  - Records with the same address and a heavily reworded name.
  - 19% of wrong merges have an empty pool address.
- **Common false negatives (missed matches):**
  - 41% have an empty pool address, so the model sees a matching name with no address evidence and
    stays below the threshold.
  - DBA / trade names that share no token with the S1 name ("Golden Barbershop" vs "Iriumbra One" at
    the same address).
  - House-number typos ("19701" vs "9701").

---

## 6. Conclusion

Most of the achievable score is set by blocking: the matcher cannot exceed a 0.9928 ceiling. A
learned re-ranker keeps that ceiling while cutting candidates to about 6 per S1. A calibrated LightGBM
matcher with list-context features then recovers most true matches the re-ranker scored low: missed-match
loss falls from 0.031 to 0.012 without adding wrong merges. The main remaining gaps are matches with
missing pool addresses, trade names with no shared token, and branch disambiguation inside large chains.

---

## Appendix

### A. Code Artefacts

`code/business_entity_resolution/`:
- `src/ber/` — the pipeline package.
- `configs/blocking.json` (stages 1–2, tuned values annotated with the experiment that set them).
- `configs/match.json` (stage 3).
- `run_matcher.sh`.
- `tests/` (158 unit tests).
- `README.md` (exact reproduction steps).
- `requirements.txt` (pinned: numpy, pandas, pyarrow, rapidfuzz, jellyfish, scikit-learn, scipy,
  lightgbm, tqdm, matplotlib).

No pretrained models, external data or network access are used. Entry point, from the folder that
holds `student_resource/dataset/`:

```bash
export PYTHONPATH=code/business_entity_resolution/src
python -m ber.cli ingest --split train     # ... see README section 4 for the full ordered list
python -m ber.cli candidates --set TEST    # stages 1-2 over all test S1
python -m ber.cli write-outputs            # -> work/outputs/candidate_pairs.tsv
bash code/business_entity_resolution/run_matcher.sh   # stage 3 -> work/outputs/matching_results.tsv
```

| Module | Role |
|---|---|
| `ingest.py`, `splits.py` | TSV reading, S1 split and disjoint work slices |
| `textnorm.py`, `translit.py`, `translit_dict.py`, `abbrev_mine.py` | normalization, romanization, learned dictionary, abbreviation mining |
| `keys.py`, `hashing.py`, `index_build.py`, `index_store.py` | key families and memory-mapped index |
| `retrieve.py`, `stage1_model.py` | stage-1 retrieval, logistic score, quota union |
| `rerank.py`, `run_candidates.py` | stage-2 re-ranker and cut, candidate generation |
| `match.py` | stage-3 features, training, calibration, decision rule, prediction |
| `write_outputs.py`, `validate_stream.py`, `monitor.py` | output files, streaming validation, test-side monitoring |

### B. Additional Results

| Stage | Set | Mean candidates / S1 | F0.5 ceiling | Entity recall | Pair recall |
|---|---|---|---|---|---|
| Stage 1 (quota union) | tuning slice, 10,000 S1 | 291 | 0.9957 | 0.9993 | 0.9854 |
| Stage 2 (re-ranker + cut) | validation S1, 441,363 | 5.43 | 0.9928 | 0.9984 | 0.9755 |
| Stage 2 | test, 1,732,544 | 6.13 | — (no labels) | — | — |

Runtime on an 8-core Apple M3 (6 workers):
- train index 805 s;
- stages 1–2 over all test S1: 8,463 s;
- matcher training (5 folds): 988 s;
- test features: 133 s;
- test prediction: 1,806 s.
