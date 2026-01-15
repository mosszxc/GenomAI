## [v1.3.2] - 2026-01-15

### Changes
- 1ab7376 feat(auth): add /api/auth/telegram endpoint for Telegram Login Widget (#740) (#741)

### Issues
- Closes #740
- Closes #741

---

## [v1.3.1] - 2026-01-15

### Changes
- 85c18cd feat(api): add volatility metrics to /recommendations/stats (#737)
- 61671d1 feat: complete issue #735 (#738)
- dd2e896 fix(migration): rename approve_with_warnings to avoid timestamp conflict
- 90d7155 feat: complete issue #732 (#734)
- 4c9396e feat: complete issue #731 (#733)

### Issues
- Closes #731
- Closes #732
- Closes #733
- Closes #734
- Closes #735
- Closes #737
- Closes #738

---

## [v1.2.0] - 2026-01-13

### Changes
- a152a5b Issue #706: /health/metrics возвращает 404 (#706) (#723)
- bd56548 feat: complete issue #707 (#722)
- 2429741 feat: complete issue #709 (#721)
- d3dcb66 feat: complete issue #711 (#720)
- 203454e feat: complete issue #714 (#719)
- 79e5083 feat: complete issue #710 (#718)
- 3a8a8d2 feat: complete issue #706 (#717)
- a2c78bf feat: complete issue #705 (#716)
- 2634d78 feat: complete issue #713 (#715)
- df82a17 feat: complete issue #694 (#704)
- d7ff3f1 feat: complete issue #693 (#703)
- c8a5cf9 feat: complete issue #698 (#702)
- 5a41c23 feat: complete issue #696 (#700)
- cfe3271 feat: complete issue #697 (#701)

### Issues
- Closes #693
- Closes #694
- Closes #696
- Closes #697
- Closes #698
- Closes #700
- Closes #701
- Closes #702
- Closes #703
- Closes #704
- Closes #705
- Closes #706
- Closes #707
- Closes #709
- Closes #710
- Closes #711
- Closes #713
- Closes #714
- Closes #715
- Closes #716
- Closes #717
- Closes #718
- Closes #719
- Closes #720
- Closes #721
- Closes #722
- Closes #723

---

## [v1.1.4] - 2026-01-13

**4 issues closed**

---

## [v1.1.3] - 2026-01-13

### Changes
- 953d96b feat(telegram): add progress notifications during creative processing (#685)
- 48a42c8 feat: complete issue #676 (#684)
- 3b2da3e feat: complete issue #673 (#683)
- 85f9894 feat(telegram): improve Welcome message with value proposition (#679)
- a44bf7b feat: complete issue #672 (#682)
- 002ff4b feat: complete issue #671 (#681)
- 60e4f72 feat: complete issue #670 (#680)
- 5a3e075 feat: complete issue #598 (#669)
- 8170afd feat: complete issue #604 (#659)
- b74b872 fix(types): use Optional[dict] for Python 3.9 compatibility (#668)
- e7581c7 feat: complete issue #601 (#667)
- c6aadbc feat: complete issue #602 (#656)
- f6ede39 feat: complete issue #599 (#666)
- 000745a fix(temporal): add fail-fast validation for required env vars (#651)
- 214ba3f feat: complete issue #598 (#665)
- 9821822 feat: complete issue #662 (#663)
- 82ebef2 feat: complete issue #597 (#660)
- 1785e32 feat: complete issue #603 (#658)
- 318a0c6 feat: complete issue #600 (#657)
- 37e386f feat: complete issue #575 (#655)
- 3c86b94 Issue #568: Missing env vars validation в temporal/config.p (#568) (#654)
- 124e9b4 feat: complete issue #567 (#653)
- cd644db feat: complete issue #576 (#652)
- d9aa981 feat: complete issue #555 (#650)
- cd462e1 feat: complete issue #587 (#649)
- 367b040 Issue #535: Callback query input injection vulnerability (#535) (#648)
- bdc0a64 feat: complete issue #563 (#647)
- 29ddf2e fix(types): resolve mypy errors across codebase (#646)
- faf1d66 feat: complete issue #564 (#645)
- 72d8701 feat: complete issue #562 (#644)
- cf7ab1f feat: complete issue #554 (#643)
- b54c49d feat: complete issue #548 (#642)
- 2413961 feat: complete issue #552 (#641)
- 0049933 test: update callback_data tests for UUID validation
- 177539a feat: complete issue #546 (#639)
- a2d5ac3 Issue #549: Replace unsafe args unpacking in check_staleness (#549) (#625)
- 94733a3 fix(security): add type-specific validation to callback_data
- da75fd5 feat: complete issue #536 (#637)
- 82f5a91 docs: update L025 lesson - lsof for port detection (#638)
- bf6b333 fix(scripts): detect FastAPI port via lsof (#636)
- 8e043fb docs: add L025 lesson about pid file fallback (#635)
- 5ed11af feat: complete issue #630 (#633)
- 30da949 fix(scripts): add port probing fallback when pid file missing (#634)
- f468d27 feat: complete issue #547 (#632)
- 97bfdfc feat: complete issue #537 (#631)
- c8dc500 feat: complete issue #545 (#629)
- 8931455 feat: complete issue #539 (#627)
- 2347d4b feat: complete issue #540 (#626)
- 5b44bd2 fix(security): add ReDoS protection to URL regex patterns (#624)
- 387a777 fix(telegram): replace broad exception handling with specific RPCError handling (#538) (#622)
- d0cc1c4 feat: complete issue #542 (#621)
- d7ff104 feat: complete issue #543 (#620)
- c4d6cf1 feat: complete issue #558 (#619)
- 7c39d1f feat: complete issue #572 (#618)
- 00f6838 feat: complete issue #559 (#617)
- bdf3544 Issue #560: Unhandled child workflow error types в maintena (#560) (#616)
- 0859987 Issue #579: INSERT операции без ON CONFLICT — � (#579) (#610)
- 16da695 Issue #571: Валидация callback_data в Telegram han (#571) (#614)
- 3b68e2c fix: add max limit validation to API endpoints (#573) (#609)
- e900547 fix(temporal): add error handling for PATCH operations (#551) (#608)
- dba1518 fix(scripts): detect main repo root from worktree context
- 66c9302 feat: complete issue #566
- c795f43 fix(scripts): use nullglob for pid file detection in task-done.sh
- b428db1 feat: complete issue #550 (#605)
- c725e0e chore: run ruff format on entire codebase (#613)
- cbeddf6 fix(lint): add 'from e' to all raise in except blocks + clean up ruff config
- b4079aa fix(scripts): use dynamic FastAPI port in task-done.sh
- 731a76f feat: complete issue #556 (#606)
- b081801 fix(scripts): close issue immediately after CI passes
- 27e175a Revert "docs: add mandatory issue closure rule after CI success"
- e4821b2 feat: complete issue #588 (#607)
- 38a2f83 docs: add mandatory issue closure rule after CI success
- 6ed4e5d feat: add bug prevention system (mypy, ruff rules, workflow improvements)
- 859ff6e fix: prevent ZeroDivisionError in feature_correlation (#583)
- 84af416 Issue #577: N+1 queries в maintenance activities (#577) (#595)
- 0e38fd8 fix(scripts): run qa-notes test in worktree, not PROJECT_ROOT
- e1fa1b3 feat: complete issue #590 (#594)
- 6ee01e0 feat: complete issue #586 (#593)
- 2298c17 feat: complete issue #589 (#592)
- 0a4fc13 fix(temporal): make retry_failed_hypotheses idempotent (#578) (#591)
- dcdc82d docs: add .env.example files for security best practices (#580)
- f59df38 feat: complete issue #574 (#581)
- 76db914 feat: complete issue #557 (#584)
- d845261 feat: complete issue #553
- e65df79 feat: complete issue #534 (#582)
- 31c0bb9 feat: complete issue #553
- 8a04df4 feat: complete issue #553

### Issues
- Closes #534
- Closes #535
- Closes #536
- Closes #537
- Closes #538
- Closes #539
- Closes #540
- Closes #542
- Closes #543
- Closes #545
- Closes #546
- Closes #547
- Closes #548
- Closes #549
- Closes #550
- Closes #551
- Closes #552
- Closes #553
- Closes #554
- Closes #555
- Closes #556
- Closes #557
- Closes #558
- Closes #559
- Closes #560
- Closes #562
- Closes #563
- Closes #564
- Closes #566
- Closes #567
- Closes #568
- Closes #571
- Closes #572
- Closes #573
- Closes #574
- Closes #575
- Closes #576
- Closes #577
- Closes #578
- Closes #579
- Closes #580
- Closes #581
- Closes #582
- Closes #583
- Closes #584
- Closes #585
- Closes #586
- Closes #587
- Closes #588
- Closes #589
- Closes #590
- Closes #591
- Closes #592
- Closes #593
- Closes #594
- Closes #595
- Closes #597
- Closes #598
- Closes #599
- Closes #600
- Closes #601
- Closes #602
- Closes #603
- Closes #604
- Closes #605
- Closes #606
- Closes #607
- Closes #608
- Closes #609
- Closes #610
- Closes #613
- Closes #614
- Closes #615
- Closes #616
- Closes #617
- Closes #618
- Closes #619
- Closes #620
- Closes #621
- Closes #622
- Closes #624
- Closes #625
- Closes #626
- Closes #627
- Closes #629
- Closes #630
- Closes #631
- Closes #632
- Closes #633
- Closes #634
- Closes #635
- Closes #636
- Closes #637
- Closes #638
- Closes #639
- Closes #640
- Closes #641
- Closes #642
- Closes #643
- Closes #644
- Closes #645
- Closes #646
- Closes #647
- Closes #648
- Closes #649
- Closes #650
- Closes #651
- Closes #652
- Closes #653
- Closes #654
- Closes #655
- Closes #656
- Closes #657
- Closes #658
- Closes #659
- Closes #660
- Closes #662
- Closes #663
- Closes #665
- Closes #666
- Closes #667
- Closes #668
- Closes #669
- Closes #670
- Closes #671
- Closes #672
- Closes #673
- Closes #676
- Closes #679
- Closes #680
- Closes #681
- Closes #682
- Closes #683
- Closes #684
- Closes #685

---

## [v1.1.2] - 2026-01-12

### Changes
- f31e2cf feat: complete issue #486 (#532)
- 3ee1a71 docs: document existing E2E testing infrastructure for #529 (#531)
- e4ec09d fix(scripts): complete task-done.sh flow with CI wait, merge, issue close (#530)
- 506b1c1 feat: increase orphan cleanup batch to 500, add error logging (#485) (#528)
- c824790 Closes #483 (#526)
- cd3328a fix(maintenance): add force recovery for stuck creatives > 2h (#481) (#525)
- e07bd25 feat: complete issue #482 (#527)
- f17e513 Heartbeat timeout 60 сек слишком короткий для transcription (#524)
- bbdb273 feat: complete issue #487
- bea497e feat: complete issue #483 (#522)
- 8b11db2 feat: complete issue #476 (#521)
- 2bb0968 feat: increase orphan cleanup batch to 500 with error logging (#485) (#520)
- c5c7408 feat(temporal): add 'failed' status for stuck creatives (#472) (#518)
- da42b91 feat(temporal): add structured logging with trace IDs (#519)
- 28745b5 feat: complete issue #475 (#517)
- 998e170 Closes #471 (#516)
- fb0db56 feat: complete issue #484 (#515)
- c66fe14 fix(temporal): increase heartbeat_timeout from 60s to 5min for transcription (#510)
- 24333d4 feat: complete issue #474 (#513)
- 03bd262 fix(qa-notes): fix test path for issue-473 (#514)
- cf78387 fix: Learning Loop idempotency - prevent duplicate processing (#473) (#512)
- d99c5fa feat: complete issue #479 (#509)
- f369cbe feat: complete issue #468 (#511)
- 60a3fd6 Closes #467 (#508)
- cbfd91f fix: validate --geo flag against VALID_GEOS in /simulate command (#506)
- 2e2e857 docs: require specific functional test before issue completion
- d697b5f docs: add strict warnings about transcript creation rules
- adaf1bb docs: update TRANSCRIPT_WEBHOOK.md with full pipeline documentation
- 0a8e064 Closes #466

### Issues
- Closes #466
- Closes #467
- Closes #468
- Closes #471
- Closes #472
- Closes #473
- Closes #474
- Closes #475
- Closes #476
- Closes #479
- Closes #481
- Closes #482
- Closes #483
- Closes #484
- Closes #485
- Closes #486
- Closes #487
- Closes #506
- Closes #508
- Closes #509
- Closes #510
- Closes #511
- Closes #512
- Closes #513
- Closes #514
- Closes #515
- Closes #516
- Closes #517
- Closes #518
- Closes #519
- Closes #520
- Closes #521
- Closes #522
- Closes #523
- Closes #524
- Closes #525
- Closes #526
- Closes #527
- Closes #528
- Closes #529
- Closes #530
- Closes #531
- Closes #532

---

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.1.1] - 2026-01-12

### Fixed
- BuyerOnboardingInput telegram_id backward compatibility (#505)

---

## [2.0.0] - 2026-01-12

### Temporal Migration & Production Release

Major release marking migration from n8n to Temporal workflow orchestration and full production readiness.

### Added

- **Temporal Workflows** - Complete migration from n8n (#241-#245)
  - CreativePipelineWorkflow - video ingestion to idea
  - LearningLoopWorkflow - market feedback processing
  - KeitaroPollerWorkflow - metrics collection
  - MetricsProcessingWorkflow - outcome aggregation
  - HygieneWorkflow - system health monitoring
- **Modular Creative System** - Hook/Promise/Proof module bank (#377, #380, #382)
- **Knowledge Ingestion** - YouTube transcript extraction and premise learning (#453, #455)
- **Multi-Agent Orchestration** - Agent registry and task queue (#351)
- **Feature Experiments** - Shadow/active/deprecated ML feature lifecycle (#303)
- **Staleness Detection** - Auto-injection of external inspiration when system stales

### Fixed

- 200+ bug fixes across all workflows
- Fatigue versioning in Learning Loop (#237, #240)
- HypothesisDelivered events missing (#223)
- Buyer_id propagation through creative chain (#226)
- Avatar hash length validation (#205)
- Keitaro metrics staleness (#206)
- Decision traces integrity (#207)

### Changed

- **BREAKING**: n8n workflows deprecated, Temporal is now primary orchestrator
- Database schema v1.2.0 with 45+ tables
- 7-phase issue workflow for development
- Schema-first coding enforced

### Infrastructure

- 455 issues resolved
- 127 commits since v1.1.0
- Full E2E test coverage
- Automated worktree management

## [1.1.0] - 2025-12-27

### Buyer Production Release

This release marks the production readiness of the Buyer System with full automation pipeline.

### Added

- **Outcome Service** - Centralized outcome aggregation with `/api/outcomes/aggregate` endpoint (#141-#146)
- **Schema Validator** - JSON Schema validation for LLM outputs with API endpoint (#135-#138)
- **Recommendation Engine** - Smart recommendations with Thompson Sampling exploration (#123, #124)
- **Recommendation Delivery** - n8n workflow for automated Telegram delivery (#125)
- **Component Learning** - Granular learning tracking for creative components (#122)
- **Idea Registry API** - Endpoint with canonical hashing utilities
- **Emergent Avatar System** - Dynamic avatar generation with canonical hash
- **Multi-geo Buyers** - Support for multiple geos and verticals per buyer
- **Geo/Vertical Lookup Tables** - Normalized reference data for geos and verticals

### Fixed

- **Death Memory Check** - Now correctly checks `death_state` instead of `status` (#158)
- **Recommendations Routing** - Reordered routes for correct matching
- **Learning Pipeline** - Removed generated columns from inserts, improved error handling
- **Telegram Bot** - `/help` command now works regardless of conversation state

### Changed

- CI pipeline now runs unit tests on push
- Added Schema-First Coding guidelines to development workflow

### Testing

- 22 unit tests for Outcome Service
- 126 system capabilities documented and verified

## [1.0.0] - 2025-12-26

### Production Ready

Initial production release with complete Decision Engine pipeline.

### Added

- Decision Engine with 4-stage validation (schema, death_memory, fatigue, risk_budget)
- Learning Loop with market feedback integration
- Hypothesis Factory for creative generation
- Video Ingestion pipeline
- Telegram Bot for buyer interaction
- n8n orchestration workflows

## [0.1.0] - 2025-12-25

### Initial Release

- Project scaffolding
- Basic Decision Engine structure
- Supabase schema setup
