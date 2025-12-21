#!/usr/bin/env node

/**
 * GenomAI — Simple Webhook Test Script
 * Версия: v1.0
 * Назначение: Супер простая проверка webhook'ов
 * 
 * Использование:
 *   node test_webhook_simple.js <webhook-url>
 *   node test_webhook_simple.js <workflow-id>
 */

const https = require('https');
const http = require('http');
const path = require('path');

// Опциональная загрузка dotenv
try {
    require('dotenv').config({ path: path.join(__dirname, '../../tests/config/.env') });
} catch (e) {
    // dotenv не установлен, используем переменные окружения напрямую
}

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
                'User-Agent': 'GenomAI-Webhook-Test',
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
                    parsedBody = body ? JSON.parse(body) : body;
                } catch (e) {
                    parsedBody = body;
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
        
        req.setTimeout(10000, () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });
        
        req.end();
    });
}

// Получить workflow через API
async function getWorkflow(workflowId) {
    try {
        const response = await makeRequest(`${N8N_API_URL}/workflows/${workflowId}`, {
            headers: {
                'X-N8N-API-KEY': N8N_API_KEY,
            },
        });
        
        if (response.statusCode === 200) {
            return response.body;
        }
        throw new Error(`HTTP ${response.statusCode}: ${JSON.stringify(response.body)}`);
    } catch (error) {
        log('error', `Ошибка при получении workflow: ${error.message}`);
        throw error;
    }
}

// Найти webhook URL из workflow
function findWebhookUrl(workflow) {
    const webhookNode = workflow.nodes?.find(node => 
        node.type === 'n8n-nodes-base.webhook' || 
        node.type === 'n8n-nodes-base.webhookTrigger'
    );
    
    if (!webhookNode) {
        return null;
    }
    
    const baseUrl = N8N_API_URL.replace('/api/v1', '');
    
    // В n8n webhook URL формируется так:
    // 1. Если есть path: https://kazamaqwe.app.n8n.cloud/webhook/{workflow-id}/{path}
    // 2. Если path нет: https://kazamaqwe.app.n8n.cloud/webhook/{workflow-id}
    // 3. Или через webhookId: https://kazamaqwe.app.n8n.cloud/webhook/{webhook-id}
    
    // Проверяем path (может быть в разных местах)
    const webhookPath = webhookNode.parameters?.path || 
                       webhookNode.parameters?.path?.value || 
                       webhookNode.parameters?.options?.path ||
                       '';
    
    // Проверяем webhookId (если есть)
    const webhookId = webhookNode.webhookId || webhookNode.parameters?.webhookId;
    
    if (webhookPath && webhookPath.trim() !== '') {
        // Убираем ведущий слэш, если есть
        const cleanPath = webhookPath.startsWith('/') ? webhookPath.slice(1) : webhookPath;
        return `${baseUrl}/webhook/${workflow.id}/${cleanPath}`;
    } else if (webhookId) {
        // Используем webhookId, если path нет
        return `${baseUrl}/webhook/${webhookId}`;
    } else {
        // Используем только workflow ID
        return `${baseUrl}/webhook/${workflow.id}`;
    }
}

// Простой тест webhook
async function testWebhook(webhookUrl, payload = {}) {
    log('info', `Тестирование webhook: ${webhookUrl}`);
    log('info', `Payload: ${JSON.stringify(payload, null, 2)}`);
    console.log('');
    
    try {
        const response = await makeRequest(webhookUrl, {
            method: 'POST',
            body: payload,
        });
        
        log('info', `Status Code: ${response.statusCode}`);
        log('info', `Response: ${JSON.stringify(response.body, null, 2)}`);
        
        if (response.statusCode >= 200 && response.statusCode < 300) {
            log('success', '✅ Webhook работает!');
            return { success: true, response };
        } else {
            log('error', `❌ Webhook вернул ошибку: ${response.statusCode}`);
            return { success: false, response };
        }
    } catch (error) {
        log('error', `❌ Ошибка при тестировании webhook: ${error.message}`);
        return { success: false, error: error.message };
    }
}

// Основная функция
async function main() {
    const arg = process.argv[2];
    
    if (!arg) {
        console.error('Использование:');
        console.error('  node test_webhook_simple.js <webhook-url>');
        console.error('  node test_webhook_simple.js <workflow-id>');
        console.error('');
        console.error('Примеры:');
        console.error('  node test_webhook_simple.js https://kazamaqwe.app.n8n.cloud/webhook/dvZvUUmhtPzYOK7X/ingest/creative');
        console.error('  node test_webhook_simple.js dvZvUUmhtPzYOK7X');
        console.error('');
        console.error('Переменные окружения:');
        console.error('  N8N_API_URL - URL n8n API (по умолчанию: https://kazamaqwe.app.n8n.cloud/api/v1)');
        console.error('  N8N_API_KEY - API ключ n8n (опционально, для получения workflow)');
        process.exit(1);
    }
    
    console.log('='.repeat(60));
    log('header', 'GenomAI — Simple Webhook Test');
    console.log('='.repeat(60));
    console.log('');
    
    let webhookUrl = arg;
    
    // Если это workflow ID, получаем webhook URL из workflow
    if (!arg.startsWith('http')) {
        log('info', `Получение webhook URL из workflow: ${arg}`);
        
        if (!N8N_API_KEY) {
            log('error', 'N8N_API_KEY не установлен!');
            log('info', 'Установите переменную окружения: export N8N_API_KEY="your-api-key"');
            process.exit(1);
        }
        
        try {
            const workflow = await getWorkflow(arg);
            webhookUrl = findWebhookUrl(workflow);
            
            if (!webhookUrl) {
                log('error', 'Webhook trigger не найден в workflow');
                log('info', 'Убедитесь, что workflow содержит Webhook Trigger node');
                process.exit(1);
            }
            
            log('success', `Webhook URL найден: ${webhookUrl}`);
        } catch (error) {
            log('error', `Ошибка: ${error.message}`);
            process.exit(1);
        }
    }
    
    console.log('');
    
    // Тестируем webhook с простым payload
    const testPayload = {
        video_url: 'https://example.com/test/video/123',
        tracker_id: 'KT-TEST-123',
        source_type: 'user',
    };
    
    const result = await testWebhook(webhookUrl, testPayload);
    
    console.log('');
    log('header', '='.repeat(60));
    
    if (result.success) {
        log('success', '✅ Webhook работает корректно!');
        process.exit(0);
    } else {
        log('error', '❌ Webhook не работает или вернул ошибку');
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

module.exports = { testWebhook, findWebhookUrl, getWorkflow };

