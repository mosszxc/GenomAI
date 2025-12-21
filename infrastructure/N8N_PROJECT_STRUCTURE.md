# n8n Project Structure - Unighaz

**Версия:** v1.0  
**Статус:** ACTIVE  
**Проект:** Unighaz

## 📋 Обзор

Все новые workflow для GenomAI создаются в проекте **Unighaz** в n8n.

## 🏷️ Структура именования

### Актуальные workflow (новые, для GenomAI)
- **Без префикса** - просто актуальные workflow
- Все новые workflow находятся в проекте **Unighaz**
- Примеры:
  - `Test Supabase Connection`
  - `Creative Ingestion Webhook` (будущий)
  - `Daily Metrics Scan` (будущий)

### Legacy workflow (старые)
- Префикс: `Legacy -`
- Все старые workflow переименованы с префиксом "Legacy -"
- Эти workflow не используются в новой архитектуре GenomAI

## 📁 Организация workflow

### В проекте Unighaz:

**Актуальные Workflows (новые):**
- `Test Supabase Connection` (ID: `cpaFx4dhT5gQBB4C`)
- (другие будут добавлены по мере разработки)

**Legacy Workflows (помечены, но не используются):**
- `Legacy - Telegram Daily Messages Summary`
- `Legacy - Performance Metrics Collector`
- `Legacy - UniAI - Router Workflow` (множество копий)
- `Legacy - Keitaro Daily Sync`
- `Legacy - creative_ingestion_webhook`
- И другие старые workflow...

## 🎯 Правила работы

1. **Все новые workflow для GenomAI** создаются в проекте **Unighaz**
2. **Именование:** Новые workflow **без префикса** - просто актуальные названия
3. **Legacy workflow:** Не удаляем, но не используем. Помечены префиксом `Legacy -`
4. **Активные workflow:** Только новые актуальные workflow могут быть активными

## 📝 Примеры именования

### Правильно (новые актуальные):
- ✅ `Test Supabase Connection`
- ✅ `Creative Ingestion Webhook`
- ✅ `Daily Metrics Scan`
- ✅ `Learning Loop`
- ✅ `Hypothesis Generation`

### Неправильно:
- ❌ `GenomAI - Test Connection` (не нужен префикс)
- ❌ `Legacy - ...` (только для старых)
- ❌ `UniAI - ...` (старый префикс, должен быть Legacy)

## 🔍 Поиск workflow

В n8n Dashboard:
1. Перейдите в проект **Unighaz**
2. **Актуальные workflow:** Все workflow **без префикса** в проекте Unighaz
3. **Legacy workflow:** Фильтруйте по префиксу `Legacy -` для поиска старых workflow

## 📊 Статистика

- **Актуальных workflow (новые):** 1 (пока)
- **Legacy workflow:** ~55 (помечены префиксом "Legacy -")
- **Проект:** Unighaz

## 🎯 Следующие шаги

При создании новых workflow для GenomAI:
1. Убедитесь, что вы в проекте **Unighaz**
2. **Не используйте префиксы** - просто актуальное название
3. Следуйте структуре из playbooks (STEP 01-08)
4. Старые workflow помечайте префиксом `Legacy -`

