# ML Challenge 2026: Business Entity Resolution Solution

**Team Name:** VadaPav  
**Team Members:** Prathamesh Kinagi, Ajinkya Jagdish Pathak, Aayush Kulkarni, Aarush Oak (Pune Institute of Computer Technology)  
**Submission Date:** 2026-09-27

---

## 1. Executive Summary

We link each Source-1 (S1) record to its copies in the S2 + S3 pool in four steps:

1. **Lexical blocking** (an inverted index over 10 key families) and a LightGBM re-ranker. Together they keep about
   6.1 candidates per S1.
2. **A pair classifier** (LightGBM) over 68 handcrafted similarity features plus the score of a cross-encoder:
   `bge-reranker-v2-m3` with a LoRA adapter, fine-tuned on 4.26M of our training pairs.
3. **Two pieces of name-ownership evidence** for pool records that carry a name but no address:
   - where this S1 ranks among *all* S1 names nearest to the pool name;
   - how the candidate compares with the pool records already accepted for the same S1.
4. **A second retrieval channel (DRACE):** dense retrieval with multilingual-e5-small, plus "copy expansion" from pool
   records we already matched. The cross-encoder accepts only pairs it scores ≥ 0.995.

On held-out train S1, DRACE adds +0.0025 F0.5. Public leaderboard: 0.96611 (first submission) → 0.98135 (S10,
DRACE) → 0.98306 (S12, ownership features + fine-tuned retriever) → **0.98360** (S13, deeper fine-tuned retrieval).

---

## 2. Methodology

### 2.1 Problem Analysis

Measured on the training data:

- **Sizes.**
  - Train: S1 2,206,821; S2 5,034,616; S3 5,285,603; 7,638,365 true links.
  - Test: S1 1,732,544; pool 9,969,589.
- **Link structure.**
  - An S1 has 0–11 true pool records, mean ≈ 3.45; 5.59% have none.
  - No pool record belongs to two S1, and true links never cross countries.
  - Record IDs and file row order carry no signal: Spearman −0.002 and 0.001 over 300,000 true pairs, equal to a
    shuffled baseline.
- **Scripts.** S1 is Latin-only. 752,869 train-pool names are in 9 Indic scripts.
- **Missing fields.** About 345K train-pool addresses are empty, and about 87K more are the literal `<NULL>`.
- **Noise on true copies.** The same business appears with:
  - legal-suffix changes (Pvt / Private / Ltd / LLC);
  - word-order changes ("Concepts-Co Digital Value" for "Value Digital Concepts");
  - accents and typos ("Límited", "8eat Milk");
  - a website in place of the name ("urbanconstruction.com");
  - mixed scripts in one address ("Thane, महाराष्ट्र");
  - a corrupted house number ("4900" vs "490"). Accepted pairs whose house numbers disagree are still 99.6% correct
    (`logs/veto_probe.log`).
- **Chains.** Many S1 share a name with other S1. Only 24.7% of the true links of S1 in chains of 10 or more share the
  exact name.
- **France** appears only in test. No step contains country-specific rules. Country is an open-set string, used only as
  a grouping key and as a same/different feature.

### 2.2 Solution Strategy

**Approach type:** blocking + learned re-ranker + pair classifier, with a second, dense retrieval channel whose
additions are judged by a cross-encoder.

**Core contribution:** DRACE (Dense Retrieval And Copy Expansion) and name-ownership features.
- Each business has about 3.45 records in the pool.
- Once one copy is matched with confidence, its nearest neighbours in embedding space are likely other copies. They are
  often ones that share no blocking key with the S1: another script, a website name, a missing address.
- A cross-encoder then decides which of those neighbours are real matches.

**Validation protocol.**
- Train S1 is split 80/20 by seed. The 20% (441,363 S1) is used only for scoring.
- Within the 80%, disjoint S1 slices serve one purpose each: stage-1 tuning, re-ranker training, cross-encoder training
  (DEV_REST_180K, DEV_REST_REST fold 0), matcher experiments (MATCH_TRAIN, 180K S1), matcher confirmation (MATCH_VALID).
- The S2/S3 pool is never split: every query searches the full pool.
- **Matcher experiments** use 5-fold GroupKFold by S1 on MATCH_TRAIN, scored as paired differences per S1 with bootstrap
  95% intervals.
- **Rule choices** (DRACE threshold, retrieval depth) are fitted on one hash half of the S1 and scored on the other.
- **The cross-encoder** never scores a pair whose S1 it was trained on when that score feeds the matcher.
- **Test labels** do not exist and were never used. Every access to test inputs is logged in `reports/test_usage_log.md`.

---

## 3. Candidate Generation (Blocking)

**Normalisation (same code on both sides):**
- Unicode NFC, then romanisation of the 9 Indic scripts.
- Accent folding and case folding; `&` → `and`; punctuation removal.
- Abbreviations mined from the unlabelled pool, per country (e.g. French `r` → `rue` without any French rules).
- A transliteration dictionary learned from train pairs.

**Stage 1: lexical blocking.**
- 10 key families, 64-bit hashed, memory-mapped postings:
  - whole name;
  - name tokens;
  - name character 3-grams;
  - pairs of the first 8 name tokens;
  - Metaphone codes;
  - consonant-skeleton pairs;
  - joined/split name variants;
  - address tokens and address bigrams;
  - name skeleton × rare address token.
- Keys above a document-frequency cap are dropped.
- A logistic model over per-family match scores, plus per-channel quotas, keeps ~290 candidates per S1.
- Ceiling F0.5 0.9957, entity recall 0.9993 on a tuning slice.

**Stage 2: re-ranker.**
- LightGBM on 35 cheap features.
- Keeps rank ≤ 5, or p ≥ 0.05 up to rank 60.
- Result: 6.13 candidates per test S1; on the 441,363 validation S1, entity recall 0.9984 and ceiling F0.5 0.9928.

**DRACE: dense retrieval + copy expansion** (runs after the matcher; `ce/hf_job/retrieve_job.py`, `plan/checks/drace_test.py`).
- **Model:** `intfloat/multilingual-e5-small` (118M parameters) embeds "name | address" for every S1 and pool record;
  mean pooling, L2 norm.
- **S1 query:** the 5 nearest pool records of each S1 in its country (exact cosine search).
- **Distilled S1 query:** the 2 nearest pool records under a copy of e5 fine-tuned on our data (section 4.3).
- **Copy expansion:** for every pool record the matcher accepted, its 2 nearest pool records.
- **Filter:** pairs already in the candidate list, or whose pool record the matcher already assigned, are dropped. The
  rest (about 1.0–1.3 per S1) go to the cross-encoder.

**Candidate pairs submitted:** `candidate_pairs.tsv` holds every pair a model scored: the stage-2 lists plus every DRACE
pair. That's 7.13 per test S1 for S10 and S11.

**Recall recovered by DRACE** (train, 180K S1, against the full 10.3M train pool; `gate1_gate1.json`, `gate1_gate1_distil.json`):
- 15,117 of 621,534 true pairs (2.43%) are not in the stage-2 lists.
- Untrained e5 recovers 44.1% of them at S1 top-5 + copy top-5.
- The distilled model's S1 query recovers 47.7% of the Indian misses at top-5, against 24.4% for the untrained model.

---

## 4. Matching Model

### 4.1 Pair features (68)

- **Name.** Token-set, token-sort, plain and partial ratios; Jaro-Winkler; token Jaccard; IDF-weighted Jaccard and
  coverage; rarest missing token; exact / core / no-space equality; acronym; Monge-Elkan; Metaphone and Soundex Jaccard;
  character TF-IDF cosine.
- **Address.** Token-set/sort; IDF Jaccard; number agreement (shared, conflicting, one-sided, house number, 4-state digit
  code); empty flag; character 3-gram Jaccard; TF-IDF cosine.
- **Context.** Stage-2 score and rank; country same/different/unknown; source S2/S3; Indic flag; S1 chain size; pool
  counts of the same name and address.
- **List position (14).** Size of the S1's list, gap to the best and next score, rank by name and address similarity
  inside the list, number of look-alikes.

### 4.2 Cross-encoder score (c0)

- **Model:** `BAAI/bge-reranker-v2-m3` (568M parameters) with LoRA: r = 16, α = 32, dropout 0.05, on the query/key/value
  projections plus the classifier head (3.4M trainable parameters).
- **Input:** "S1 name | S1 address" and "pool name | pool address", 128 tokens. Only 0.06% of pairs are longer.
- **Training:**
  - Epoch 1 on 971,466 pairs (DEV_REST_180K).
  - Epoch 2 on 3,285,477 new pairs (DEV_REST_REST fold 0): lr 5e-5, batch 32, fp16, one T4, 6.5 h.
- **Held-out quality:** MATCH_VALID AUC 0.99896, logloss 0.0402, against 0.99841 / 0.0507 after epoch 1.
- **How it enters the matcher:** as a single feature. Adding its rank, margins, list z-score, softmax share, entropy, or
  disagreement with stage 2 changed F0.5 by at most ±0.00008 (7 feature families, `cefe_ablation.json`), so only the
  probability is kept.

### 4.3 Name-ownership evidence for records without an address

This is the largest remaining loss:
- 77% of the true pairs the matcher rejects have a pool record with an empty address.
- 97% of those S1 already have at least one accepted match.
- The question is which of several same-named S1 owns a bare name.

Two feature groups address it:

- **Reverse name retrieval** (`plan/checks/rev_prep.py`, 7 columns):
  - The pool record's name is compared with **all** S1 names of the same country (e5 embeddings, top 20).
  - Features: this S1's rank, its cosine, the best cosine, the gap to it, the margin over the best *other* S1, and the
    number of S1 within 0.02 of the best.
  - The margin over the other S1 is the most used new column.
- **Group profile** (`plan/checks/grp_feats.py`, 6 columns):
  - The candidate is compared with the pool records already accepted for this S1 by a first-pass model (out-of-fold on
    every training row).
  - Features: best name token-set and edit ratio, share of its name tokens found in the group, best address similarity,
    number of accepted records from the same source.

**Distilled retriever for DRACE** (`plan/checks/distill_e5.py`, `ce/hf_job/distill_job.py`):
- e5-small fine-tuned on 435,454 triplets (S1, true record, hardest wrong candidate by c0) from DEV_REST_REST fold 1,
  which is disjoint from the evaluation S1.
- Loss: in-batch InfoNCE plus MarginMSE against c0's probability margin, i.e. c0 is used as the teacher.
- 1 epoch, 6.8 minutes on one A100.

### 4.4 Model and decision

- **Model:** LightGBM, binary logloss, no class weighting.
- **Training rows:** the final model trains once on about 837K train S1 (3.86M pairs): MATCH_TRAIN, MATCH_VALID, and
  DEV_REST_REST fold 1. The S1 used to train the cross-encoder are excluded, because their scores would be in-sample.
- **Stopping and calibration:** early stopping on 5% of S1; isotonic calibration on a separate 10% of S1.
- **Decision rule:**
  - Threshold 0.72 on the calibrated probability, then one-owner: each pool record is kept only for the S1 where it
    scores highest.
  - With no capacity limit on the S1 side, this greedy rule is the optimal assignment.
  - Chosen by macro F0.5 on held-out S1.
- **DRACE pairs** skip LightGBM (they have no stage-2 score or list position) and are accepted when c0 ≥ 0.995.
  - On train, a LightGBM trained on DRACE provenance (cosines, ranks, number of seed paths) matched this threshold
    (−0.00001).
  - The added pairs are 97.9% correct at 0.99.

---

## 5. Results & Error Analysis

### F0.5 (macro over S1, singletons included)

| Submission | Change | Held-out train F0.5 | Public LB |
|---|---|---|---|
| S1 | 3 stages, 50 features | 0.9741 (180K OOF) | 0.96611 |
| S2 | 68 features | 0.97807 | 0.96680 |
| S6 | + cross-encoder score (epoch 1) | 0.98438 | 0.97613 |
| S7 | + name frequency | — | 0.97621 |
| **S10** | c0 (epoch 2) + DRACE | 0.98802 (M027 + DRACE, 180K) | **0.98135** |
| S11 | + reverse name retrieval + name frequency | +0.00037 over the S10 matcher | 0.98162 |
| S12 | + group profile + distilled-e5 S1 query in DRACE (top-2) | 0.98643 (matcher, calibration slice) | 0.98306 |
| **S13** | distilled-e5 S1 query widened to top-5 (7.73 candidates per S1) | +0.00026 over S12 (train) | **0.98360** |

Paired gains on 180K MATCH_TRAIN S1 (5-fold, 95% CI, from `artifacts/metrics/`):

| Step | Δ F0.5 |
|---|---|
| Cross-encoder epoch 2 instead of epoch 1 | +0.00106 [0.00091, 0.00121] |
| DRACE, untrained e5 | +0.00251 [0.00239, 0.00264] |
| Reverse name retrieval | +0.00028 [0.00016, 0.00039] |
| Group profile | +0.00016 [0.00005, 0.00027] |
| Distilled S1 query in DRACE (top-2) | +0.00049 [0.00040, 0.00058], India +0.00120 |

### Where the loss is now (S10 on 180K train S1, F0.5 0.98801; `loss_s10.json`)

| Error | Pairs | Oracle gain |
|---|---|---|
| True pair in the list, rejected (77% pool address empty) | 9,878 | +0.00546 |
| True pair found by nothing (keywords, e5 top-50) | 4,900 | +0.00271 |
| Wrong pair accepted by LightGBM | 1,395 | +0.00192 |
| True pair at e5 rank 6–50 | 3,554 | +0.00162 |

- **Common false positives:** branches of one chain on the same street; near-identical names of different businesses
  ("DHL Hotel Limited" vs "IHL Hotel Límited"); name-only records assigned to the wrong one of several same-named S1.
- **Common false negatives:**
  - name-only copies ("Heritage Analytics |" with no address) next to name-only records of other S1 with the same name;
  - trade names with no shared token;
  - transliterations that neither keys nor embeddings connect.

### What did not help (measured, not assumed)

| Idea | Result |
|---|---|
| XGBoost blend; MLP; MLP with periodic numeric embeddings | ±0.0001 blended; raw-p correlation with LightGBM 0.997–0.9998 |
| LambdaRank (listwise) objective | −0.0198 |
| Candidate-list competition features | +0.003 held-out, negative on the LB (test pool is denser: 5.75 vs 4.68 records per S1) |
| Transitive-consistency cleaning (TransClean) | +0.00000; only 0.25% of multi-match predictions are wrong, and c0 is weak on pool-vs-pool pairs (AUC 0.831) |
| Hard house-number / postal vetoes | −0.014 to −0.078; conflicting-number pairs are 99.3–99.7% correct |
| Separate threshold for empty-address pairs; exact-name twin rescue | −0.0001; −0.0003 or worse |

---

## 6. Conclusion

- The pool contains several noisy copies of each business, and that structure carried the last gains.
- A cross-encoder fine-tuned on our pairs gave the biggest single jump (+0.0093 on the public leaderboard).
- DRACE uses the copies to reach records that share no blocking key.
- The ownership features tell the matcher which of several same-named S1 a bare name belongs to.
- Replacing the gradient-boosted matcher with neural or listwise models did not help. The remaining loss is in
  name-only records and in matches that neither keys nor embeddings retrieve.

---

## Appendix

### A. Code Artefacts

- **Core pipeline:** `code/business_entity_resolution/src/ber/`.
  - Ingestion, normalisation, blocking, re-ranker and matcher; `exp.py` holds the feature groups (`cex_p`, `rev`,
    `nfreq`, `grp_full`).
  - Configs in `configs/`; `README.md` has the exact order of commands.
- **Cross-encoder and DRACE scripts** (in the repository next to the package):

| File | Role |
|---|---|
| `ce/train_continue.py`, `ce/kaggle_continue/` | LoRA continuation training of the cross-encoder |
| `ce/hf_job/score_job.py`, `ce/hf_job/collect.py` | cross-encoder scoring on a GPU, reassembly by (S1, pool) |
| `ce/hf_job/retrieve_job.py` | e5 embedding + per-country exact nearest-neighbour search |
| `ce/hf_job/distill_job.py`, `plan/checks/distill_e5.py` | distilling the cross-encoder into e5 |
| `plan/checks/drace_test.py` | DRACE pairs, merge, one-owner, output files |
| `plan/checks/rev_prep.py`, `plan/checks/grp_feats.py`, `plan/checks/firstpass_oof.py` | ownership features |
| `plan/checks/train_final_comp.py` | final LightGBM training (`REST_FOLD=1 EXCLUDE_SETS=DEV_REST_180K`) |
| `plan/checks/run_submission_*.sh` | the exact command chains that produced each submission |

- **Every submitted file** passed `student_resource/utils/validate_submission.py --check-ids`.

### B. Scaling

| Step | Measured here | At billions of records |
|---|---|---|
| Lexical blocking | 2.35 h for 1.73M S1, 8-core laptop | shard queries; postings are memory-mapped |
| LightGBM stages | minutes; linear in ~6–7 candidates per S1 | unchanged |
| Cross-encoder | 3,600 pairs/s on one A100 (10.6M pairs in 49 min) | the main cost; linear in candidates; score only uncertain pairs, or distil |
| Dense retrieval | exact search by matrix multiply, per country | needs an approximate index (FAISS IVF / HNSW) |
| One-owner, name counts | group-bys | map-reduce |

### C. Models and licences

| Model | Size | Licence |
|---|---|---|
| BAAI/bge-reranker-v2-m3 | 568M | Apache-2.0 |
| intfloat/multilingual-e5-small | 118M | MIT |
| Our LoRA adapter | 3.4M trainable | — |
| Distilled e5 | 118M | derived from MIT |

- No external data, APIs or gazetteers.
- GPU jobs ran our own code on Hugging Face Jobs and Kaggle.

### D. References

1. Li, Li, Suhara, Doan, Tan. *Deep Entity Matching with Pre-Trained Language Models* (Ditto). PVLDB 14(1), 2021.
2. Chen et al. *BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings*. arXiv:2402.03216, 2024.
3. Wang, Yang, Huang, Yang, Majumder, Wei. *Multilingual E5 Text Embeddings: A Technical Report*. arXiv:2402.05672, 2024.
4. Hu et al. *LoRA: Low-Rank Adaptation of Large Language Models*. arXiv:2106.09685, 2021.
5. Ke et al. *LightGBM: A Highly Efficient Gradient Boosting Decision Tree*. NeurIPS 2017.
6. Brinkmann, Shraga, Bizer. *SC-Block: Supervised Contrastive Blocking within Entity Resolution Pipelines*. ESWC 2024; arXiv:2303.03132.
   Dense, fine-tuned blocking; basis for DRACE and the distilled retriever.
7. Wang et al. *Towards Universal Dense Blocking for Entity Resolution*. arXiv:2404.14831.
   Dense and sparse blocking are complementary, which is why DRACE adds to the lexical index rather than replacing it.
8. Hofstätter et al. *Improving Efficient Neural Ranking Models with Cross-Architecture Knowledge Distillation*.
   arXiv:2010.02666, 2020. The MarginMSE objective used to distil c0 into e5.
9. *Match, Compare, or Select? An Investigation of Large Language Models for Entity Matching* (ComEM). COLING 2025.
10. *TransClean: Finding False Positives in Multi-Source Entity Matching under Real-World Conditions via Transitive
    Consistency*. arXiv:2506.04006, 2025. Tested; no gain here.
11. *Entity Resolution in Practice: Lessons from a Self-Serve Pipeline*. arXiv:2607.26298.
12. Grinsztajn, Oyallon, Varoquaux. *Why do tree-based models still outperform deep learning on tabular data?* NeurIPS 2022.
13. Gorishniy, Rubachev, Babenko. *On Embeddings for Numerical Features in Tabular Deep Learning*. NeurIPS 2022.
14. Fellegi, Sunter. *A Theory for Record Linkage*. JASA 64(328), 1969.
