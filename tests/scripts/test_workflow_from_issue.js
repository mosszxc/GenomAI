#!/usr/bin/env node

/**
 * GenomAI — Test n8n Workflow from GitHub Issue
 * Версия: v1.0
 * Назначение: Автоматический запуск тестирования workflow из Issue через Cursor
 * 
 * Использование:
 *   node test_workflow_from_issue.js <issue-number>
 *   node test_workflow_from_issue.js <issue-number> <workflow-id>
 */

const https = require('https');
const http = require('http');

// Конфигурация
const GITHUB_TOKEN = process.env.GITHUB_TOKEN || '';
const GITHUB_OWNER = process.env.GITHUB_OWNER || 'mosszxc';
const GITHUB_REPO = process.env.GITHUB_REPO || 'GenomAI';
const N8N_API_URL = process.env.N8N_API_URL || 'https://kazamaqwe.app.n8n.cloud/api/v1';
const N8N_API_KEY = process.env.N8N_API_KEY || '';

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
                'User-Agent': 'GenomAI-Test-Script',
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

// Получить Issue через GitHub API
async function getIssue(issueNumber) {
    log('info', `Получение Issue #${issueNumber}...`);
    
    try {
        const response = await makeRequest(
            `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/issues/${issueNumber}`,
            {
                headers: {
                    'Authorization': `token ${GITHUB_TOKEN}`,
                    'Accept': 'application/vnd.github.v3+json',
                },
            }
        );
        
        if (response.statusCode === 200) {
            log('success', `Issue найден: ${response.body.title}`);
            return response.body;
        } else {
            throw new Error(`HTTP ${response.statusCode}: ${JSON.stringify(response.body)}`);
        }
    } catch (error) {
        log('error', `Ошибка при получении Issue: ${error.message}`);
        throw error;
    }
}

// Извлечь Workflow ID из Issue body
function extractWorkflowId(issueBody) {
    if (!issueBody) return null;
    
    // Паттерны для поиска:
    // - Workflow ID: `abc123`
    // - workflow-id: `abc123`
    // - Workflow: `abc123`
    // - Workflow ID: abc123 (без backticks)
    
    const patterns = [
        /Workflow ID:\s*`?([a-zA-Z0-9_-]+)`?/i,
        /workflow-id:\s*`?([a-zA-Z0-9_-]+)`?/i,
        /Workflow:\s*`?([a-zA-Z0-9_-]+)`?/i,
        /workflow[\/\s]+([a-zA-Z0-9_-]+)/i,
    ];
    
    for (const pattern of patterns) {
        const match = issueBody.match(pattern);
        if (match && match[1]) {
            return match[1];
        }
    }
    
    return null;
}

// Добавить комментарий в Issue
async function addComment(issueNumber, comment) {
    log('info', `Добавление комментария в Issue #${issueNumber}...`);
    
    try {
        const response = await makeRequest(
            `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/issues/${issueNumber}/comments`,
            {
                method: 'POST',
                headers: {
                    'Authorization': `token ${GITHUB_TOKEN}`,
                    'Accept': 'application/vnd.github.v3+json',
                },
                body: {
                    body: comment,
                },
            }
        );
        
        if (response.statusCode === 201) {
            log('success', `Комментарий добавлен в Issue #${issueNumber}`);
            return response.body;
        } else {
            throw new Error(`HTTP ${response.statusCode}: ${JSON.stringify(response.body)}`);
        }
    } catch (error) {
        log('error', `Ошибка при добавлении комментария: ${error.message}`);
        throw error;
    }
}

// Импорт функции тестирования из test_n8n_workflow.js
async function testWorkflow(workflowId) {
    // Динамический импорт функции из другого файла
    const { testWorkflow: testFn } = require('./test_n8n_workflow.js');
    return await testFn(workflowId, { waitForManual: true });
}

// Основная функция
async function main() {
    const issueNumber = process.argv[2];
    const workflowIdArg = process.argv[3];
    
    if (!issueNumber) {
        console.error('Использование:');
        console.error('  node test_workflow_from_issue.js <issue-number> [workflow-id]');
        console.error('');
        console.error('Примеры:');
        console.error('  node test_workflow_from_issue.js 22');
        console.error('  node test_workflow_from_issue.js 22 cGSyJPROrkqLVHZP');
        console.error('');
        console.error('Переменные окружения:');
        console.error('  GITHUB_TOKEN - GitHub token (обязательно)');
        console.error('  N8N_API_KEY - n8n API key (обязательно)');
        console.error('  GITHUB_OWNER - GitHub owner (по умолчанию: mosszxc)');
        console.error('  GITHUB_REPO - GitHub repo (по умолчанию: GenomAI)');
        process.exit(1);
    }
    
    console.log('='.repeat(60));
    log('header', 'GenomAI — Test n8n Workflow from GitHub Issue');
    console.log('='.repeat(60));
    log('info', `Issue Number: ${issueNumber}`);
    console.log('');
    
    if (!GITHUB_TOKEN) {
        log('error', 'GITHUB_TOKEN не установлен!');
        log('info', 'Установите переменную окружения: export GITHUB_TOKEN="your-token"');
        process.exit(1);
    }
    
    if (!N8N_API_KEY) {
        log('error', 'N8N_API_KEY не установлен!');
        log('info', 'Установите переменную окружения: export N8N_API_KEY="your-api-key"');
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
            log('info', 'Добавьте Workflow ID в Issue body:');
            log('info', '  **Workflow ID:** `workflow-id`');
            log('info', 'Или укажите как аргумент:');
            log('info', `  node test_workflow_from_issue.js ${issueNumber} workflow-id`);
            
            // Добавим комментарий с инструкцией
            await addComment(issueNumber, `## ⚠️ Workflow ID не найден
            
Не удалось найти Workflow ID в Issue.

**Как указать Workflow ID:**

1. В Issue body: \`**Workflow ID:** \`workflow-id\`\`
2. Как аргумент: \`node test_workflow_from_issue.js ${issueNumber} workflow-id\`

**Пример:**
\`\`\`
**Workflow ID:** \`cGSyJPROrkqLVHZP\`
\`\`\`
`);
            process.exit(1);
        }
        
        log('success', `Workflow ID найден: ${workflowId}`);
        console.log('');
        
        // 3. Запустить тестирование
        log('info', 'Запуск тестирования workflow...');
        log('warning', '⚠️ ВНИМАНИЕ: Этот тест требует ручного запуска workflow в n8n UI');
        log('info', `1. Откройте workflow: https://kazamaqwe.app.n8n.cloud/workflow/${workflowId}`);
        log('info', '2. Нажмите на Manual Trigger node');
        log('info', '3. Нажмите "Execute Node" или "Test workflow"');
        log('info', '4. Скрипт автоматически обнаружит новый execution...');
        console.log('');
        
        const result = await testWorkflow(workflowId);
        
        // 4. Добавить комментарий с результатами
        const success = result && result.finished && !result.data?.resultData?.error;
        const emoji = success ? '✅' : '❌';
        const status = success ? 'успешно' : 'с ошибкой';
        const statusColor = success ? '🟢' : '🔴';
        
        // Форматируем вывод
        const output = JSON.stringify(result, null, 2);
        const formattedOutput = output
            .replace(/\[INFO\]/g, 'ℹ️')
            .replace(/\[PASS\]/g, '✅')
            .replace(/\[FAIL\]/g, '❌')
            .replace(/\[WARN\]/g, '⚠️')
            .replace(/\[DEBUG\]/g, '🔍');
        
        const comment = `## ${emoji} Результаты тестирования n8n Workflow (из Cursor)

${statusColor} **Статус:** ${status}
🔧 **Workflow ID:** \`${workflowId}\`
🔗 **Workflow URL:** https://kazamaqwe.app.n8n.cloud/workflow/${workflowId}

<details>
<summary>📊 Детали выполнения</summary>

\`\`\`json
${formattedOutput}
\`\`\`

</details>

---

💡 **Для повторного запуска из Cursor:**
\`\`\`bash
node tests/scripts/test_workflow_from_issue.js ${issueNumber} ${workflowId}
\`\`\`

*Автоматически запущено из Cursor*`;
        
        await addComment(issueNumber, comment);
        console.log('');
        log('success', `Результаты добавлены в Issue #${issueNumber}`);
        
        process.exit(success ? 0 : 1);
        
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

module.exports = { main, getIssue, extractWorkflowId, addComment };
