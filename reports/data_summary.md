# Data summary (from artifacts/metrics/data_summary.json)

## train_source1.tsv: 2206821 rows; cols=entity_id,business_name,business_address,country
countries: {"US": 1323633, "India": 883188}
empty: {}; prefixes: {"S1": 2206821}
non-ascii rows by country: {"India": 554}
non-latin rows by country: {"India": 554}

## train_source2.tsv: 5034616 rows; cols=entity_id,business_name,business_address,country
countries: {"India": 2017799, "US": 3016817}
empty: {"business_address": 168967}; prefixes: {"S2": 5034616}
non-ascii rows by country: {"India": 904496, "US": 202224}
non-latin rows by country: {"India": 904496, "US": 202224}

## train_source3.tsv: 5285603 rows; cols=entity_id,business_name,business_address,country
countries: {"US": 3170056, "India": 2115547}
empty: {"business_address": 175916}; prefixes: {"S3": 5285603}
non-ascii rows by country: {"US": 215616, "India": 774056}
non-latin rows by country: {"US": 215616, "India": 774056}

## train_ground_truth.tsv: 2206821 rows; cols=source1_entity_id,matched_entity_ids
singleton_rate=0.0558 (123247/2206821); max_matches=11; s2_links=3693619 s3_links=3944746 bad_format=0
match-count dist: {"0": 123247, "1": 119157, "2": 375212, "3": 530841, "4": 484115, "5": 321957, "6": 164868, "7": 63968, "8": 18680, "9": 4205, "10": 534, "11": 37}

## test_source1.tsv: 1732544 rows; countries={"US": 663106, "France": 259452, "India": 809986}; prefixes={"S1": 1732544}
## test_source2.tsv: 4887273 rows; countries={"India": 2312565, "France": 703378, "US": 1871330}; prefixes={"S2": 4887273}
## test_source3.tsv: 5082316 rows; countries={"India": 2405000, "France": 731615, "US": 1945701}; prefixes={"S3": 5082316}

## GT integrity (from artifacts/metrics/gt_checks.json)
S1 ID set == GT S1 set (2206821 each, 0 diff). All 7638365 GT links exist in pool (0 missing).
Each pool record has <=1 owner (raw == unique). This enables Phase 3 rule R4.

## machine: ncpu=8 mem_GB=17.2 disk_free_GB=1917.4
battery: Now drawing from 'AC Power'
 -InternalBattery-0 (id=22872163)	64%; charging; 1:00 remaining present: true
