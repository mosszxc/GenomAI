# Dependency Graph

Визуализация зависимостей между workflows, API и таблицами БД.

**Auto-generated from:** n8n API
**Last updated:** 2025-12-27 01:26

---

## Workflow Call Graph

```mermaid
flowchart TD

    %% Auto-generated from n8n workflows
    %% Updated: 2025-12-27 01:26

    subgraph Telegram["Telegram Entry Points"]
        legacyuniairout[legacy___uniai___router_workflow_(imported)]
        legacyuniairout[legacy___uniai___router_test_1]
        legacyuniairout[legacy___uniai___router_workflow]
        myworkflow[my_workflow]
        legacyroutermai[legacy___router___main]
        buyerhistorical[buyer_historical_url_handler]
        telegramrouter[telegram_router]
        legacydota2hero[legacy___dota_2_hero_picker___main_workflow]
        telegramcreativ[telegram_creative_ingestion]
        legacydota2hero[legacy___dota_2_hero_picker___pool_management]
        legacyuniairout[legacy___uniai___router_workflow_(copy)]
        historicalimpor[historical_import_video_handler]
        buyercreativere[buyer_creative_registration]
        legacymyworkflo[legacy___my_workflow]
        legacyregisterc[legacy___register_creative_via_telegram]
        buyeronboarding[buyer_onboarding]
        legacyregisterc[legacy___register_creative_via_telegram_(new)]
        legacydota2hero[legacy___dota_2_hero_picker___side_selection]
        legacyuniairout[legacy___uniai___router_workflow_copy]
        buyerstatscomma[buyer_stats_command]
        legacytrendwatc[legacy___trendwatcher_reels_mvp_v2_(fixed)]
        legacytrendwatc[legacy___trendwatcher_reels_mvp_v2_(fixed)_copy1123123123]
        legacyregisterc[legacy___register_creative_via_telegram_(optimized)]
    end

    subgraph Scheduled["Scheduled Jobs"]
        legacytelegramd[legacy___telegram_daily_messages_summary]
        keitaropoller[keitaro_poller]
        performancemetr[performance_metrics_collector]
        keepalivedecisi[keep_alive_decision_engine]
        legacykeitaroda[legacy___keitaro_daily_sync]
        buyerdailydiges[buyer_daily_digest]
        legacy1register[legacy___1___register_new_creative___scan_google_drive]
        legacyregistern[legacy___register_new_creative___scan_google_drive_v2]
        legacykeitarome[legacy___keitaro_metrics_daily_sync]
        legacykeitaro30[legacy___keitaro_30d_metrics_sync_(new)]
        dailyrecommenda[daily_recommendation_generator]
        outcomeingestio[outcome_ingestion_keitaro]
    end

    %% Workflow calls
    keitaropoller --> snapshotcreator
    keitaropoller --> buyer
    historicalcreat --> learningloop
    historicalcreat --> creativetranscr
    buyerhistorical --> historicalimpor
    zalivsessionhan --> creativetranscr
    creativereplyha --> creativetranscr
    buyerhistorical --> historicalimpor
    telegramrouter --> router
    snapshotcreator --> outcomeaggregat
    snapshotcreator --> outcomeprocesso
    telegramcreativ --> ingest
    historicalimpor --> historicalimpor
    idearegistrycre --> 8a0b9e75a8eb449
    buyercreativere --> decompose
    creativeingesti --> a1b2c3d4e5f6789
    buyeronboarding --> buyerhistorical
    creativedecompo --> idearegistrycre
    spycreativeregi --> decompose
    spycreativeregi --> creativetranscr
    dailyrecommenda --> recommendationd
```

---

See `infrastructure/schemas/dependency_manifest.json` for full details.
