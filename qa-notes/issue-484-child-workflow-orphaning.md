# Issue #484: Child workflow orphaning при cancel parent

## Что изменено

Добавлен `parent_close_policy=workflow.ParentClosePolicy.TERMINATE` ко всем child workflow вызовам:

- `historical_import.py:294` - CreativeRegistrationWorkflow → CreativePipelineWorkflow
- `historical_import.py:470` - HistoricalVideoHandlerWorkflow → CreativePipelineWorkflow
- `premise_extraction.py:226` - BatchPremiseExtractionWorkflow → PremiseExtractionWorkflow
- `buyer_onboarding.py:530` - BuyerOnboardingWorkflow → HistoricalImportWorkflow
- `buyer_onboarding.py:632` - BuyerOnboardingWorkflow → CreativeRegistrationWorkflow (start_child_workflow)

## Проблема

Child workflows продолжали работать как orphans когда parent workflow был cancelled. По умолчанию Temporal использует `ABANDON` policy, что приводило к:
- Child workflows работающим в background без visibility
- Orphaned processes потребляющим ресурсы
- Нет трассируемости completion

## Решение

Явно указан `ParentClosePolicy.TERMINATE` для всех child workflow вызовов. Теперь при cancel/close parent workflow все child workflows также будут terminated.

## Test

```bash
python3 -m py_compile decision-engine-service/temporal/workflows/historical_import.py decision-engine-service/temporal/workflows/buyer_onboarding.py decision-engine-service/temporal/workflows/premise_extraction.py && echo "OK: syntax valid"
```
