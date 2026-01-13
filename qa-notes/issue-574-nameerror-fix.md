# Issue #574: NameError в creative_pipeline — except без binding

## Что изменено

- Добавлен `as e` к `except Exception` в `creative_pipeline.py:489`
- До: `except Exception:` → NameError при использовании `{e}`
- После: `except Exception as e:` → корректное логирование ошибки

## Test

```bash
grep -n 'except Exception as e:' decision-engine-service/temporal/workflows/creative_pipeline.py | grep 489 && echo 'Fix verified'
```
