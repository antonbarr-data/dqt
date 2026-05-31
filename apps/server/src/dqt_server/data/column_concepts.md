# dqt — Column Concepts and Recommended Checks

A reference mapping common data-column concepts to the dqt detector checks that catch their most likely data quality problems. Calibrated for freelance-marketplace warehouses but generalizable to any transactional product.

**143 concepts across 20 categories.**

## How to use

Each row maps one column concept (e.g. *Email*, *Order total*, *Country code*) to the dqt checks most likely to catch real-world quality problems on a column of that type.

- **Column concept** — what the column represents
- **Description** — plain-English meaning
- **Recommended checks** — semicolon-separated detector slugs with key parameters
- **Priority** — `must-have` / `should-have` / `nice-to-have`, calibrated for marketplace contexts
- **Notes** — what the check catches in practice; why it matters

## Detector check categories (cross-reference)

- **1. Completeness** — null_fraction, row_count, completeness, empty_string_fraction, freshness_seconds_behind, volume_anomaly, date_part_missing_fraction
- **2. Validity** — value_in_range, set_membership, regex_match, string_case, value_validity, numeric_bounds, value_check, cardinality_in_range, column_pair_comparison, pattern_check
- **3. Integrity** — uniqueness, monotonicity, referential_integrity_rate, column_pairs, sql_assertion
- **4. Schema** — schema_changes, column_pair_check
- **5. Univariate outliers** — mad_outlier_fraction, double_mad_outlier_fraction, z_score_outlier_fraction, iqr_outlier_fraction, adjusted_boxplot_fraction, grubbs, gesd, auto_outlier, benford
- **6. Multivariate outliers** — isolation_forest_fraction, mahalanobis_distance, lof_outlier_fraction, ocsvm, hbos, ecod
- **7. Drift** — wasserstein_1, ks_test, psi, kl_divergence, js_divergence, mmd, chi_squared, cramers_v
- **8. Time series** — bocpd, adwin, cusum, page_hinkley, stl_residual_zscore, holt_winters_anomaly, prophet_anomaly, matrix_profile
- **9. Custom** — mutual_information, callable_check, remote_check

## Suggested workflow

1. Open dqt's column browser (datasets page)
2. For each column, identify the concept from this reference
3. Use the recommended checks as the starting set
4. Run dqt's AI suggester (or `dqt.checks.suggest`) for column-specific refinements
5. Calibrate thresholds per your data's distribution shape (see the v0.9.3 calibration tables)

## Categories

- [Identity & References](#identity--references)
- [People](#people)
- [Time](#time)
- [Money](#money)
- [Quantity & Counts](#quantity--counts)
- [Status & State](#status--state)
- [Categorization](#categorization)
- [Geography](#geography)
- [Content & Media](#content--media)
- [Communication](#communication)
- [Behavioral & Engagement](#behavioral--engagement)
- [Marketing & Attribution](#marketing--attribution)
- [Reviews & Reputation](#reviews--reputation)
- [Trust, Safety, Fraud](#trust-safety-fraud)
- [Payments](#payments)
- [Subscriptions](#subscriptions)
- [Marketplace Mechanics](#marketplace-mechanics)
- [Quality of Service](#quality-of-service)
- [Operational & Audit](#operational--audit)
- [URLs & External](#urls--external)

---

## Identity & References

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Entity ID (primary key)** | Primary key for users, freelancers, clients, gigs, orders. | `uniqueness`<br>`null_fraction (fail_threshold ≤ 0.0001)`<br>`regex_match (format guard)`<br>`row_count` | **must-have** | PKs should be 100% non-null and 100% unique. |
| **Foreign key** | Reference to another entity (e.g. client_id, freelancer_id). | `referential_integrity_rate (to parent table)`<br>`null_fraction`<br>`cardinality_in_range` | **must-have** | Most common silent bug: orphaned FKs after upstream deletes. |
| **External ID** | IDs from external systems (Stripe, OAuth, partner integrations). | `uniqueness`<br>`null_fraction`<br>`regex_match (provider format)`<br>`set_membership (provider whitelist)` | **must-have** | Format often well-defined per provider — pattern checks catch corruption. |
| **Slug / handle** | Human-readable identifiers (@username, URL fragments). | `uniqueness`<br>`regex_match (allowed charset)`<br>`string_case`<br>`null_fraction` | should-have | Lower-case + alphanumeric+dash is the typical contract. |
| **Hash / idempotency key** | Deduplication keys, idempotency tokens. | `uniqueness`<br>`regex_match (hash format e.g. sha256 length)`<br>`null_fraction` | should-have | Length and hex-only charset are the obvious checks. |

## People

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Name** | Display name, full name, business name. | `null_fraction`<br>`empty_string_fraction`<br>`string_case`<br>`regex_match (loose charset)` | should-have | Avoid strict format rules; international names break naive patterns. |
| **Email** | Email address. | `regex_match (RFC-lite pattern)`<br>`null_fraction`<br>`uniqueness (per-user)`<br>`string_case (lowercase)` | **must-have** | Storing lowercased is the most common convention; check it. |
| **Phone** | Phone number. | `regex_match (E.164 format)`<br>`null_fraction`<br>`pattern_check (international)` | should-have | E.164 (+CCC...) is the warehouse-friendly format. |
| **Avatar URL** | Profile image URL. | `regex_match (URL format)`<br>`null_fraction`<br>`pattern_check (https only)` | _nice-to-have_ | https-only is a security guarantee worth enforcing. |
| **Bio / about** | Long-form text about a person or business. | `null_fraction`<br>`empty_string_fraction`<br>`value_in_range (character count)` | _nice-to-have_ | Watch for HTML injection via cardinality of distinct lengths. |
| **Role / persona** | Enum: buyer/seller/freelancer/client/admin. | `set_membership`<br>`null_fraction`<br>`cardinality_in_range` | **must-have** | Classic enum — set_membership catches typos and new values. |
| **Account status** | Enum: active/suspended/pending/banned/dormant. | `set_membership`<br>`null_fraction`<br>`cardinality_in_range` | **must-have** | Status drift is a common silent failure. |
| **Verification level** | Tier: email_verified / id_verified / kyc_full. | `set_membership`<br>`monotonicity (per user over time)`<br>`null_fraction` | should-have | Verification levels should only increase, not decrease. |

## Time

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Created timestamp** | When the record was created. | `null_fraction`<br>`value_in_range (max_value: now())`<br>`monotonicity (id vs created_at)` | **must-have** | Never NULL on created_at. Never in the future. |
| **Updated timestamp** | Last modification time. | `value_in_range (max_value: now())`<br>`column_pair_comparison (updated_at >= created_at)` | **must-have** | Cross-column check catches clock skew and bugs. |
| **Event timestamp** | When an event occurred (purchase, login, click). | `freshness_seconds_behind`<br>`value_in_range (max_value: now())`<br>`volume_anomaly` | **must-have** | Freshness is the single most useful event-table check. |
| **Scheduled timestamp** | Future time when something should happen. | `null_fraction`<br>`value_in_range (min_value: now() at insertion)` | should-have | Scheduled times in the past on insertion indicate bugs. |
| **Period start / end** | Range bounds (billing period, campaign). | `column_pair_comparison (end > start)`<br>`null_fraction`<br>`value_in_range` | **must-have** | End-before-start is a classic data corruption signal. |
| **Date partition** | Partition key (day, week, month). | `date_part_missing_fraction`<br>`set_membership (expected values)`<br>`volume_anomaly` | **must-have** | Missing partitions = silent data gaps. Always check. |
| **Time zone** | IANA zone or UTC offset. | `set_membership (IANA tz list)`<br>`regex_match`<br>`null_fraction` | should-have | Mixing tz-naive and tz-aware times is a top-5 warehouse bug. |
| **Duration** | Elapsed time in seconds/minutes. | `value_in_range (min_value: 0)`<br>`mad_outlier_fraction`<br>`null_fraction` | should-have | Negative durations indicate clock issues. |
| **TTL / expiry** | When something becomes invalid. | `value_in_range (min_value: now())`<br>`null_fraction` | should-have | Expired-on-insertion is a logic bug worth flagging. |

## Money

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Price (list / asking)** | List price for a gig or service. | `value_in_range (min_value: 0)`<br>`mad_outlier_fraction`<br>`null_fraction`<br>`wasserstein_1 (drift)` | **must-have** | Heavy-tailed — use MAD, not z-score. |
| **Bid amount** | What a freelancer proposes. | `value_in_range (min_value: 0)`<br>`mad_outlier_fraction`<br>`null_fraction` | **must-have** | Outliers here are either fraud or testing — both worth catching. |
| **Order total** | What was actually transacted. | `value_in_range (min_value: 0)`<br>`mad_outlier_fraction`<br>`null_fraction`<br>`volume_anomaly`<br>`wasserstein_1` | **must-have** | The headline revenue input. Drift detection is essential. |
| **Fee (commission, processing)** | Platform commission or processing fee. | `value_in_range (min_value: 0)`<br>`column_pair_comparison (fee <= order_total)`<br>`null_fraction` | **must-have** | Cross-column check catches percentage-of-zero bugs. |
| **Tax** | Sales tax, VAT, withholding. | `value_in_range (min_value: 0)`<br>`column_pair_comparison (tax <= order_total)`<br>`null_fraction` | should-have | Negative tax is meaningful only on refunds — segment accordingly. |
| **Discount** | Promotional reduction. | `value_in_range (min/max)`<br>`column_pair_comparison (discount <= order_total)`<br>`null_fraction` | should-have | 100%+ discounts are typically bugs unless explicitly modeled. |
| **Refund amount** | Reversal amount. | `value_in_range (min_value: 0)`<br>`column_pair_comparison (refund <= order_total)`<br>`null_fraction` | **must-have** | Refund > original is a serious billing bug. |
| **Payout** | What a freelancer receives net of fees. | `value_in_range (min_value: 0)`<br>`column_pair_comparison (payout <= order_total - fee)`<br>`mad_outlier_fraction` | **must-have** | The math has to reconcile or someone gets paid wrong. |
| **Wallet balance** | Held funds available to a user. | `value_in_range (min_value: 0)`<br>`null_fraction`<br>`mad_outlier_fraction` | **must-have** | Negative balances = bug or fraud; either way, page someone. |
| **Escrow amount** | Funds held pending delivery. | `value_in_range (min_value: 0)`<br>`null_fraction` | should-have | Volume anomaly on escrow indicates flow disruption. |
| **Lifetime value (LTV)** | Cumulative spend per user. | `value_in_range (min_value: 0)`<br>`monotonicity (per user)`<br>`mad_outlier_fraction` | should-have | LTV should only increase per user. |
| **Average order value (AOV)** | Derived metric, often per cohort. | `value_in_range (min_value: 0)`<br>`bocpd (changepoint over time)`<br>`wasserstein_1 (drift)` | should-have | AOV shifts often signal mix-shift; surface them. |
| **Take rate** | Platform's share of GMV. | `value_in_range (0.0 to 1.0)`<br>`bocpd`<br>`null_fraction` | **must-have** | Take rate drift is the canary for pricing bugs and policy changes. |
| **Currency code** | ISO 4217 (USD, EUR, GBP). | `set_membership (ISO 4217)`<br>`null_fraction`<br>`cardinality_in_range` | **must-have** | Unknown currency codes break all downstream FX math. |
| **FX rate** | Currency conversion rate at txn time. | `value_in_range (min_value: 0)`<br>`null_fraction`<br>`mad_outlier_fraction`<br>`freshness_seconds_behind` | **must-have** | Stale FX = systematic revenue miscalculation. |

## Quantity & Counts

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Count (items, messages, views)** | Generic count column. | `value_in_range (min_value: 0)`<br>`null_fraction`<br>`mad_outlier_fraction` | should-have | Negative counts indicate signed-int overflow or bad joins. |
| **Rating count** | Number of reviews received. | `value_in_range (min_value: 0)`<br>`monotonicity (per entity)`<br>`null_fraction` | should-have | Counts only go up — monotonicity catches deletes. |
| **Star rating** | Average or instance rating. | `value_in_range (min: 1.0, max: 5.0)`<br>`null_fraction`<br>`mad_outlier_fraction` | **must-have** | Out-of-range = bug. 1.0-5.0 or 0-100 are the usual conventions. |
| **Score (composite)** | Seller score, gig score, trust score. | `value_in_range (typically 0-100 or 0-1)`<br>`null_fraction`<br>`bocpd (drift over time)` | should-have | Composite scores drift as inputs change — track it. |
| **Rank / position** | Placement in search results, leaderboards. | `value_in_range (min_value: 1)`<br>`uniqueness (per query/list)`<br>`null_fraction` | should-have | Rank ties and gaps both indicate ranker bugs. |
| **Capacity** | Max concurrent gigs, max storage. | `value_in_range (min_value: 0)`<br>`null_fraction`<br>`cardinality_in_range` | _nice-to-have_ | Capacity changes are policy decisions — log them. |
| **Inventory** | Stock level for digital goods, license seats. | `value_in_range (min_value: 0)`<br>`null_fraction` | should-have | Negative inventory = oversell. Page someone. |

## Status & State

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Order status** | Enum: draft/placed/accepted/in-progress/delivered/completed/cancelled/refunded. | `set_membership`<br>`null_fraction`<br>`cardinality_in_range` | **must-have** | New statuses appearing without code changes = enum drift. |
| **Payment status** | Enum: pending/authorized/captured/settled/failed/refunded. | `set_membership`<br>`null_fraction`<br>`cardinality_in_range` | **must-have** | Payment status enum drift directly affects revenue recognition. |
| **Listing status** | Enum: draft/active/paused/sold-out/archived. | `set_membership`<br>`null_fraction`<br>`cardinality_in_range` | **must-have** | Same as order status — enum drift is the silent killer. |
| **Approval status** | Enum: pending/approved/rejected/escalated. | `set_membership`<br>`null_fraction` | should-have | Volume anomaly on 'rejected' is the moderation health signal. |
| **Stage (pipeline position)** | Lead/qualified/proposal/won/lost. | `set_membership`<br>`null_fraction`<br>`cardinality_in_range` | should-have | Stage stuck for too long → freshness check per user/deal. |
| **Tier / level** | Bronze/silver/gold/top-rated. | `set_membership`<br>`null_fraction`<br>`monotonicity (per user, upward only)` | should-have | Tier should rise or stay; falling = demotion event worth flagging. |
| **Flag (boolean)** | is_featured, is_verified, is_premium, is_deleted. | `set_membership ({true, false})`<br>`null_fraction` | **must-have** | NULL booleans almost always indicate a bug. |
| **Reason code** | Cancellation reason, rejection reason, dispute type. | `set_membership`<br>`null_fraction (when status indicates reason required)` | should-have | Reason code populated only when parent status calls for it. |

## Categorization

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Category** | Service category, product type, skill area. | `set_membership`<br>`null_fraction`<br>`cardinality_in_range` | **must-have** | Categories drift slowly; cardinality_in_range catches the drift. |
| **Subcategory** | Finer-grained tag within a category. | `set_membership`<br>`column_pair_comparison (valid subcategory for category)`<br>`null_fraction` | should-have | Cross-column constraint: not every subcategory fits every category. |
| **Tag** | Free-form or controlled-vocabulary labels. | `regex_match (allowed charset)`<br>`cardinality_in_range`<br>`null_fraction` | _nice-to-have_ | Tag explosion is common; cardinality_in_range catches it. |
| **Skill** | Competency (Python, copywriting, video). | `set_membership (controlled vocabulary)`<br>`cardinality_in_range` | should-have | Free-text skills become dirty fast. |
| **Language** | ISO 639 code or spoken language proficiency. | `set_membership (ISO 639)`<br>`null_fraction`<br>`regex_match` | should-have | ISO 639 is the warehouse-friendly standard. |
| **Industry / vertical** | Finance, healthcare, gaming, education. | `set_membership`<br>`null_fraction`<br>`cardinality_in_range` | should-have | Industry taxonomy drift directly impacts segmentation. |

## Geography

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Country code** | ISO 3166-1 alpha-2 / alpha-3. | `set_membership (ISO 3166)`<br>`null_fraction`<br>`string_case (uppercase)` | **must-have** | Top reason category drift fails — bad country codes. |
| **Region / state** | ISO 3166-2 subdivision. | `set_membership (ISO 3166-2)`<br>`column_pair_comparison (subdivision valid for country)` | should-have | Cross-column: subdivision must belong to the country. |
| **City** | City name. | `null_fraction`<br>`empty_string_fraction`<br>`regex_match (no special chars)` | _nice-to-have_ | Cities are messy; avoid strict format rules. |
| **Postal code** | Country-specific format. | `regex_match (per country)`<br>`column_pair_comparison (matches country format)`<br>`null_fraction` | should-have | Format varies by country — cross-column gives the precision. |
| **Latitude / longitude** | Coordinates. | `value_in_range (lat: -90 to 90, lng: -180 to 180)`<br>`null_fraction (both or neither)` | should-have | 0,0 ('null island') often indicates a default-value bug. |
| **IP address** | Source IP for fraud / geo / sessions. | `regex_match (IPv4 or IPv6)`<br>`null_fraction`<br>`cardinality_in_range` | should-have | Same IP across many users = bot/proxy signal. |
| **Inferred location** | IP-derived country, browser-locale guess. | `set_membership (ISO 3166)`<br>`column_pair_comparison (matches user.country if available)` | _nice-to-have_ | Mismatch with declared country is interesting, not always wrong. |

## Content & Media

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Title / headline** | Short string describing gig/project/message. | `null_fraction`<br>`empty_string_fraction`<br>`value_in_range (character count)` | **must-have** | Empty titles surface immediately in product, page someone. |
| **Description (long-form)** | Multi-paragraph text. | `null_fraction`<br>`empty_string_fraction`<br>`value_in_range (character count)` | should-have | Min length 50 chars typical; max 5000-10000. |
| **Cover image URL** | Primary image URL. | `regex_match (URL)`<br>`null_fraction`<br>`pattern_check (https only)` | should-have | Broken images = embarrassing user experience. |
| **Gallery image URLs** | Array or comma-separated list. | `null_fraction`<br>`cardinality_in_range (count)`<br>`regex_match (per URL)` | _nice-to-have_ | Large galleries should have a reasonable upper bound. |
| **Video URL** | Hosted video URL. | `regex_match (URL)`<br>`null_fraction`<br>`pattern_check (https only)` | _nice-to-have_ | Check the host domain via pattern_check. |
| **File size (bytes)** | Attachment or asset size. | `value_in_range (min_value: 0, max: per-tier limit)`<br>`mad_outlier_fraction` | should-have | Files over limit are upload-flow bugs. |
| **MIME type** | Content type identifier. | `set_membership (allowed MIME types)`<br>`null_fraction` | should-have | MIME drift is a security signal. |
| **Word / character count** | For written deliverables or messages. | `value_in_range`<br>`null_fraction`<br>`mad_outlier_fraction` | _nice-to-have_ | Outlier-long submissions = either valuable or spam. |

## Communication

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Message body** | Inbound/outbound message text. | `null_fraction`<br>`empty_string_fraction`<br>`value_in_range (character count)`<br>`cardinality_in_range` | should-have | Watch for duplicate message bursts via cardinality. |
| **Message direction** | Enum: inbound / outbound / internal. | `set_membership`<br>`null_fraction` | **must-have** | Direction misclassification breaks all conversation analytics. |
| **Channel** | Email / SMS / push / in-app / webhook. | `set_membership`<br>`null_fraction`<br>`cardinality_in_range` | **must-have** | Channel drift = new integration not yet documented. |
| **Subject line** | Email subject. | `null_fraction`<br>`empty_string_fraction`<br>`value_in_range (character count)` | should-have | Subject < 5 chars or > 80 = usability issues. |
| **Open / click status** | Booleans on email events. | `set_membership ({true, false})`<br>`column_pair_comparison (click implies open)` | should-have | Cross-column: clicks without opens = tracking bug. |
| **Response time** | First-response or average response latency. | `value_in_range (min_value: 0)`<br>`mad_outlier_fraction`<br>`bocpd` | should-have | Response time SLA drift = team capacity or process change. |
| **Sentiment score** | Positive / neutral / negative inference. | `set_membership or value_in_range (-1 to 1)`<br>`null_fraction`<br>`wasserstein_1` | should-have | Sentiment drift on inbound = product issue brewing. |

## Behavioral & Engagement

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Session ID** | Unique session identifier. | `uniqueness (per session)`<br>`null_fraction`<br>`regex_match (UUID format)` | should-have | Session ID collisions = analytics chaos. |
| **Session start / end** | Session bounds. | `column_pair_comparison (end > start)`<br>`value_in_range (duration < 24h)` | should-have | Multi-day sessions = device sleep, not real engagement. |
| **Page views** | Pages viewed per session. | `value_in_range (min: 1)`<br>`mad_outlier_fraction`<br>`null_fraction` | should-have | Sessions with 0 page views indicate tracking misfire. |
| **Click count** | Clicks per session. | `value_in_range (min: 0)`<br>`column_pair_comparison (click <= page_views * 10ish)` | _nice-to-have_ | Clickbots show as extreme outliers. |
| **Time on page** | Seconds spent on a page. | `value_in_range (min: 0)`<br>`mad_outlier_fraction`<br>`null_fraction` | should-have | Long tails are bots or open-tab artifacts. |
| **Bounce indicator** | Single-page session flag. | `set_membership ({true, false})`<br>`column_pair_comparison (bounce -> page_views == 1)` | should-have | Cross-column consistency catches tracker bugs. |
| **Search query** | What the user typed. | `null_fraction`<br>`empty_string_fraction`<br>`value_in_range (character count)` | should-have | Long-tail queries are interesting; track distribution. |
| **Funnel step** | Which stage of a flow. | `set_membership`<br>`null_fraction`<br>`monotonicity (per session, generally increasing)` | should-have | Skipped steps = analytics dropouts. |
| **A/B test variant** | Experimental group assignment. | `set_membership`<br>`cardinality_in_range`<br>`null_fraction` | **must-have** | Variant drift = experiment integrity violation. |
| **Event name** | Discrete tracked action. | `set_membership (allowed event taxonomy)`<br>`cardinality_in_range` | **must-have** | Untaxonomized events = silent product launches. |

## Marketing & Attribution

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Acquisition source** | Organic / paid / referral / direct. | `set_membership`<br>`null_fraction`<br>`cardinality_in_range` | **must-have** | Source drift = new channel turned on without instrumentation. |
| **UTM parameters** | source, medium, campaign, term, content. | `null_fraction`<br>`regex_match (URL-safe charset)`<br>`cardinality_in_range` | should-have | UTM hygiene is a perennial discipline problem. |
| **Referrer URL** | Where the user came from. | `regex_match (URL or empty)`<br>`null_fraction` | _nice-to-have_ | Watch self-referrers (your domain in the referrer). |
| **Campaign ID** | Reference to a campaign. | `referential_integrity_rate (to campaigns table)`<br>`null_fraction` | should-have | Orphaned campaign IDs are common after campaigns archive. |
| **Cost per click / acquisition** | Ad spend efficiency. | `value_in_range (min: 0)`<br>`mad_outlier_fraction`<br>`bocpd` | should-have | CPC/CPA drift = ad market shift or budget event. |
| **Conversion flag** | Did this visit convert? | `set_membership ({true, false})`<br>`null_fraction` | **must-have** | NULL on conversion flag breaks every funnel metric. |
| **Attribution weight** | Fractional credit in multi-touch. | `value_in_range (0.0 to 1.0)`<br>`null_fraction`<br>`column_pair_comparison (weights sum to 1.0 per conversion)` | should-have | Weights not summing to 1.0 = attribution model bug. |

## Reviews & Reputation

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Review body** | Written feedback text. | `null_fraction`<br>`empty_string_fraction`<br>`value_in_range (character count)`<br>`cardinality_in_range` | should-have | Duplicate reviews (low cardinality vs row count) = spam. |
| **Star rating** | Per-review rating. | `value_in_range (1 to 5)`<br>`null_fraction`<br>`cardinality_in_range` | **must-have** | Same as quantity → ratings, applied per review row. |
| **Recommendation flag** | Would-recommend yes/no. | `set_membership ({true, false})`<br>`null_fraction` | should-have | NULL on recommendation = survey UI bug. |
| **Review helpfulness** | Upvotes on a review. | `value_in_range (min: 0)`<br>`monotonicity (only increases over time)` | _nice-to-have_ | Helpfulness should only grow per review. |
| **Reviewer / reviewee ID** | Foreign keys to users. | `referential_integrity_rate`<br>`column_pair_comparison (reviewer != reviewee)`<br>`null_fraction` | **must-have** | Self-reviews = fraud or test data leakage. |
| **Review verified** | Did reviewer actually purchase? | `set_membership ({true, false})`<br>`null_fraction` | should-have | Verified-review rate is a trust signal. |

## Trust, Safety, Fraud

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Risk score** | Composite fraud likelihood. | `value_in_range (0 to 100 or 0 to 1)`<br>`bocpd (drift)`<br>`null_fraction` | **must-have** | Risk-score distribution drift = fraud landscape change. |
| **IP reputation score** | Per-IP risk signal. | `value_in_range (0 to 100)`<br>`null_fraction`<br>`mad_outlier_fraction` | should-have | High-reputation IPs flooding = botnet signal. |
| **Device fingerprint** | Per-device identifier. | `uniqueness (per device)`<br>`null_fraction`<br>`cardinality_in_range` | should-have | Low cardinality vs user count = device-spoofing. |
| **Anomaly flag** | Upstream-detected unusual indicator. | `set_membership ({true, false})`<br>`volume_anomaly (rate over time)` | should-have | Anomaly-flag rate spike = upstream model change. |
| **Manual review flag** | Queued for human review. | `set_membership ({true, false})`<br>`volume_anomaly` | **must-have** | Manual review queue volume = capacity planning input. |
| **Sanctions flag** | OFAC/PEP/restricted-country. | `set_membership ({true, false})`<br>`null_fraction` | **must-have** | Sanctions checks are regulatory; NULL is unacceptable. |
| **Chargeback indicator** | Disputed transaction flag. | `set_membership ({true, false})`<br>`volume_anomaly`<br>`bocpd` | **must-have** | Chargeback rate is a top-tier executive metric. |
| **Banned reason code** | Why a user was banned. | `set_membership`<br>`null_fraction (when status=banned)` | should-have | Reason code populated only when ban status applies. |

## Payments

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Payment method type** | Card / bank / wallet / crypto. | `set_membership`<br>`null_fraction`<br>`cardinality_in_range` | **must-have** | New payment methods enabled without instrumentation. |
| **Card brand** | Visa / Mastercard / Amex / etc. | `set_membership`<br>`null_fraction` | should-have | Brand drift can indicate fraud-pattern shifts. |
| **Card last-four** | Last 4 digits. | `regex_match (4 digits)`<br>`null_fraction` | should-have | Should never exceed 4 chars or contain non-digits. |
| **Card BIN** | First 6 digits, for issuer lookup. | `regex_match (6 digits)`<br>`null_fraction`<br>`set_membership (known BINs)` | should-have | BIN reveals issuer country — useful for fraud. |
| **Card expiry** | MM/YY or month/year. | `value_in_range (year: now to now+10)`<br>`regex_match` | **must-have** | Expired-on-issue = tokenization bug. |
| **Gateway / processor** | Stripe / Adyen / Braintree. | `set_membership`<br>`cardinality_in_range` | **must-have** | Gateway routing changes are operational events. |
| **Authorization code** | Processor auth response. | `null_fraction (when payment_status='authorized')`<br>`regex_match (processor format)` | should-have | Missing auth code on authorized payments = sync bug. |
| **Settlement date** | When funds settle. | `value_in_range (>= transaction_date)`<br>`null_fraction`<br>`column_pair_comparison` | should-have | Settlement before transaction = clock or logic bug. |

## Subscriptions

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Plan name** | Subscription tier name. | `set_membership (active plan list)`<br>`null_fraction`<br>`cardinality_in_range` | **must-have** | Plans deprecated but still referenced = legacy data risk. |
| **Billing interval** | Monthly / annual / weekly. | `set_membership`<br>`null_fraction`<br>`cardinality_in_range` | **must-have** | Interval drift affects MRR math directly. |
| **MRR / ARR** | Recurring revenue per subscription. | `value_in_range (min: 0)`<br>`mad_outlier_fraction`<br>`bocpd` | **must-have** | Headline metric; track drift carefully. |
| **Churn flag** | Has this subscription ended? | `set_membership ({true, false})`<br>`volume_anomaly`<br>`bocpd` | **must-have** | Churn rate spike = retention crisis. |
| **Cancellation reason** | Why subscription ended. | `set_membership`<br>`null_fraction (when churn_flag=true)` | should-have | Reason code drift = new churn theme emerging. |
| **Trial flag** | Currently in trial. | `set_membership ({true, false})`<br>`column_pair_comparison (trial_end_date set when flag=true)` | should-have | Trial-without-end-date is a flow bug. |

## Marketplace Mechanics

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Bid / application count** | Proposals on a job. | `value_in_range (min: 0)`<br>`mad_outlier_fraction`<br>`null_fraction` | should-have | Sudden spikes = bot activity or virality. |
| **View count** | Page visits per gig. | `value_in_range (min: 0)`<br>`volume_anomaly`<br>`mad_outlier_fraction` | should-have | View count drift = SEO or recommendation change. |
| **Acceptance rate** | % of orders the seller accepted. | `value_in_range (0.0 to 1.0)`<br>`bocpd`<br>`null_fraction` | **must-have** | Acceptance rate drift = seller-side capacity issue. |
| **Completion rate** | % of orders successfully delivered. | `value_in_range (0.0 to 1.0)`<br>`bocpd`<br>`null_fraction` | **must-have** | Completion rate is a top supply-side KPI. |
| **On-time delivery rate** | % of orders delivered by promise date. | `value_in_range (0.0 to 1.0)`<br>`bocpd`<br>`mad_outlier_fraction` | **must-have** | On-time rate is a buyer-trust input. |
| **Response rate** | % of messages replied to. | `value_in_range (0.0 to 1.0)`<br>`bocpd` | should-have | Response rate drift = seller engagement signal. |
| **Cancellation rate** | % of orders cancelled. | `value_in_range (0.0 to 1.0)`<br>`bocpd`<br>`volume_anomaly` | **must-have** | Cancellation rate spike = upstream problem; investigate. |

## Quality of Service

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Delivery time** | Actual time from order to delivery. | `value_in_range (min: 0)`<br>`mad_outlier_fraction`<br>`bocpd` | should-have | Delivery time drift = capacity or workflow change. |
| **Expected delivery time** | Quoted at order time. | `value_in_range (min: 0)`<br>`column_pair_comparison (actual <= expected * 1.5 nominally)` | should-have | Promise-vs-actual delta is the SLA breach signal. |
| **Revision count** | Number of revisions requested. | `value_in_range (min: 0)`<br>`mad_outlier_fraction`<br>`bocpd` | should-have | Revision count drift = quality or expectation mismatch. |
| **SLA breach flag** | Was the SLA broken? | `set_membership ({true, false})`<br>`volume_anomaly` | **must-have** | SLA breach rate is the operational health top-line. |

## Operational & Audit

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Created by / updated by** | User who modified the record. | `referential_integrity_rate (to users)`<br>`null_fraction (when audit required)` | should-have | NULL when audit policy requires = compliance gap. |
| **Source system** | Which service wrote this row. | `set_membership`<br>`cardinality_in_range` | should-have | New source systems should be approved before ingest. |
| **ETL run ID** | Pipeline batch identifier. | `referential_integrity_rate (to runs)`<br>`null_fraction`<br>`regex_match (run-id format)` | should-have | Orphaned run IDs = pipeline metadata corruption. |
| **dbt model name** | For derived columns. | `set_membership (deployed model list)`<br>`cardinality_in_range` | _nice-to-have_ | Model name drift = release event. |

## URLs & External

| Column concept | Description | Recommended checks | Priority | Notes |
|---|---|---|---|---|
| **Profile / portfolio URL** | User-facing URL. | `regex_match (URL)`<br>`null_fraction`<br>`pattern_check (https)` | should-have | http (not https) = mixed-content issue. |
| **Social handle** | @-handle on LinkedIn/GitHub/Twitter. | `regex_match (per-platform format)`<br>`null_fraction`<br>`uniqueness` | _nice-to-have_ | Format varies by platform; multi-pattern check helps. |
| **Webhook target URL** | Outbound webhook endpoint. | `regex_match (URL)`<br>`pattern_check (https only)`<br>`null_fraction` | **must-have** | Webhooks going to http = data leak risk. |

---

## Vocabulary note

In dqt:
- A **detector** is a Python class — the algorithm type (e.g. `mad_outlier_fraction`, `wasserstein_1`). There are 64 of them.
- A **check** is a configured instance — the detector applied to a specific column with specific parameters. Users create checks; dqt provides detectors.

This reference recommends checks. The underlying detectors are documented in `dqt/algorithms/docs/<group>/<slug>.md` (shipped in the wheel since v0.9.3).

---

*This list is opinionated for freelance-marketplace workloads. Adjust priorities for your domain.*
