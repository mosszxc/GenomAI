#!/usr/bin/env node

/**
 * GenomAI — Fix and Test n8n Workflow (Auto-fix loop)
 * Версия: v1.0
 * Назначение: Автоматическое исправление и тестирование workflow до успешного результата
 * 
 * Использование:
 *   node fix_and_test_workflow.js <issue-number>
 *   node fix_and_test_workflow.js <issue-number> <workflow-id>
 */

const https = require('https');
const http = require('http');
const { testWorkflow, getWorkflow, getExecutionDetails } = require('./test_n8n_workflow.js');
const { getIssue, extractWorkflowId, addComment } = require('./test_workflow_from_issue.js');

// Конфигурация
const GITHUB_TOKEN = process.env.GITHUB_TOKEN || '';
const GITHUB_OWNER = process.env.GITHUB_OWNER || 'mosszxc';
const GITHUB_REPO = process.env.GITHUB_REPO || 'GenomAI';
const N8N_API_URL = process.env.N8N_API_URL || 'https://kazamaqwe.app.n8n.cloud/api/v1';
const N8N_API_KEY = process.env.N8N_API_KEY || '';
const MAX_ITERATIONS = parseInt(process.env.MAX_ITERATIONS || '10', 10);
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
                'X-N8N-API-KEY': N8N_API_KEY,
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

// Анализ ошибок из execution
function analyzeErrors(execution) {
    const errors = [];
    
    if (!execution || !execution.data) {
        return errors;
    }
    
    const runData = execution.data.resultData?.runData || {};
    
    // Проверяем каждый node
    for (const [nodeName, nodeExecutions] of Object.entries(runData)) {
        if (!nodeExecutions || !Array.isArray(nodeExecutions)) continue;
        
        for (const nodeExec of nodeExecutions) {
            if (nodeExec.error) {
                errors.push({
                    node: nodeName,
                    error: nodeExec.error,
                    message: nodeExec.error.message || nodeExec.error.toString(),
                    type: classifyError(nodeExec.error),
                });
            }
        }
    }
    
    // Проверяем общие ошибки
    if (execution.data.resultData?.error) {
        errors.push({
            node: 'workflow',
            error: execution.data.resultData.error,
            message: execution.data.resultData.error.message || execution.data.resultData.error.toString(),
            type: 'workflow_error',
        });
    }
    
    return errors;
}

// Классификация ошибок
function classifyError(error) {
    const message = (error.message || error.toString()).toLowerCase();
    
    if (message.includes('schema') || message.includes('validation')) {
        return 'schema_validation';
    }
    if (message.includes('connection') || message.includes('credentials')) {
        return 'connection';
    }
    if (message.includes('table') || message.includes('column')) {
        return 'database';
    }
    if (message.includes('expression') || message.includes('syntax')) {
        return 'expression';
    }
    if (message.includes('required') || message.includes('missing')) {
        return 'missing_parameter';
    }
    if (message.includes('type') || message.includes('format')) {
        return 'type_mismatch';
    }
    
    return 'unknown';
}

// Получить workflow через n8n API
async function getWorkflowFromAPI(workflowId) {
    try {
        const response = await makeRequest(`${N8N_API_URL}/workflows/${workflowId}`);
        if (response.statusCode === 200) {
            return response.body;
        }
        throw new Error(`HTTP ${response.statusCode}: ${JSON.stringify(response.body)}`);
    } catch (error) {
        log('error', `Ошибка при получении workflow: ${error.message}`);
        throw error;
    }
}

// Обновить workflow через n8n API
async function updateWorkflow(workflowId, workflowData) {
    try {
        const response = await makeRequest(`${N8N_API_URL}/workflows/${workflowId}`, {
            method: 'PUT',
            body: workflowData,
        });
        
        if (response.statusCode === 200) {
            return response.body;
        }
        throw new Error(`HTTP ${response.statusCode}: ${JSON.stringify(response.body)}`);
    } catch (error) {
        log('error', `Ошибка при обновлении workflow: ${error.message}`);
        throw error;
    }
}

// Исправление ошибок
async function fixErrors(workflowId, errors) {
    log('info', `Анализ ${errors.length} ошибок для исправления...`);
    
    const workflow = await getWorkflowFromAPI(workflowId);
    let hasChanges = false;
    
    for (const error of errors) {
        log('info', `Исправление ошибки в node "${error.node}": ${error.type}`);
        
        const node = workflow.nodes.find(n => n.name === error.node || n.id === error.node);
        if (!node) {
            log('warning', `Node "${error.node}" не найден, пропускаю`);
            continue;
        }
        
        // Исправление в зависимости от типа ошибки
        let fixed = false;
        switch (error.type) {
            case 'schema_validation':
                fixed = fixSchemaValidation(node, error);
                break;
            case 'missing_parameter':
                fixed = fixMissingParameter(node, error);
                break;
            case 'expression':
                fixed = fixExpression(node, error);
                break;
            case 'connection':
                log('warning', `Ошибка подключения в "${error.node}" - требует ручной настройки credentials`);
                break;
            case 'database':
                fixed = fixDatabaseError(node, error);
                break;
            default:
                log('warning', `Неизвестный тип ошибки: ${error.type}, требуется ручное исправление`);
        }
        
        if (fixed) {
            hasChanges = true;
        }
    }
    
    if (hasChanges) {
        log('info', 'Применение исправлений к workflow...');
        await updateWorkflow(workflowId, workflow);
        log('success', 'Workflow обновлён');
    }
    
    return hasChanges;
}

// Исправление schema validation
function fixSchemaValidation(node, error) {
    // Для Supabase nodes добавляем useCustomSchema и schema
    if (node.type === 'n8n-nodes-base.supabase') {
        if (!node.parameters.useCustomSchema) {
            node.parameters.useCustomSchema = true;
            node.parameters.schema = 'genomai';
            log('info', `Добавлен useCustomSchema и schema для ${node.name}`);
            return true;
        }
    }
    return false;
}

// Исправление missing parameter
function fixMissingParameter(node, error) {
    const message = error.message.toLowerCase();
    
    // Проверяем, какие параметры отсутствуют
    if (message.includes('table') && node.type === 'n8n-nodes-base.supabase') {
        if (!node.parameters.tableId) {
            // Пытаемся определить tableId из имени node
            const tableName = node.name.toLowerCase().replace(/[^a-z0-9]/g, '');
            if (tableName.includes('transcript')) {
                node.parameters.tableId = { __rl: true, value: 'transcripts', mode: 'name' };
            } else if (tableName.includes('creative')) {
                node.parameters.tableId = { __rl: true, value: 'creatives', mode: 'name' };
            } else if (tableName.includes('idea')) {
                node.parameters.tableId = { __rl: true, value: 'ideas', mode: 'name' };
            } else if (tableName.includes('event')) {
                node.parameters.tableId = { __rl: true, value: 'event_log', mode: 'name' };
            }
            log('info', `Добавлен tableId для ${node.name}`);
            return true;
        }
    }
    
    return false;
}

// Исправление expression
function fixExpression(node, error) {
    // Для expression ошибок обычно нужно исправить вручную
    log('warning', `Ошибка expression в "${node.name}" - требуется ручное исправление`);
    return false;
}

// Исправление database error
function fixDatabaseError(node, error) {
    // Проверяем, может быть проблема с schema
    if (node.type === 'n8n-nodes-base.supabase') {
        if (!node.parameters.useCustomSchema) {
            node.parameters.useCustomSchema = true;
            node.parameters.schema = 'genomai';
            log('info', `Добавлен useCustomSchema для ${node.name}`);
            return true;
        }
    }
    return false;
}

// Основная функция: цикл исправления и тестирования
async function fixAndTestLoop(issueNumber, workflowId) {
    log('header', '='.repeat(60));
    log('header', 'GenomAI — Auto-fix and Test Workflow Loop');
    log('header', '='.repeat(60));
    log('info', `Issue: #${issueNumber}`);
    log('info', `Workflow ID: ${workflowId}`);
    log('info', `Max iterations: ${MAX_ITERATIONS}`);
    log('info', `Auto-fix: ${AUTO_FIX_ENABLED ? 'enabled' : 'disabled'}`);
    console.log('');
    
    const results = [];
    
    for (let iteration = 1; iteration <= MAX_ITERATIONS; iteration++) {
        log('header', `Итерация ${iteration}/${MAX_ITERATIONS}`);
        console.log('');
        
        // 1. Тестирование
        log('info', 'Запуск тестирования...');
        log('warning', '⚠️ ВНИМАНИЕ: Запустите workflow в n8n UI');
        log('info', `1. Откройте: https://kazamaqwe.app.n8n.cloud/workflow/${workflowId}`);
        log('info', '2. Нажмите на Manual Trigger node');
        log('info', '3. Нажмите "Execute Node" или "Test workflow"');
        log('info', '4. Скрипт автоматически обнаружит новый execution...');
        console.log('');
        
        const testResult = await testWorkflow(workflowId, { waitForManual: true });
        const success = testResult && testResult.finished && !testResult.data?.resultData?.error;
        
        results.push({
            iteration,
            success,
            execution: testResult,
        });
        
        if (success) {
            log('success', `✅ Workflow работает успешно после ${iteration} итерации(й)!`);
            console.log('');
            
            // Добавляем финальный комментарий в Issue
            await addComment(issueNumber, `## ✅ Workflow исправлен и протестирован!

🟢 **Статус:** успешно после ${iteration} итерации(й)
🔧 **Workflow ID:** \`${workflowId}\`
🔗 **Workflow URL:** https://kazamaqwe.app.n8n.cloud/workflow/${workflowId}

**Итерации:**
${results.map((r, i) => `- Итерация ${i + 1}: ${r.success ? '✅ успешно' : '❌ ошибка'}`).join('\n')}

*Автоматически исправлено и протестировано из Cursor*`);
            
            return { success: true, iterations: iteration, results };
        }
        
        // 2. Анализ ошибок
        log('info', 'Анализ ошибок...');
        const errors = analyzeErrors(testResult);
        
        if (errors.length === 0) {
            log('warning', 'Ошибки не найдены, но workflow не успешен. Требуется ручная проверка.');
            break;
        }
        
        log('error', `Найдено ${errors.length} ошибок:`);
        errors.forEach(err => {
            log('error', `  - ${err.node}: ${err.type} - ${err.message}`);
        });
        console.log('');
        
        // 3. Исправление (если включено)
        if (!AUTO_FIX_ENABLED) {
            log('warning', 'Автоматическое исправление отключено. Требуется ручное исправление.');
            break;
        }
        
        log('info', 'Попытка автоматического исправления...');
        const fixed = await fixErrors(workflowId, errors);
        
        if (!fixed) {
            log('warning', 'Не удалось автоматически исправить ошибки. Требуется ручное исправление.');
            break;
        }
        
        log('success', 'Исправления применены. Повторное тестирование...');
        console.log('');
        
        // Небольшая задержка перед следующим тестом
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
    
    // Если дошли сюда, значит не удалось исправить
    log('error', `Не удалось исправить workflow за ${MAX_ITERATIONS} итераций`);
    
    await addComment(issueNumber, `## ⚠️ Workflow требует ручного исправления

🔴 **Статус:** не удалось автоматически исправить за ${MAX_ITERATIONS} итераций
🔧 **Workflow ID:** \`${workflowId}\`

**Итерации:**
${results.map((r, i) => `- Итерация ${i + 1}: ${r.success ? '✅ успешно' : '❌ ошибка'}`).join('\n')}

**Требуется ручное исправление ошибок.**

*Автоматическое исправление из Cursor*`);
    
    return { success: false, iterations: MAX_ITERATIONS, results };
}

// Основная функция
async function main() {
    const issueNumber = process.argv[2];
    const workflowIdArg = process.argv[3];
    
    if (!issueNumber) {
        console.error('Использование:');
        console.error('  node fix_and_test_workflow.js <issue-number> [workflow-id]');
        console.error('');
        console.error('Примеры:');
        console.error('  node fix_and_test_workflow.js 22');
        console.error('  node fix_and_test_workflow.js 22 cGSyJPROrkqLVHZP');
        console.error('');
        console.error('Переменные окружения:');
        console.error('  GITHUB_TOKEN - GitHub token (обязательно)');
        console.error('  N8N_API_KEY - n8n API key (обязательно)');
        console.error('  MAX_ITERATIONS - Максимум итераций (по умолчанию: 10)');
        console.error('  AUTO_FIX=false - Отключить автоматическое исправление');
        process.exit(1);
    }
    
    if (!GITHUB_TOKEN) {
        log('error', 'GITHUB_TOKEN не установлен!');
        process.exit(1);
    }
    
    if (!N8N_API_KEY) {
        log('error', 'N8N_API_KEY не установлен!');
        process.exit(1);
    }
    
    try {
        // 1. Получить Issue
        const issue = await getIssue(issueNumber);
        console.log('');
        
        // 2. Извлечь Workflow ID
        let workflowId = workflowIdArg;
        if (!workflowId) {
            workflowId = extractWorkflowId(issue.body);
        }
        
        if (!workflowId) {
            log('error', 'Workflow ID не найден в Issue и не указан как аргумент');
            await addComment(issueNumber, `## ⚠️ Workflow ID не найден
            
Не удалось найти Workflow ID в Issue.

**Как указать Workflow ID:**

1. В Issue body: \`**Workflow ID:** \`workflow-id\`\`
2. Как аргумент: \`node fix_and_test_workflow.js ${issueNumber} workflow-id\`
`);
            process.exit(1);
        }
        
        log('success', `Workflow ID найден: ${workflowId}`);
        console.log('');
        
        // 3. Запустить цикл исправления и тестирования
        const result = await fixAndTestLoop(issueNumber, workflowId);
        
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

module.exports = { fixAndTestLoop, analyzeErrors, fixErrors };

