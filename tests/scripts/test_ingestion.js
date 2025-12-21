#!/usr/bin/env node

/**
 * GenomAI — Ingestion Test Script (Node.js)
 * Версия: v1.0
 * Назначение: Автоматизированное тестирование STEP 01 — Ingestion
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

// Конфигурация
const WEBHOOK_URL = process.env.WEBHOOK_URL || 'http://localhost:5678/webhook/ingest/creative';
const PAYLOADS_DIR = path.join(__dirname, '../payloads/ingestion');
const VERBOSE = process.env.VERBOSE === 'true';

// Счетчики
let passed = 0;
let failed = 0;
let total = 0;

// Цвета для консоли
const colors = {
    reset: '\x1b[0m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
};

function log(level, message) {
    const prefix = {
        info: `${colors.blue}[INFO]${colors.reset}`,
        success: `${colors.green}[PASS]${colors.reset}`,
        error: `${colors.red}[FAIL]${colors.reset}`,
        warning: `${colors.yellow}[WARN]${colors.reset}`,
    }[level];
    console.log(`${prefix} ${message}`);
}

function makeRequest(url, payload) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const isHttps = urlObj.protocol === 'https:';
        const client = isHttps ? https : http;
        
        const options = {
            hostname: urlObj.hostname,
            port: urlObj.port || (isHttps ? 443 : 80),
            path: urlObj.pathname + urlObj.search,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const req = client.request(options, (res) => {
            let body = '';
            res.on('data', (chunk) => {
                body += chunk;
            });
            res.on('end', () => {
                resolve({
                    statusCode: res.statusCode,
                    body: body,
                    headers: res.headers,
                });
            });
        });

        req.on('error', (error) => {
            reject(error);
        });

        req.write(JSON.stringify(payload));
        req.end();
    });
}

async function testRequest(testName, payloadFile, expectedStatus, expectedBehavior) {
    total++;
    
    log('info', `Testing: ${testName}`);
    
    if (!fs.existsSync(payloadFile)) {
        log('error', `Payload file not found: ${payloadFile}`);
        failed++;
        return false;
    }
    
    const payload = JSON.parse(fs.readFileSync(payloadFile, 'utf8'));
    
    if (VERBOSE) {
        log('info', `Payload: ${JSON.stringify(payload, null, 2)}`);
    }
    
    try {
        const response = await makeRequest(WEBHOOK_URL, payload);
        
        if (VERBOSE) {
            log('info', `HTTP Code: ${response.statusCode}`);
            log('info', `Response: ${response.body}`);
        }
        
        if (response.statusCode === expectedStatus) {
            log('success', `${testName} — HTTP ${response.statusCode} (expected ${expectedStatus})`);
            passed++;
            return true;
        } else {
            log('error', `${testName} — HTTP ${response.statusCode} (expected ${expectedStatus})`);
            failed++;
            return false;
        }
    } catch (error) {
        log('error', `${testName} — Error: ${error.message}`);
        failed++;
        return false;
    }
}

async function runTests() {
    console.log('==========================================');
    console.log('GenomAI — Ingestion Test Suite');
    console.log('==========================================');
    console.log(`Webhook URL: ${WEBHOOK_URL}`);
    console.log(`Payloads Dir: ${PAYLOADS_DIR}`);
    console.log('');
    
    if (!WEBHOOK_URL || WEBHOOK_URL.includes('localhost')) {
        log('warning', 'WEBHOOK_URL not set. Using default.');
        log('warning', 'Set WEBHOOK_URL environment variable to test against your n8n instance');
        console.log('');
    }
    
    // Тест 1: Happy Path
    await testRequest(
        'Happy Path',
        path.join(PAYLOADS_DIR, 'happy_path.json'),
        200,
        'Creative should be created'
    );
    
    // Тест 2: Idempotency
    log('info', 'Waiting 1 second before idempotency test...');
    await new Promise(resolve => setTimeout(resolve, 1000));
    await testRequest(
        'Idempotency',
        path.join(PAYLOADS_DIR, 'idempotency.json'),
        200,
        'Duplicate should not be created'
    );
    
    // Тест 3: Edge Case — один video_url, разные tracker_id
    await testRequest(
        'Edge Case: Same video, different tracker (1)',
        path.join(PAYLOADS_DIR, 'edge_same_video_different_tracker_1.json'),
        200,
        'Should create different creative'
    );
    
    await testRequest(
        'Edge Case: Same video, different tracker (2)',
        path.join(PAYLOADS_DIR, 'edge_same_video_different_tracker_2.json'),
        200,
        'Should create different creative'
    );
    
    // Тест 4: Edge Case — разные video_url, один tracker_id
    await testRequest(
        'Edge Case: Different video, same tracker (1)',
        path.join(PAYLOADS_DIR, 'edge_different_video_same_tracker_1.json'),
        200,
        'Should create different creative'
    );
    
    await testRequest(
        'Edge Case: Different video, same tracker (2)',
        path.join(PAYLOADS_DIR, 'edge_different_video_same_tracker_2.json'),
        200,
        'Should create different creative'
    );
    
    // Тест 5: Invalid — отсутствует video_url
    await testRequest(
        'Invalid: Missing video_url',
        path.join(PAYLOADS_DIR, 'invalid_missing_video_url.json'),
        400,
        'Should reject missing field'
    );
    
    // Тест 6: Invalid — отсутствует tracker_id
    await testRequest(
        'Invalid: Missing tracker_id',
        path.join(PAYLOADS_DIR, 'invalid_missing_tracker_id.json'),
        400,
        'Should reject missing field'
    );
    
    // Тест 7: Invalid — пустой video_url
    await testRequest(
        'Invalid: Empty video_url',
        path.join(PAYLOADS_DIR, 'invalid_empty_video_url.json'),
        400,
        'Should reject empty field'
    );
    
    // Тест 8: Invalid — пустой tracker_id
    await testRequest(
        'Invalid: Empty tracker_id',
        path.join(PAYLOADS_DIR, 'invalid_empty_tracker_id.json'),
        400,
        'Should reject empty field'
    );
    
    // Тест 9: Invalid — неверный source_type
    await testRequest(
        'Invalid: Wrong source_type',
        path.join(PAYLOADS_DIR, 'invalid_wrong_source_type.json'),
        400,
        'Should reject wrong source_type'
    );
    
    // Тест 10: Garbage Input
    await testRequest(
        'Garbage Input',
        path.join(PAYLOADS_DIR, 'garbage_input.json'),
        400,
        'Should reject invalid payload'
    );
    
    // Итоги
    console.log('');
    console.log('==========================================');
    console.log('Test Results');
    console.log('==========================================');
    console.log(`Total:  ${total}`);
    console.log(`${colors.green}Passed: ${passed}${colors.reset}`);
    console.log(`${colors.red}Failed: ${failed}${colors.reset}`);
    console.log('');
    
    if (failed === 0) {
        console.log(`${colors.green}All tests passed! ✅${colors.reset}`);
        process.exit(0);
    } else {
        console.log(`${colors.red}Some tests failed. ❌${colors.reset}`);
        process.exit(1);
    }
}

// Запуск тестов
runTests().catch((error) => {
    console.error('Fatal error:', error);
    process.exit(1);
});


