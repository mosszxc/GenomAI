#!/usr/bin/env node

/**
 * GenomAI — n8n Workflow Test Script
 * Версия: v1.0
 * Назначение: Автоматизированное тестирование n8n workflows с Manual Trigger
 * 
 * Решает проблему: не нужно постоянно нажимать на Manual Trigger и проверять execution вручную
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

// Конфигурация
const N8N_API_URL = process.env.N8N_API_URL || 'https://kazamaqwe.app.n8n.cloud/api/v1';
const N8N_API_KEY = process.env.N8N_API_KEY || '';
const WORKFLOW_ID = process.env.WORKFLOW_ID || '';
const TIMEOUT = parseInt(process.env.TIMEOUT || '120000', 10); // 2 минуты по умолчанию
const POLL_INTERVAL = parseInt(process.env.POLL_INTERVAL || '1000', 10); // 1 секунда
const VERBOSE = process.env.VERBOSE === 'true';

// Цвета для консоли
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
        
        req.setTimeout(TIMEOUT, () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });
        
        req.end();
    });
}

// Получить информацию о workflow
async function getWorkflow(workflowId) {
    log('info', `Получение информации о workflow: ${workflowId}`);
    
    try {
        const response = await makeRequest(`${N8N_API_URL}/workflows/${workflowId}`);
        
        if (response.statusCode === 200) {
            log('success', `Workflow найден: ${response.body.name}`);
            if (VERBOSE) {
                log('debug', `Active: ${response.body.active}`);
                log('debug', `Nodes: ${response.body.nodes?.length || 0}`);
            }
            return response.body;
        } else {
            throw new Error(`HTTP ${response.statusCode}: ${JSON.stringify(response.body)}`);
        }
    } catch (error) {
        log('error', `Ошибка при получении workflow: ${error.message}`);
        throw error;
    }
}

// Активировать workflow (если неактивен)
async function activateWorkflow(workflowId) {
    log('info', `Проверка активности workflow...`);
    
    try {
        const workflow = await getWorkflow(workflowId);
        
        if (!workflow.active) {
            log('warning', `Workflow неактивен. Активация...`);
            const response = await makeRequest(`${N8N_API_URL}/workflows/${workflowId}/activate`, {
                method: 'POST',
            });
            
            if (response.statusCode === 200) {
                log('success', `Workflow активирован`);
            } else {
                log('warning', `Не удалось активировать workflow: ${response.statusCode}`);
            }
        } else {
            log('success', `Workflow уже активен`);
        }
    } catch (error) {
        log('warning', `Не удалось проверить/активировать workflow: ${error.message}`);
    }
}

// Запустить workflow через webhook (если есть webhook trigger)
async function triggerWorkflowViaWebhook(workflowId, data = {}) {
    log('info', `Попытка запуска через webhook...`);
    
    try {
        const workflow = await getWorkflow(workflowId);
        
        // Ищем webhook trigger
        const webhookNode = workflow.nodes?.find(node => 
            node.type === 'n8n-nodes-base.webhook' || 
            node.type === 'n8n-nodes-base.webhookTrigger'
        );
        
        if (!webhookNode) {
            log('warning', `Webhook trigger не найден. Пропускаем webhook запуск.`);
            return null;
        }
        
        const webhookPath = webhookNode.parameters?.path || webhookNode.parameters?.path?.value;
        if (!webhookPath) {
            log('warning', `Webhook path не найден. Пропускаем webhook запуск.`);
            return null;
        }
        
        // Для тестирования используем /webhook-test/ вместо /webhook/
        // Это позволяет тестировать workflow без влияния на production
        const isTestWebhook = webhookPath.startsWith('test-');
        const webhookEndpoint = isTestWebhook ? 'webhook-test' : 'webhook';
        const webhookUrl = `${N8N_API_URL.replace('/api/v1', '')}/${webhookEndpoint}/${webhookPath}`;
        log('info', `Запуск через ${isTestWebhook ? 'тестовый' : 'production'} webhook: ${webhookUrl}`);
        
        const response = await makeRequest(webhookUrl, {
            method: 'POST',
            body: data,
            headers: {
                'X-N8N-API-KEY': '', // Webhook не требует API key
            },
        });
        
        if (response.statusCode >= 200 && response.statusCode < 300) {
            log('success', `Webhook запущен успешно`);
            return response.body;
        } else {
            throw new Error(`HTTP ${response.statusCode}`);
        }
    } catch (error) {
        log('warning', `Не удалось запустить через webhook: ${error.message}`);
        return null;
    }
}

// Получить последний execution для workflow
async function getLastExecution(workflowId) {
    try {
        const response = await makeRequest(
            `${N8N_API_URL}/executions?workflowId=${workflowId}&limit=1`
        );
        
        if (response.statusCode === 200 && response.body.data && response.body.data.length > 0) {
            return response.body.data[0];
        }
        return null;
    } catch (error) {
        log('error', `Ошибка при получении последнего execution: ${error.message}`);
        return null;
    }
}

// Получить детали execution
async function getExecutionDetails(executionId) {
    try {
        const response = await makeRequest(`${N8N_API_URL}/executions/${executionId}`);
        
        if (response.statusCode === 200) {
            return response.body;
        }
        return null;
    } catch (error) {
        log('error', `Ошибка при получении деталей execution: ${error.message}`);
        return null;
    }
}

// Ждать завершения execution
async function waitForExecution(workflowId, previousExecutionId = null, timeout = TIMEOUT) {
    const startTime = Date.now();
    let lastExecutionId = previousExecutionId;
    
    log('info', `Ожидание нового execution (timeout: ${timeout}ms)...`);
    
    while (Date.now() - startTime < timeout) {
        await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL));
        
        const execution = await getLastExecution(workflowId);
        
        if (execution && execution.id !== lastExecutionId) {
            log('success', `Новый execution найден: ${execution.id}`);
            return execution;
        }
    }
    
    throw new Error('Timeout: новый execution не появился');
}

// Проверить статус execution
function checkExecutionStatus(execution) {
    log('header', '='.repeat(60));
    log('info', `Execution ID: ${execution.id}`);
    log('info', `Status: ${execution.finished ? 'finished' : 'running'}`);
    log('info', `Mode: ${execution.mode || 'unknown'}`);
    
    if (execution.startedAt) {
        const started = new Date(execution.startedAt);
        log('info', `Started: ${started.toLocaleString()}`);
    }
    
    if (execution.stoppedAt) {
        const stopped = new Date(execution.stoppedAt);
        const duration = new Date(stopped) - new Date(execution.startedAt);
        log('info', `Stopped: ${stopped.toLocaleString()}`);
        log('info', `Duration: ${duration}ms`);
    }
    
    if (execution.finished) {
        if (execution.data?.resultData?.error) {
            log('error', `Execution завершился с ошибкой!`);
            if (VERBOSE) {
                log('debug', `Error: ${JSON.stringify(execution.data.resultData.error, null, 2)}`);
            }
            return false;
        } else {
            log('success', `Execution завершился успешно!`);
            
            // Показываем статистику по нодам
            if (execution.data?.resultData?.runData) {
                const nodes = Object.keys(execution.data.resultData.runData);
                log('info', `Выполнено нод: ${nodes.length}`);
                
                if (VERBOSE) {
                    nodes.forEach(nodeName => {
                        const nodeData = execution.data.resultData.runData[nodeName];
                        const executions = nodeData[0] || [];
                        const successCount = executions.filter(e => !e.error).length;
                        const errorCount = executions.filter(e => e.error).length;
                        log('debug', `  ${nodeName}: ${successCount} success, ${errorCount} errors`);
                    });
                }
            }
            
            return true;
        }
    } else {
        log('warning', `Execution ещё выполняется...`);
        return null;
    }
}

// Основная функция
async function testWorkflow(workflowId, options = {}) {
    console.log('='.repeat(60));
    log('header', 'GenomAI — n8n Workflow Test Script');
    console.log('='.repeat(60));
    log('info', `Workflow ID: ${workflowId}`);
    log('info', `API URL: ${N8N_API_URL}`);
    log('info', `Timeout: ${TIMEOUT}ms`);
    console.log('');
    
    if (!N8N_API_KEY) {
        log('error', 'N8N_API_KEY не установлен!');
        log('info', 'Установите переменную окружения: export N8N_API_KEY="your-api-key"');
        process.exit(1);
    }
    
    try {
        // 1. Получить информацию о workflow
        const workflow = await getWorkflow(workflowId);
        console.log('');
        
        // 2. Активировать workflow если нужно
        await activateWorkflow(workflowId);
        console.log('');
        
        // 3. Получить последний execution до запуска
        log('info', 'Получение последнего execution до запуска...');
        const previousExecution = await getLastExecution(workflowId);
        const previousExecutionId = previousExecution?.id || null;
        
        if (previousExecution) {
            log('info', `Последний execution до запуска: ${previousExecution.id} (${previousExecution.finished ? 'finished' : 'running'})`);
        } else {
            log('info', 'Нет предыдущих executions');
        }
        console.log('');
        
        // 4. Попытка запустить через webhook (если есть)
        if (options.triggerWebhook !== false) {
            const webhookResult = await triggerWorkflowViaWebhook(workflowId, options.webhookData || {});
            if (webhookResult) {
                console.log('');
                // Ждём новый execution
                const newExecution = await waitForExecution(workflowId, previousExecutionId);
                const details = await getExecutionDetails(newExecution.id);
                console.log('');
                checkExecutionStatus(details);
                console.log('');
                return details;
            }
        }
        
        // 5. Если webhook не сработал, ждём ручного запуска
        if (options.waitForManual) {
            log('warning', 'Webhook не найден. Ожидание ручного запуска через Manual Trigger...');
            log('info', 'Запустите workflow вручную в n8n UI, скрипт будет ждать новый execution...');
            console.log('');
            
            const newExecution = await waitForExecution(workflowId, previousExecutionId);
            const details = await getExecutionDetails(newExecution.id);
            console.log('');
            checkExecutionStatus(details);
            console.log('');
            return details;
        } else {
            log('warning', 'Webhook не найден и waitForManual=false. Используйте Manual Trigger вручную.');
            log('info', 'Для автоматического ожидания установите: waitForManual=true');
            return null;
        }
        
    } catch (error) {
        log('error', `Ошибка: ${error.message}`);
        if (VERBOSE) {
            console.error(error);
        }
        process.exit(1);
    }
}

// CLI
if (require.main === module) {
    const workflowId = WORKFLOW_ID || process.argv[2];
    
    if (!workflowId) {
        console.error('Использование:');
        console.error('  node test_n8n_workflow.js <workflow-id>');
        console.error('');
        console.error('Или установите переменные окружения:');
        console.error('  export WORKFLOW_ID="your-workflow-id"');
        console.error('  export N8N_API_KEY="your-api-key"');
        console.error('  export N8N_API_URL="https://your-n8n-instance.com/api/v1"');
        console.error('');
        console.error('Опции:');
        console.error('  VERBOSE=true - подробный вывод');
        console.error('  TIMEOUT=120000 - timeout в миллисекундах');
        console.error('  POLL_INTERVAL=1000 - интервал проверки в миллисекундах');
        console.error('  waitForManual=true - ждать ручного запуска если webhook не найден');
        process.exit(1);
    }
    
    const options = {
        waitForManual: process.env.WAIT_FOR_MANUAL === 'true',
        triggerWebhook: process.env.TRIGGER_WEBHOOK !== 'false',
        webhookData: process.env.WEBHOOK_DATA ? JSON.parse(process.env.WEBHOOK_DATA) : {},
    };
    
    testWorkflow(workflowId, options)
        .then((result) => {
            if (result) {
                process.exit(result.finished && !result.data?.resultData?.error ? 0 : 1);
            } else {
                process.exit(0);
            }
        })
        .catch((error) => {
            console.error('Fatal error:', error);
            process.exit(1);
        });
}

module.exports = { testWorkflow, getWorkflow, getLastExecution, getExecutionDetails };


