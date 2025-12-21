#!/usr/bin/env node

/**
 * GenomAI — Test tableId Auto-Fix Rule
 * Тестирование автоматического исправления tableId в Supabase узлах
 */

const { getWorkflow } = require('./test_n8n_workflow.js');

// Конфигурация
const WORKFLOW_ID = process.env.WORKFLOW_ID || 'YT2d7z5h9bPy1R4v';

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

/**
 * Проверка формата tableId в Supabase узле
 */
function checkTableIdFormat(node) {
    if (node.type !== 'n8n-nodes-base.supabase') {
        return { isValid: null, reason: 'not_supabase_node' };
    }

    const tableId = node.parameters?.tableId;

    if (!tableId) {
        return { isValid: false, reason: 'missing_tableId', nodeName: node.name };
    }

    // Проверяем, является ли tableId объектом с __rl
    if (typeof tableId === 'object' && tableId.__rl === true) {
        return {
            isValid: false,
            reason: 'object_format',
            nodeName: node.name,
            currentFormat: 'object',
            expectedFormat: 'expression',
            tableName: tableId.value
        };
    }

    // Проверяем, является ли tableId выражением
    if (typeof tableId === 'string' && tableId.startsWith('={{') && tableId.includes('"')) {
        return { isValid: true, reason: 'expression_format', nodeName: node.name };
    }

    // Простая строка (может работать, но не рекомендуется)
    if (typeof tableId === 'string') {
        return {
            isValid: true,
            reason: 'string_format',
            nodeName: node.name,
            warning: 'Should use expression format: ={{ "table_name" }}'
        };
    }

    return { isValid: false, reason: 'unknown_format', nodeName: node.name };
}

/**
 * Тестирование правила автоматического исправления
 */
async function testTableIdAutoFix() {
    log('header', '='.repeat(60));
    log('header', 'Testing tableId Auto-Fix Rule');
    log('header', '='.repeat(60));

    try {
        // 1. Получить workflow
        log('info', `Reading workflow: ${WORKFLOW_ID}`);
        const workflowData = await getWorkflow(WORKFLOW_ID);
        
        if (!workflowData || !workflowData.nodes) {
            log('error', 'Failed to get workflow data');
            process.exit(1);
        }

        log('success', `Workflow loaded: ${workflowData.name || WORKFLOW_ID}`);
        log('info', `Total nodes: ${workflowData.nodes.length}`);

        // 2. Найти все Supabase узлы
        const supabaseNodes = workflowData.nodes.filter(
            node => node.type === 'n8n-nodes-base.supabase'
        );

        log('info', `Found ${supabaseNodes.length} Supabase nodes`);

        if (supabaseNodes.length === 0) {
            log('warning', 'No Supabase nodes found in workflow');
            return;
        }

        // 3. Проверить каждый Supabase узел
        log('header', '-'.repeat(60));
        log('header', 'Checking Supabase nodes:');
        log('header', '-'.repeat(60));

        const results = [];
        let issuesFound = 0;

        for (const node of supabaseNodes) {
            const check = checkTableIdFormat(node);
            results.push({ node, check });

            if (check.isValid === false) {
                issuesFound++;
                log('error', `❌ ${node.name} (${node.id}):`);
                log('error', `   Reason: ${check.reason}`);
                if (check.tableName) {
                    log('error', `   Table: ${check.tableName}`);
                    log('error', `   Current: object format`);
                    log('error', `   Expected: ={{ "${check.tableName}" }}`);
                }
            } else if (check.warning) {
                log('warning', `⚠️  ${node.name} (${node.id}):`);
                log('warning', `   ${check.warning}`);
            } else {
                log('success', `✅ ${node.name} (${node.id}):`);
                log('success', `   Format: ${check.reason}`);
                if (node.parameters?.tableId) {
                    log('debug', `   Value: ${node.parameters.tableId}`);
                }
            }
        }

        // 4. Итоговый отчет
        log('header', '='.repeat(60));
        log('header', 'Test Results:');
        log('header', '='.repeat(60));

        const validNodes = results.filter(r => r.check.isValid === true).length;
        const invalidNodes = results.filter(r => r.check.isValid === false).length;
        const warningNodes = results.filter(r => r.check.warning).length;

        log('info', `Total Supabase nodes: ${supabaseNodes.length}`);
        log('success', `✅ Valid nodes: ${validNodes}`);
        if (warningNodes > 0) {
            log('warning', `⚠️  Nodes with warnings: ${warningNodes}`);
        }
        if (invalidNodes > 0) {
            log('error', `❌ Invalid nodes: ${invalidNodes}`);
        }

        // 5. Рекомендации
        if (invalidNodes > 0) {
            log('header', '-'.repeat(60));
            log('error', 'ACTION REQUIRED:');
            log('error', 'The following nodes need to be fixed:');
            log('header', '-'.repeat(60));
            
            results
                .filter(r => r.check.isValid === false)
                .forEach(({ node, check }) => {
                    log('error', `\nNode: ${node.name} (${node.id})`);
                    log('error', `Table: ${check.tableName || 'unknown'}`);
                    log('error', `Fix: tableId should be ={{ "${check.tableName || 'table_name'}" }}`);
                });

            log('header', '-'.repeat(60));
            log('info', 'Use n8n_update_partial_workflow to fix these nodes');
            process.exit(1);
        } else {
            log('header', '-'.repeat(60));
            log('success', '✅ All Supabase nodes have correct tableId format!');
            log('success', '✅ Auto-fix rule is working correctly!');
            log('header', '-'.repeat(60));
            process.exit(0);
        }

    } catch (error) {
        log('error', `Test failed: ${error.message}`);
        console.error(error);
        process.exit(1);
    }
}

// Запуск теста
if (require.main === module) {
    testTableIdAutoFix();
}

module.exports = { testTableIdAutoFix, checkTableIdFormat };
