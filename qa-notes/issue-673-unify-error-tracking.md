# Issue #673: Unify Error Tracking Across Handlers

## Что изменено

- Добавлена функция `record_handler_error()` для унифицированного трекинга ошибок
- Все 28 handlers теперь используют `record_handler_error()` вместо `logger.error()`
- Ошибки автоматически записываются в `WebhookErrorStats` для мониторинга через `/errors`

### Затронутые handlers:
- `log_buyer_interaction`
- `handle_start_command`
- `handle_stats_command`
- `handle_genome_command`
- `handle_confidence_command`
- `handle_trends_command`
- `handle_simulate_command`
- `handle_drift_command`
- `handle_correlations_command`
- `handle_recommend_command`
- `handle_meta_command`
- `handle_buyers_command`
- `handle_activity_command`
- `handle_chat_history`
- `handle_decisions_command`
- `handle_creatives_command`
- `handle_status_command`
- `handle_errors_command`
- `handle_pending_command`
- `handle_approve_command`
- `handle_reject_command`
- `notify_admins`
- `handle_knowledge_command`
- `handle_document_upload`
- `handle_extraction_approve`
- `handle_extraction_reject`
- `handle_video_url`
- `handle_user_message`

## Test

```bash
curl -sf localhost:10000/webhook/telegram/errors | python3 -c "import sys,json; d=json.load(sys.stdin); print('total_errors:', d.get('total_errors', 0)); print('OK: endpoint works')"
```
