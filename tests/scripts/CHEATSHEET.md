# Шпаргалка: Автоматизация тестирования n8n Workflows

## 🚀 Быстрый старт (3 шага)

### 1. В Issue добавьте комментарий:
```
/test-workflow workflow-id
```

### 2. Запустите workflow в n8n UI:
- Откройте workflow
- Нажмите Manual Trigger → Execute Node

### 3. Готово!
Результаты автоматически появятся в Issue

## 📋 Формат комментария

```
/test-workflow mv6diVtqnuwr7qev
```

## 🎯 Примеры

### Для Issue #22 (STEP 03):
```
/test-workflow cGSyJPROrkqLVHZP
```

### Для STEP 02:
```
/test-workflow mv6diVtqnuwr7qev
```

## ⚙️ Настройка (один раз)

1. GitHub Settings → Secrets → Actions
2. New secret: `N8N_API_KEY`
3. Значение: API ключ из n8n (Settings → API → Create API Key)

## 💡 Преимущества

- ✅ Не нужно постоянно проверять последний execution
- ✅ Все результаты в Issue
- ✅ Экономия времени (70 сек → 10 сек)
- ✅ История тестирования сохраняется

## 📚 Подробнее

- [HOW_TO_USE.md](./HOW_TO_USE.md) — Как использовать в workflow
- [QUICK_START.md](./QUICK_START.md) — Быстрый старт

