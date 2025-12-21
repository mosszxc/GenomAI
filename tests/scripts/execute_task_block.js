#!/usr/bin/env node

/**
 * GenomAI — Execute Task Block (Complete Block Execution)
 * Версия: v1.0
 * Назначение: Выполнение блока задач (Epic/Issues) с автоматическим тестированием и исправлением до конца
 * 
 * Использование:
 *   node execute_task_block.js <epic-number>
 *   node execute_task_block.js <issue-number> <issue-number> ...
 *   node execute_task_block.js "STEP 04"
 */

const https = require('https');
const http = require('http');
const { fixAndTestLoop, analyzeErrors, fixErrors } = require('./fix_and_test_workflow.js');
const { getIssue, extractWorkflowId, addComment } = require('./test_workflow_from_issue.js');
const { testWorkflow, getLastExecution } = require('./test_n8n_workflow.js');

// Конфигурация
const GITHUB_TOKEN = process.env.GITHUB_TOKEN || '';
const GITHUB_OWNER = process.env.GITHUB_OWNER || 'mosszxc';
const GITHUB_REPO = process.env.GITHUB_REPO || 'GenomAI';
const MAX_ITERATIONS_PER_TASK = parseInt(process.env.MAX_ITERATIONS_PER_TASK || '10', 10);
const AUTO_FIX_ENABLED = process.env.AUTO_FIX !== 'false';

// Цвета
const colors = {
    reset: '\x1b[0m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    cyan: '\x1b[36m',
    magenta: '\x1b[35m',
};

function log(level, message) {
    const prefix = {
        info: `${colors.blue}[INFO]${colors.reset}`,
        success: `${colors.green}[PASS]${colors.reset}`,
        error: `${colors.red}[FAIL]${colors.reset}`,
        warning: `${colors.yellow}[WARN]${colors.reset}`,
        debug: `${colors.cyan}[DEBUG]${colors.reset}`,
        header: `${colors.magenta}[HEADER]${colors.reset}`,
    }[level];
    console.log(`${prefix} ${message}`);
}

// HTTP request helper
function makeRequest(url, options = {}) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const isHttps = urlObj.protocol === 'https:';
        const client = isHttps ? https : http;
        
        const defaultOptions = {
            hostname: urlObj.hostname,
            port: urlObj.port || (isHttps ? 443 : 80),
            path: urlObj.pathname + urlObj.search,
            method: options.method || 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `token ${GITHUB_TOKEN}`,
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'GenomAI-Task-Block-Executor',
                ...options.headers,
            },
        };

        const req = client.request(defaultOptions, (res) => {
            let body = '';
            res.on('data', (chunk) => {
                body += chunk;
            });
            res.on('end', () => {
                let parsedBody;
                try {
                    parsedBody = body ? JSON.parse(body) : {};
                } catch (e) {
                    parsedBody = { raw: body };
                }
                
                resolve({
                    statusCode: res.statusCode,
                    body: parsedBody,
                    headers: res.headers,
                });
            });
        });

        req.on('error', (error) => {
            reject(error);
        });

        if (options.body) {
            req.write(JSON.stringify(options.body));
        }
        
        req.setTimeout(30000, () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });
        
        req.end();
    });
}

// Получить Issue
async function getIssueFromAPI(issueNumber) {
    try {
        const response = await makeRequest(
            `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/issues/${issueNumber}`
        );
        if (response.statusCode === 200) {
            return response.body;
        }
        if (response.statusCode === 404) {
            return null; // Issue не существует
        }
        throw new Error(`HTTP ${response.statusCode}: ${JSON.stringify(response.body)}`);
    } catch (error) {
        if (error.message.includes('404')) {
            return null;
        }
        log('error', `Ошибка при получении Issue #${issueNumber}: ${error.message}`);
        throw error;
    }
}

// Создать Issue
async function createIssue(title, body, labels = []) {
    try {
        const response = await makeRequest(
            `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/issues`,
            {
                method: 'POST',
                body: {
                    title,
                    body,
                    labels,
                },
            }
        );
        if (response.statusCode === 201) {
            return response.body;
        }
        throw new Error(`HTTP ${response.statusCode}: ${JSON.stringify(response.body)}`);
    } catch (error) {
        log('error', `Ошибка при создании Issue: ${error.message}`);
        throw error;
    }
}

// Поиск Epic по названию (например, "STEP 04")
async function findEpicByName(stepName) {
    log('info', `Поиск Epic по названию: "${stepName}"`);
    
    // Ищем Issues с названием, содержащим stepName
    const searchQuery = `repo:${GITHUB_OWNER}/${GITHUB_REPO} is:issue "${stepName}" in:title`;
    const encodedQuery = encodeURIComponent(searchQuery);
    
    try {
        const response = await makeRequest(
            `https://api.github.com/search/issues?q=${encodedQuery}&per_page=10`
        );
        
        if (response.statusCode === 200 && response.body.items) {
            // Ищем Epic (обычно содержит "Epic" в названии)
            const epic = response.body.items.find(item => 
                item.title.toLowerCase().includes('epic') && 
                item.title.toLowerCase().includes(stepName.toLowerCase())
            );
            
            if (epic) {
                log('success', `Найден Epic #${epic.number}: ${epic.title}`);
                return epic;
            }
        }
        
        return null;
    } catch (error) {
        log('warning', `Ошибка при поиске Epic: ${error.message}`);
        return null;
    }
}

// Создать Epic на основе STEP
async function createEpicForStep(stepName, stepNumber) {
    log('info', `Создание Epic для ${stepName}...`);
    
    // Определяем название и описание на основе stepNumber
    const stepInfo = {
        '01': { name: 'Ingestion + Validation', description: 'Приём и валидация creative' },
        '02': { name: 'Decomposition', description: 'Разложение creative на структурированные данные' },
        '03': { name: 'Idea Registry', description: 'Регистрация идей' },
        '04': { name: 'Decision Engine (MVP)', description: 'Детерминированный фильтр допустимости' },
        '05': { name: 'Hypothesis Factory', description: 'Генерация гипотез' },
        '06': { name: 'Delivery', description: 'Доставка гипотез' },
        '07': { name: 'Outcome Aggregation', description: 'Агрегация результатов' },
        '08': { name: 'Learning Loop', description: 'Обучение системы' },
    };
    
    const info = stepInfo[stepNumber] || { name: stepName, description: `Реализация ${stepName}` };
    
    const title = `Epic #${stepNumber}: ${stepName} — ${info.name}`;
    const body = `# Epic #${stepNumber}: ${stepName} — ${info.name}

**Статус:** 🟡 IN PROGRESS  
**Scope:** MVP  
**Зависимости:** STEP ${String(parseInt(stepNumber) - 1).padStart(2, '0')} ✅  
**Следующий шаг:** STEP ${String(parseInt(stepNumber) + 1).padStart(2, '0')}

## 📋 Назначение

${info.description}

## 🎯 Issues в этом Epic (порядок исполнения)

**Порядок выполнения:**

1. **Database Schema** - Создание таблиц
2. **n8n Workflow** - Создание workflow
3. **Event Logging** - Реализация событий
4. **Testing & Validation** - Финальное тестирование

## 📚 Ссылки

- [Playbook: ${stepNumber.padStart(2, '0')}_playbook.md](../../STEP_IMPLEMENTATION_PLAYBOOKS/${stepNumber.padStart(2, '0')}_playbook.md)

## ✅ Готовность к началу

**Все зависимости выполнены:** ✅  
**Готов к началу работы:** ✅`;

    const epic = await createIssue(title, body, ['epic']);
    log('success', `Epic создан: #${epic.number}`);
    return epic;
}

// Создать Issues для Epic на основе playbook
async function createIssuesForEpic(epicNumber, stepNumber) {
    log('info', `Создание Issues для Epic #${epicNumber}...`);
    
    const issues = [];
    const createdIssueNumbers = [];
    
    // Стандартная структура Issues для каждого STEP
    const issueTemplates = [
        {
            order: 1,
            title: `[STEP ${stepNumber}] 1️⃣ Database Schema: создание таблиц`,
            body: (prevIssueNum) => `# 1️⃣ Database Schema: создание таблиц

**Epic:** #${epicNumber}  
**Порядок:** 1/4 (первый шаг)  
**Статус:** 🟡 PENDING  
**Блокирует:** Следующие Issues

## Задача

Создать необходимые таблицы в схеме \`genomai\` для STEP ${stepNumber}.

## Требования

- [ ] Создать таблицы в схеме \`genomai\`
- [ ] Добавить constraints (CHECK, NOT NULL, UNIQUE)
- [ ] Добавить индексы
- [ ] Протестировать создание записей

## Зависимости

- ⚠️ **Блокирует:** Следующие Issues
- ✅ **Можно начинать:** сразу

## Ссылки

- [Playbook: ${stepNumber.padStart(2, '0')}_playbook.md](../../STEP_IMPLEMENTATION_PLAYBOOKS/${stepNumber.padStart(2, '0')}_playbook.md)
- [Epic: #${epicNumber}](../../issues/${epicNumber})`,
        },
        {
            order: 2,
            title: `[STEP ${stepNumber}] 2️⃣ n8n Workflow: создание workflow`,
            body: (prevIssueNum) => `# 2️⃣ n8n Workflow: создание workflow

**Epic:** #${epicNumber}  
**Порядок:** 2/4  
**Статус:** 🟡 PENDING  
**Блокируется:** #${prevIssueNum || '1'}  
**Блокирует:** Следующий Issue

## Задача

Создать n8n workflow для STEP ${stepNumber}.

## Требования

- [ ] Создать workflow в n8n
- [ ] Настроить все узлы
- [ ] Настроить схему \`genomai\` для всех Supabase nodes
- [ ] Протестировать workflow

## Зависимости

- ⚠️ **Блокируется:** Database Schema (#${prevIssueNum || '1'})
- ⚠️ **Блокирует:** Event Logging

## Ссылки

- [Playbook: ${stepNumber.padStart(2, '0')}_playbook.md](../../STEP_IMPLEMENTATION_PLAYBOOKS/${stepNumber.padStart(2, '0')}_playbook.md)
- [Epic: #${epicNumber}](../../issues/${epicNumber})`,
        },
        {
            order: 3,
            title: `[STEP ${stepNumber}] 3️⃣ Event Logging: реализация событий`,
            body: (prevIssueNum) => `# 3️⃣ Event Logging: реализация событий

**Epic:** #${epicNumber}  
**Порядок:** 3/4  
**Статус:** 🟡 PENDING  
**Блокируется:** #${prevIssueNum || '2'}  
**Блокирует:** Следующий Issue

## Задача

Реализовать запись событий в \`event_log\` для STEP ${stepNumber}.

## Требования

- [ ] Настроить запись события в \`event_log\`
- [ ] Реализовать все обязательные события
- [ ] Протестировать запись события

## Зависимости

- ⚠️ **Блокируется:** n8n Workflow (#${prevIssueNum || '2'})
- ⚠️ **Блокирует:** Testing & Validation

## Ссылки

- [Playbook: ${stepNumber.padStart(2, '0')}_playbook.md](../../STEP_IMPLEMENTATION_PLAYBOOKS/${stepNumber.padStart(2, '0')}_playbook.md)
- [Epic: #${epicNumber}](../../issues/${epicNumber})`,
        },
        {
            order: 4,
            title: `[STEP ${stepNumber}] 4️⃣ Testing & Validation: ручные проверки`,
            body: (prevIssueNums) => {
                const prevNums = prevIssueNums || ['1', '2', '3'];
                return `# 4️⃣ Testing & Validation: ручные проверки

**Epic:** #${epicNumber}  
**Порядок:** 4/4 (финальный шаг)  
**Статус:** 🟡 PENDING  
**Блокируется:** #${prevNums[0]}, #${prevNums[1]}, #${prevNums[2]}

## Задача

Выполнить все обязательные ручные проверки из playbook перед переходом к следующему шагу.

## Обязательные проверки

- [ ] Check 1 — [описание проверки]
- [ ] Check 2 — [описание проверки]
- [ ] Check 3 — [описание проверки]

## Definition of Done

Шаг считается выполненным, если:
- ✅ Все проверки пройдены
- ✅ Результаты задокументированы

## Зависимости

- ⚠️ **Блокируется:** Все предыдущие Issues (#${prevNums.join(', #')})
- ✅ **Финальный шаг Epic** — после завершения можно переходить к следующему STEP

## Ссылки

- [Playbook: ${stepNumber.padStart(2, '0')}_playbook.md](../../STEP_IMPLEMENTATION_PLAYBOOKS/${stepNumber.padStart(2, '0')}_playbook.md)
- [Epic: #${epicNumber}](../../issues/${epicNumber})`;
            },
        },
    ];
    
    for (let i = 0; i < issueTemplates.length; i++) {
        const template = issueTemplates[i];
        
        // Проверяем, существует ли Issue с таким названием
        const existing = await findIssueByTitle(template.title);
        if (existing) {
            log('info', `Issue уже существует: #${existing.number}`);
            issues.push(existing);
            createdIssueNumbers.push(existing.number);
        } else {
            // Формируем body с правильными ссылками
            let body;
            if (typeof template.body === 'function') {
                if (i === 0) {
                    // Первый Issue - без зависимостей
                    body = template.body(null);
                } else if (i === issueTemplates.length - 1) {
                    // Последний Issue - зависит от всех предыдущих
                    body = template.body(createdIssueNumbers);
                } else {
                    // Промежуточные Issues - зависят от предыдущего
                    body = template.body(createdIssueNumbers[createdIssueNumbers.length - 1]);
                }
            } else {
                body = template.body;
            }
            
            const issue = await createIssue(template.title, body, []);
            log('success', `Issue создан: #${issue.number} - ${template.title}`);
            issues.push(issue);
            createdIssueNumbers.push(issue.number);
            
            // Небольшая задержка между созданиями
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
    
    return issues;
}

// Поиск Issue по названию
async function findIssueByTitle(title) {
    const searchQuery = `repo:${GITHUB_OWNER}/${GITHUB_REPO} is:issue "${title}" in:title`;
    const encodedQuery = encodeURIComponent(searchQuery);
    
    try {
        const response = await makeRequest(
            `https://api.github.com/search/issues?q=${encodedQuery}&per_page=5`
        );
        
        if (response.statusCode === 200 && response.body.items && response.body.items.length > 0) {
            return response.body.items[0];
        }
        
        return null;
    } catch (error) {
        return null;
    }
}

// Получить все Issues из Epic
async function getEpicIssues(epicNumber) {
    log('info', `Получение Issues из Epic #${epicNumber}...`);
    
    const epic = await getIssueFromAPI(epicNumber);
    
    // Извлекаем номера Issues из body Epic
    const issueNumbers = [];
    const body = epic.body || '';
    
    // Паттерны: #24, #25, #26, #27 или [Issue #24](../../issues/24)
    const patterns = [
        /#(\d+)/g,
        /issues\/(\d+)/g,
    ];
    
    for (const pattern of patterns) {
        const matches = body.matchAll(pattern);
        for (const match of matches) {
            const num = parseInt(match[1], 10);
            if (num && num !== epicNumber && !issueNumbers.includes(num)) {
                issueNumbers.push(num);
            }
        }
    }
    
    // Сортируем по порядку (если указан в Issue)
    const issues = await Promise.all(
        issueNumbers.map(num => getIssueFromAPI(num))
    );
    
    // Сортируем по порядку выполнения (если указан)
    issues.sort((a, b) => {
        const orderA = extractOrder(a.body);
        const orderB = extractOrder(b.body);
        if (orderA && orderB) return orderA - orderB;
        if (orderA) return -1;
        if (orderB) return 1;
        return a.number - b.number;
    });
    
    log('success', `Найдено ${issues.length} Issues в Epic #${epicNumber}`);
    return issues;
}

// Извлечь порядок выполнения из Issue body
function extractOrder(issueBody) {
    const match = issueBody.match(/\*\*Порядок:\*\*\s*(\d+)\/(\d+)/);
    if (match) {
        return parseInt(match[1], 10);
    }
    return null;
}

// Проверить, закрыт ли Issue
function isIssueClosed(issue) {
    return issue.state === 'closed';
}

// Проверить, все ли пункты чеклиста выполнены
function isChecklistComplete(issueBody) {
    if (!issueBody) return false;
    
    // Находим все чекбоксы
    const checkboxPattern = /- \[([ x])\]/g;
    const checkboxes = [];
    let match;
    
    while ((match = checkboxPattern.exec(issueBody)) !== null) {
        checkboxes.push(match[1] === 'x');
    }
    
    if (checkboxes.length === 0) {
        // Если нет чекбоксов, считаем что чеклист выполнен
        return true;
    }
    
    // Проверяем, что все чекбоксы отмечены
    const allChecked = checkboxes.every(checked => checked);
    
    return allChecked;
}

// Проверить, пройдено ли тестирование (для задач с workflow)
async function isTestingComplete(issue) {
    const body = issue.body || '';
    const title = (issue.title || '').toLowerCase();
    
    // Если задача не требует тестирования workflow, считаем тестирование пройденным
    if (!requiresWorkflowTesting(issue)) {
        return true;
    }
    
    // Проверяем наличие Workflow ID
    const workflowId = extractWorkflowId(body);
    if (!workflowId) {
        log('warning', `Workflow ID не найден для Issue #${issue.number}`);
        return false;
    }
    
    // Проверяем, что workflow протестирован успешно
    // Это делается через проверку последнего execution
    try {
        const lastExecution = await getLastExecution(workflowId);
        
        if (!lastExecution) {
            log('warning', `Нет executions для workflow ${workflowId}`);
            return false;
        }
        
        // Проверяем, что последний execution успешен
        const isSuccess = lastExecution.finished && !lastExecution.data?.resultData?.error;
        
        if (!isSuccess) {
            log('warning', `Последний execution для workflow ${workflowId} не успешен`);
            return false;
        }
        
        return true;
    } catch (error) {
        log('warning', `Ошибка при проверке тестирования: ${error.message}`);
        return false;
    }
}

// Проверить, выполнена ли задача полностью (чеклист + тестирование)
async function isTaskComplete(issue) {
    // Проверяем чеклист
    const checklistComplete = isChecklistComplete(issue.body);
    if (!checklistComplete) {
        log('warning', `Чеклист не выполнен для Issue #${issue.number}`);
        return { complete: false, reason: 'checklist_incomplete' };
    }
    
    // Проверяем тестирование
    const testingComplete = await isTestingComplete(issue);
    if (!testingComplete) {
        log('warning', `Тестирование не пройдено для Issue #${issue.number}`);
        return { complete: false, reason: 'testing_incomplete' };
    }
    
    return { complete: true };
}

// Проверить, требует ли Issue тестирования workflow
function requiresWorkflowTesting(issue) {
    const body = (issue.body || '').toLowerCase();
    const title = (issue.title || '').toLowerCase();
    
    return (
        body.includes('testing & validation') ||
        body.includes('workflow') ||
        title.includes('testing') ||
        title.includes('workflow')
    );
}

// Выполнить одну задачу
async function executeTask(issue, taskIndex, totalTasks) {
    log('header', '='.repeat(60));
    log('header', `Задача ${taskIndex}/${totalTasks}: Issue #${issue.number}`);
    log('header', '='.repeat(60));
    log('info', `Название: ${issue.title}`);
    log('info', `Статус: ${issue.state}`);
    console.log('');
    
    // Проверяем, закрыт ли Issue
    if (isIssueClosed(issue)) {
        // Даже если Issue закрыт, проверяем чеклист и тестирование
        log('info', `Issue #${issue.number} закрыт, проверяю чеклист и тестирование...`);
        const completion = await isTaskComplete(issue);
        if (completion.complete) {
            log('success', `✅ Issue #${issue.number} полностью выполнен (чеклист + тестирование)`);
            return { success: true, skipped: true, issue: issue.number };
        } else {
            log('warning', `⚠️ Issue #${issue.number} закрыт, но ${completion.reason}`);
            // Продолжаем выполнение, чтобы завершить чеклист и тестирование
        }
    }
    
    // Проверяем зависимости
    const dependencies = extractDependencies(issue.body);
    if (dependencies.length > 0) {
        log('info', `Проверка зависимостей: ${dependencies.join(', ')}`);
        const allDependenciesMet = await checkDependencies(dependencies);
        if (!allDependenciesMet) {
            log('error', `❌ Зависимости не выполнены для Issue #${issue.number}`);
            return { success: false, issue: issue.number, reason: 'dependencies_not_met' };
        }
        log('success', `✅ Все зависимости выполнены`);
    }
    
    // Выполняем задачу
    log('info', 'Выполнение задачи...');
    
    let taskExecuted = false;
    
    // TODO: Здесь должна быть логика выполнения задачи
    // Пока что просто проверяем, требует ли она тестирования workflow
    if (requiresWorkflowTesting(issue)) {
        log('info', 'Задача требует тестирования workflow');
        
        const workflowId = extractWorkflowId(issue.body);
        if (workflowId) {
            log('info', `Workflow ID найден: ${workflowId}`);
            log('info', 'Запуск автоматического исправления и тестирования...');
            
            try {
                const result = await fixAndTestLoop(issue.number, workflowId);
                taskExecuted = true;
                
                if (!result.success) {
                    return {
                        success: false,
                        issue: issue.number,
                        workflowId: workflowId,
                        iterations: result.iterations,
                        reason: 'workflow_test_failed',
                    };
                }
            } catch (error) {
                log('error', `Ошибка при тестировании workflow: ${error.message}`);
                return { success: false, issue: issue.number, reason: 'workflow_test_failed' };
            }
        } else {
            log('warning', 'Workflow ID не найден, требуется ручное выполнение');
            return { success: false, issue: issue.number, reason: 'workflow_id_not_found' };
        }
    } else {
        log('info', 'Задача не требует тестирования workflow');
        log('warning', '⚠️ Автоматическое выполнение задачи пока не реализовано');
        log('info', 'Требуется ручное выполнение');
        taskExecuted = false;
    }
    
    // После выполнения задачи проверяем чеклист и тестирование
    console.log('');
    log('info', 'Проверка завершения задачи (чеклист + тестирование)...');
    
    // Обновляем Issue для получения актуального состояния
    const updatedIssue = await getIssueFromAPI(issue.number);
    
    const completion = await isTaskComplete(updatedIssue);
    
    if (!completion.complete) {
        log('error', `❌ Задача #${issue.number} не завершена: ${completion.reason}`);
        
        if (completion.reason === 'checklist_incomplete') {
            log('info', 'Требуется выполнить все пункты чеклиста');
            log('info', 'Обновите Issue, отметив все чекбоксы как выполненные');
        } else if (completion.reason === 'testing_incomplete') {
            log('info', 'Требуется пройти тестирование workflow');
            log('info', 'Запустите workflow в n8n UI и убедитесь, что execution успешен');
        }
        
        return {
            success: false,
            issue: issue.number,
            reason: completion.reason,
            taskExecuted: taskExecuted,
        };
    }
    
    log('success', `✅ Задача #${issue.number} полностью завершена (чеклист + тестирование)`);
    
    return {
        success: true,
        issue: issue.number,
        workflowId: extractWorkflowId(updatedIssue.body),
        taskExecuted: taskExecuted,
    };
}

// Извлечь зависимости из Issue body
function extractDependencies(issueBody) {
    const dependencies = [];
    const patterns = [
        /\*\*Блокируется:\*\*\s*#(\d+)/g,
        /\[#(\d+)\]\(/g,
    ];
    
    for (const pattern of patterns) {
        const matches = issueBody.matchAll(pattern);
        for (const match of matches) {
            const num = parseInt(match[1], 10);
            if (num && !dependencies.includes(num)) {
                dependencies.push(num);
            }
        }
    }
    
    return dependencies;
}

// Проверить, выполнены ли зависимости
async function checkDependencies(issueNumbers) {
    for (const num of issueNumbers) {
        const issue = await getIssueFromAPI(num);
        if (!isIssueClosed(issue)) {
            log('warning', `Issue #${num} не закрыт`);
            return false;
        }
    }
    return true;
}

// Выполнить блок задач
async function executeTaskBlock(issueNumbers) {
    log('header', '='.repeat(60));
    log('header', 'GenomAI — Task Block Executor');
    log('header', '='.repeat(60));
    log('info', `Задач в блоке: ${issueNumbers.length}`);
    log('info', `Максимум итераций на задачу: ${MAX_ITERATIONS_PER_TASK}`);
    log('info', `Автоматическое исправление: ${AUTO_FIX_ENABLED ? 'включено' : 'выключено'}`);
    console.log('');
    
    const results = [];
    
    for (let i = 0; i < issueNumbers.length; i++) {
        const issueNumber = issueNumbers[i];
        const issue = await getIssueFromAPI(issueNumber);
        
        const result = await executeTask(issue, i + 1, issueNumbers.length);
        results.push(result);
        
        console.log('');
        
        if (!result.success && !result.skipped) {
            log('error', `❌ Задача #${issueNumber} не выполнена: ${result.reason}`);
            
            if (result.reason === 'checklist_incomplete' || result.reason === 'testing_incomplete') {
                log('warning', 'Задача требует завершения чеклиста и/или тестирования');
                log('info', 'Выполните недостающие пункты и запустите скрипт снова');
            }
            
            log('error', 'Остановка выполнения блока задач');
            break;
        }
        
        if (result.success) {
            if (result.skipped) {
                log('success', `✅ Задача #${issueNumber} уже выполнена (пропущена)`);
            } else {
                log('success', `✅ Задача #${issueNumber} выполнена успешно (чеклист + тестирование)`);
            }
        }
    }
    
    // Итоговый отчёт
    console.log('');
    log('header', '='.repeat(60));
    log('header', 'Итоговый отчёт');
    log('header', '='.repeat(60));
    
    const successful = results.filter(r => r.success).length;
    const failed = results.filter(r => !r.success && !r.skipped).length;
    const skipped = results.filter(r => r.skipped).length;
    
    log('info', `Всего задач: ${results.length}`);
    log('success', `✅ Выполнено: ${successful}`);
    log('info', `⏭️ Пропущено: ${skipped}`);
    if (failed > 0) {
        log('error', `❌ Не выполнено: ${failed}`);
    }
    
    console.log('');
    
    // Детали по каждой задаче
    results.forEach((result, index) => {
        const issue = issueNumbers[index];
        if (result.skipped) {
            log('info', `  #${issue}: пропущено (уже закрыт)`);
        } else if (result.success) {
            log('success', `  #${issue}: выполнено успешно`);
            if (result.workflowId) {
                log('info', `    Workflow: ${result.workflowId} (${result.iterations} итераций)`);
            }
        } else {
            log('error', `  #${issue}: не выполнено (${result.reason})`);
        }
    });
    
    return {
        success: failed === 0,
        total: results.length,
        successful,
        failed,
        skipped,
        results,
    };
}

// Основная функция
async function main() {
    const args = process.argv.slice(2);
    
    if (args.length === 0) {
        console.error('Использование:');
        console.error('  node execute_task_block.js <epic-number>');
        console.error('  node execute_task_block.js <issue-number> <issue-number> ...');
        console.error('  node execute_task_block.js "STEP 04"');
        console.error('');
        console.error('Примеры:');
        console.error('  node execute_task_block.js 23  # Epic #23');
        console.error('  node execute_task_block.js 24 25 26 27  # Конкретные Issues');
        console.error('  node execute_task_block.js "STEP 04"  # По названию');
        process.exit(1);
    }
    
    if (!GITHUB_TOKEN) {
        log('error', 'GITHUB_TOKEN не установлен!');
        process.exit(1);
    }
    
    try {
        let issueNumbers = [];
        
        // Если первый аргумент - число, это Epic или список Issues
        if (!isNaN(parseInt(args[0], 10))) {
            if (args.length === 1) {
                // Один номер - это Epic
                const epicNumber = parseInt(args[0], 10);
                const issues = await getEpicIssues(epicNumber);
                issueNumbers = issues.map(i => i.number);
            } else {
                // Несколько номеров - это список Issues
                issueNumbers = args.map(a => parseInt(a, 10)).filter(n => !isNaN(n));
            }
        } else {
            // Поиск по названию (например, "STEP 04")
            const stepName = args[0];
            log('info', `Поиск Epic по названию: "${stepName}"`);
            
            // Извлекаем номер STEP (например, "STEP 04" -> "04")
            const stepMatch = stepName.match(/STEP\s*(\d+)/i);
            if (!stepMatch) {
                log('error', `Не удалось извлечь номер STEP из "${stepName}"`);
                log('info', 'Используйте формат: "STEP 04" или номер Epic');
                process.exit(1);
            }
            
            const stepNumber = stepMatch[1];
            
            // Ищем Epic
            let epic = await findEpicByName(stepName);
            
            if (!epic) {
                log('warning', `Epic для ${stepName} не найден`);
                log('info', 'Создание Epic...');
                epic = await createEpicForStep(stepName, stepNumber);
            }
            
            // Получаем Issues из Epic
            const issues = await getEpicIssues(epic.number);
            
            // Если Issues нет, создаём их
            if (issues.length === 0) {
                log('warning', `Issues для Epic #${epic.number} не найдены`);
                log('info', 'Создание Issues на основе playbook...');
                const createdIssues = await createIssuesForEpic(epic.number, stepNumber);
                issueNumbers = createdIssues.map(i => i.number);
            } else {
                issueNumbers = issues.map(i => i.number);
            }
        }
        
        if (issueNumbers.length === 0) {
            log('error', 'Не найдено Issues для выполнения');
            process.exit(1);
        }
        
        log('info', `Найдено Issues: ${issueNumbers.join(', ')}`);
        console.log('');
        
        // Выполняем блок задач
        const result = await executeTaskBlock(issueNumbers);
        
        process.exit(result.success ? 0 : 1);
        
    } catch (error) {
        log('error', `Ошибка: ${error.message}`);
        console.error(error);
        process.exit(1);
    }
}

// Запуск
if (require.main === module) {
    main().catch((error) => {
        console.error('Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { executeTaskBlock, getEpicIssues, executeTask };

