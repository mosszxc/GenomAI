# GenomAI — Testing & Preparation

**Версия:** v1.0  
**Статус:** ACTIVE  
**Ответственный:** Агент 3 — Подготовка и тесты

## 📋 Обзор

Этот каталог содержит:
- Тестовые payload'ы для всех сценариев
- Тестовые скрипты для автоматизации проверок
- Документацию API/webhook контрактов
- Шаблоны конфигурационных файлов

## 📁 Структура

```
tests/
├── README.md                    # Этот файл
├── payloads/                    # Тестовые payload'ы
│   ├── ingestion/               # Payload'ы для STEP 01 (Ingestion)
│   │   ├── happy_path.json
│   │   ├── idempotency.json
│   │   ├── invalid_missing_fields.json
│   │   ├── invalid_empty_fields.json
│   │   ├── invalid_wrong_source_type.json
│   │   ├── edge_same_video_different_tracker.json
│   │   └── garbage_input.json
│   └── README.md               # Описание сценариев
├── scripts/                     # Тестовые скрипты
│   ├── test_ingestion.sh        # Bash скрипт для тестирования ingestion
│   ├── test_ingestion.js        # Node.js скрипт (альтернатива)
│   └── README.md                # Инструкции по использованию
├── docs/                        # Документация контрактов
│   ├── API_CONTRACTS.md         # Детальная документация API
│   └── WEBHOOK_GUIDE.md         # Руководство по webhook'ам
└── config/                      # Шаблоны конфигурации
    ├── .env.example             # Пример .env файла
    └── n8n_config.example.json  # Пример конфигурации n8n
```

## 🎯 Тестовые сценарии

### STEP 01 — Ingestion

#### ✅ Happy Path
- Валидный payload с корректными данными
- Ожидается: creative создан, события записаны

#### 🔄 Idempotency
- Повторный ingestion одного и того же креатива
- Ожидается: дубль не создаётся, возвращается существующий creative_id

#### ⚠️ Edge Cases
- Один video_url, разные tracker_id → должны создаться разные creatives
- Разные video_url, один tracker_id → должны создаться разные creatives

#### ❌ Invalid Input
- Отсутствующие обязательные поля
- Пустые строки в обязательных полях
- Неверный source_type (не "user")
- Мусорный JSON

## 🚀 Быстрый старт

### 1. Тестирование Ingestion

```bash
# Использование bash скрипта
./scripts/test_ingestion.sh

# Или через Node.js
node scripts/test_ingestion.js
```

### 2. Ручное тестирование

```bash
# Happy path
curl -X POST http://your-n8n-webhook/ingest/creative \
  -H "Content-Type: application/json" \
  -d @tests/payloads/ingestion/happy_path.json

# Idempotency check
curl -X POST http://your-n8n-webhook/ingest/creative \
  -H "Content-Type: application/json" \
  -d @tests/payloads/ingestion/idempotency.json
```

## 📚 Документация

- [API Contracts](./docs/API_CONTRACTS.md) — Детальная документация всех API контрактов
- [Webhook Guide](./docs/WEBHOOK_GUIDE.md) — Руководство по работе с webhook'ами
- [Payload Scenarios](./payloads/README.md) — Описание всех тестовых сценариев

## ⚙️ Конфигурация

Скопируйте `.env.example` в `.env` и заполните значениями:

```bash
cp tests/config/.env.example .env
```

## 📝 Примечания

- Все тесты должны быть идемпотентными
- Тесты не должны изменять production данные
- Используйте тестовые credentials для n8n
- Проверяйте event_log после каждого теста


