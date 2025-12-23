#!/usr/bin/env node

/**
 * Скрипт для создания issues для STEP 07 - Outcome Ingestion
 * Использование: node .github/create_step07_issues.js
 * 
 * Требуется: GITHUB_TOKEN в environment variables
 */

import https from 'https';

const GITHUB_OWNER = 'mosszxc';
const GITHUB_REPO = 'GenomAI';
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;

if (!GITHUB_TOKEN) {
  console.error('❌ Ошибка: GITHUB_TOKEN не установлен в environment variables');
  console.error('Установите токен: export GITHUB_TOKEN=your_token');
  process.exit(1);
}

// Функция для создания issue через GitHub API
function createIssue(title, body, labels = []) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({
      title,
      body,
      labels
    });

    const options = {
      hostname: 'api.github.com',
      path: `/repos/${GITHUB_OWNER}/${GITHUB_REPO}/issues`,
      method: 'POST',
      headers: {
        'Authorization': `token ${GITHUB_TOKEN}`,
        'User-Agent': 'Node.js',
        'Content-Type': 'application/json',
        'Content-Length': data.length,
        'Accept': 'application/vnd.github.v3+json'
      }
    };

    const req = https.request(options, (res) => {
      let responseData = '';

      res.on('data', (chunk) => {
        responseData += chunk;
      });

      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          const issue = JSON.parse(responseData);
          resolve(issue);
        } else {
          reject(new Error(`HTTP ${res.statusCode}: ${responseData}`));
        }
      });
    });

    req.on('error', (error) => {
      reject(error);
    });

    req.write(data);
    req.end();
  });
}

// Epic #7
const epic7 = {
  title: 'Epic #7: STEP 07 — Outcome Ingestion (MVP)',
  body: `# Epic #7: STEP 07 — Outcome Ingestion (MVP)

**Статус:** 🟡 IN PROGRESS  
**Scope:** MVP  
**Зависимости:** STEP 06 (telegram_output_playbook) ✅  
**Следующий шаг:** STEP 08 (learning_loop_playbook)

## 📋 Назначение

Реализация outcome ingestion для получения метрик из Keitaro API и сохранения их в БД.

Этот шаг фиксирует реальность. Outcome ingestion отвечает не на вопрос "почему", а только на вопрос "что произошло".

На этом этапе:
- нет learning
- нет интерпретаций
- нет решений

## 🎯 Workflow

**Workflow:** \`Outcome Ingestion Keitaro\` (ID: \`zMHVFT2rM7PpTiJj\`)  
**Статус:** Создан, требует тестирования

## 📚 Ссылки

- [Playbook: 07_outcome_ingestion_playbook.md](docs/layer-4-implementation-planning/STEP_IMPLEMENTATION_PLAYBOOKS/07_outcome_ingestion_playbook.md)

## ✅ Готовность к началу

**Все зависимости выполнены:** ✅  
**Готов к началу работы:** ✅`,
  labels: ['epic', 'step-07', 'outcome-ingestion']
};

// Issue 1: Тестирование workflow
const issue1 = {
  title: '[STEP 07] Тестирование workflow Outcome Ingestion Keitaro',
  body: `# Тестирование workflow Outcome Ingestion Keitaro

**Epic:** #7  
**Приоритет:** High  
**Тип:** Task

## Описание

Протестировать workflow \`Outcome Ingestion Keitaro\` (ID: \`zMHVFT2rM7PpTiJj\`) и убедиться, что все узлы работают корректно.

## Чеклист

- [ ] Запустить workflow через Manual Trigger
- [ ] Проверить, что все узлы выполняются без ошибок
- [ ] Проверить, что данные корректно передаются между узлами
- [ ] Проверить, что SplitInBatches connections правильные (output 1 для loop, output 0 для done)
- [ ] Проверить, что обработка ошибок работает (пропуск кампаний без данных)
- [ ] Проверить, что события эмитятся корректно

## Ожидаемый результат

- Workflow выполняется без ошибок
- Все узлы работают корректно
- Данные передаются между узлами правильно

## Связанные файлы

- \`docs/layer-4-implementation-planning/STEP_IMPLEMENTATION_PLAYBOOKS/07_outcome_ingestion_playbook.md\``,
  labels: ['step-07', 'testing', 'high-priority']
};

// Issue 2: Проверка данных в БД
const issue2 = {
  title: '[STEP 07] Проверка данных в БД после выполнения workflow',
  body: `# Проверка данных в БД после выполнения workflow

**Epic:** #7  
**Приоритет:** High  
**Тип:** Task

## Описание

Проверить, что данные корректно сохраняются в БД после выполнения workflow.

## Чеклист

### raw_metrics_current
- [ ] Записи создаются/обновляются для каждого \`tracker_id\`
- [ ] Поле \`date\` содержит вчерашнюю дату
- [ ] Поле \`metrics\` содержит корректные данные (clicks, conversions, revenue, cost)
- [ ] Поле \`updated_at\` обновляется при изменении

### daily_metrics_snapshot
- [ ] Snapshot создается для каждого \`tracker_id\` с данными
- [ ] Поле \`date\` содержит вчерашнюю дату
- [ ] Поле \`metrics\` содержит корректные данные
- [ ] Unique constraint \`(tracker_id, date)\` работает (нет дубликатов)

### event_log
- [ ] Событие \`RawMetricsObserved\` создается после сохранения raw metrics
- [ ] Событие \`DailyMetricsSnapshotCreated\` создается после создания snapshot
- [ ] Payload событий содержит корректные данные

## Запросы для проверки

\`\`\`sql
-- Проверить raw_metrics_current
SELECT tracker_id, date, metrics, updated_at 
FROM genomai.raw_metrics_current 
ORDER BY updated_at DESC 
LIMIT 10;

-- Проверить daily_metrics_snapshot
SELECT tracker_id, date, metrics, created_at 
FROM genomai.daily_metrics_snapshot 
ORDER BY created_at DESC 
LIMIT 10;

-- Проверить события
SELECT event_type, entity_type, entity_id, payload, occurred_at 
FROM genomai.event_log 
WHERE event_type IN ('RawMetricsObserved', 'DailyMetricsSnapshotCreated')
ORDER BY occurred_at DESC 
LIMIT 10;
\`\`\`

## Ожидаемый результат

- Данные корректно сохраняются в БД
- Все таблицы содержат ожидаемые данные
- События эмитятся корректно`,
  labels: ['step-07', 'database', 'high-priority']
};

// Issue 3: Валидация playbook
const issue3 = {
  title: '[STEP 07] Валидация соответствия playbook и проверка ручных тестов',
  body: `# Валидация соответствия playbook и проверка ручных тестов

**Epic:** #7  
**Приоритет:** Medium  
**Тип:** Task

## Описание

Проверить, что workflow соответствует playbook и пройти все ручные проверки.

## Чеклист согласно playbook

### Check 1 — Happy path
- [ ] Schedule Trigger работает (cron: \`0 3 * * *\`)
- [ ] Workflow выполняется автоматически
- [ ] Snapshot появляется в \`daily_metrics_snapshot\`
- [ ] Raw metrics обновляются в \`raw_metrics_current\`

### Check 2 — Missing data
- [ ] Keitaro вернул пустой ответ для некоторых кампаний
- [ ] Workflow не падает при отсутствии данных
- [ ] Кампании без данных пропускаются корректно
- [ ] Workflow продолжает обработку других кампаний

### Check 3 — Retry safety
- [ ] Повторный запуск workflow (через cron или manual trigger)
- [ ] Duplicate snapshot не создается (unique constraint работает)
- [ ] Raw metrics обновляются корректно при повторном запуске
- [ ] Idempotency работает (можно запускать несколько раз без дубликатов)

## Проверка соответствия playbook
- [ ] Workflow соответствует структуре из playbook
- [ ] Все узлы реализованы согласно playbook
- [ ] События эмитятся согласно playbook
- [ ] Нет запрещенных действий (learning, интерпретация, оптимизация, decision)

## Ожидаемый результат

- Все проверки из playbook пройдены
- Workflow соответствует playbook
- Готовность к переходу к STEP 08`,
  labels: ['step-07', 'validation', 'playbook']
};

// Issue 4: Проверка конфигурации
const issue4 = {
  title: '[STEP 07] Проверка конфигурации Keitaro',
  body: `# Проверка конфигурации Keitaro

**Epic:** #7  
**Приоритет:** Medium  
**Тип:** Task

## Описание

Проверить, что конфигурация Keitaro настроена корректно в БД.

## Чеклист

- [ ] Проверить таблицу \`genomai.keitaro_config\`:
  - [ ] Есть активная конфигурация (\`is_active = true\`)
  - [ ] Поле \`domain\` содержит корректный URL Keitaro
  - [ ] Поле \`api_key\` содержит корректный API ключ
  - [ ] Только одна активная конфигурация существует
- [ ] Проверить, что workflow корректно загружает конфигурацию
- [ ] Проверить, что API запросы к Keitaro используют правильные credentials

## Запросы для проверки

\`\`\`sql
-- Проверить конфигурацию
SELECT id, domain, is_active, created_at, updated_at 
FROM genomai.keitaro_config 
WHERE is_active = true;
\`\`\`

## Ожидаемый результат

- Конфигурация настроена корректно
- Workflow корректно загружает конфигурацию
- API запросы к Keitaro работают`,
  labels: ['step-07', 'configuration']
};

// Основная функция
async function main() {
  console.log('🚀 Создание issues для STEP 07...\n');

  try {
    // Создаем Epic #7
    console.log('📋 Создание Epic #7...');
    const epic = await createIssue(epic7.title, epic7.body, epic7.labels);
    console.log(`✅ Epic создан: #${epic.number} - ${epic.title}`);
    console.log(`   URL: ${epic.html_url}\n`);

    const epicNumber = epic.number;

    // Обновляем body issues с номером Epic
    issue1.body = issue1.body.replace('**Epic:** #7', `**Epic:** #${epicNumber}`);
    issue2.body = issue2.body.replace('**Epic:** #7', `**Epic:** #${epicNumber}`);
    issue3.body = issue3.body.replace('**Epic:** #7', `**Epic:** #${epicNumber}`);
    issue4.body = issue4.body.replace('**Epic:** #7', `**Epic:** #${epicNumber}`);

    // Создаем Issue 1
    console.log('📝 Создание Issue 1: Тестирование workflow...');
    const issue1Created = await createIssue(issue1.title, issue1.body, issue1.labels);
    console.log(`✅ Issue создан: #${issue1Created.number} - ${issue1Created.title}`);
    console.log(`   URL: ${issue1Created.html_url}\n`);

    // Создаем Issue 2
    console.log('📝 Создание Issue 2: Проверка данных в БД...');
    const issue2Created = await createIssue(issue2.title, issue2.body, issue2.labels);
    console.log(`✅ Issue создан: #${issue2Created.number} - ${issue2Created.title}`);
    console.log(`   URL: ${issue2Created.html_url}\n`);

    // Создаем Issue 3
    console.log('📝 Создание Issue 3: Валидация playbook...');
    const issue3Created = await createIssue(issue3.title, issue3.body, issue3.labels);
    console.log(`✅ Issue создан: #${issue3Created.number} - ${issue3Created.title}`);
    console.log(`   URL: ${issue3Created.html_url}\n`);

    // Создаем Issue 4
    console.log('📝 Создание Issue 4: Проверка конфигурации...');
    const issue4Created = await createIssue(issue4.title, issue4.body, issue4.labels);
    console.log(`✅ Issue создан: #${issue4Created.number} - ${issue4Created.title}`);
    console.log(`   URL: ${issue4Created.html_url}\n`);

    console.log('✅ Все issues успешно созданы!');
    console.log(`\n📊 Итого:`);
    console.log(`   - Epic: #${epicNumber}`);
    console.log(`   - Issues: #${issue1Created.number}, #${issue2Created.number}, #${issue3Created.number}, #${issue4Created.number}`);

  } catch (error) {
    console.error('❌ Ошибка при создании issues:', error.message);
    process.exit(1);
  }
}

main();

