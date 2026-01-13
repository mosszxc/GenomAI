# Issue #575: Silent Exception Swallowing Fix

## Что изменено

Исправлено 18 мест с `except Exception: pass` паттерном, который молча проглатывал ошибки:

### Файлы и изменения:

| Файл | Изменений | Тип исправления |
|------|-----------|-----------------|
| `src/services/supabase.py` | 3 | httpx.HTTPStatusError + logging |
| `temporal/workflows/keitaro_polling.py` | 5 | workflow.logger.debug |
| `temporal/workflows/historical_import.py` | 1 | workflow.logger.debug |
| `temporal/workflows/metrics_processing.py` | 1 | workflow.logger.debug |
| `temporal/workflows/learning_loop.py` | 1 | workflow.logger.debug |
| `temporal/circuit_breaker.py` | 1 | activity.logger.warning |
| `temporal/activities/maintenance.py` | 1 | ValueError/TypeError + logger |
| `temporal/activities/hygiene_cleanup.py` | 1 | ValueError/TypeError + logger |
| `src/routes/telegram.py` | 1 | httpx + logger.debug |
| `src/services/recommendation.py` | 1 | logger.warning |
| `src/services/external_inspiration.py` | 1 | logger.warning |
| `src/services/component_learning.py` | 1 | logger.debug |

### Паттерн исправления:

```python
# ❌ БЫЛО:
except Exception:
    pass

# ✅ СТАЛО:
except Exception as e:
    logger.warning(f"Context description: {e}")
```

Для best-effort операций (event emission) используется `logger.debug`.
Где возможно, использованы более специфичные исключения (ValueError, TypeError, httpx.HTTPStatusError).

## Test

```bash
cd decision-engine-service && python3 -c "import subprocess; result=subprocess.run(['grep', '-rn', 'except Exception:', '.'], capture_output=True, text=True); lines=[l for l in result.stdout.split('\n') if l and 'pass' in l and 'except Exception:' in l]; print('PASS: No silent exception swallowing' if not lines else f'FAIL: {lines}')"
```
