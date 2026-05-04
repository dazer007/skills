#!/usr/bin/env node
/**
 * summarize-config - 配置 summarize CLI 工具
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const CONFIG_PATH = path.join(os.homedir(), '.summarize', 'config.json');

// 常用代理配置模板
const PROXY_TEMPLATES = {
  dashscope: {
    name: '阿里云 DashScope (Anthropic 兼容)',
    baseUrl: 'https://coding.dashscope.aliyuncs.com/apps/anthropic',
    provider: 'anthropic',
    models: ['glm-5', 'qwen-plus', 'qwen-turbo', 'qwen-max']
  },
  aicodemirror: {
    name: 'aicodemirror (Claude Code 代理)',
    baseUrl: 'https://api.aicodemirror.com/api/claudecode',
    provider: 'openai',
    models: ['claude-3-5-sonnet-20241022', 'claude-sonnet-4-20250514', 'claude-opus-4-20250514']
  },
  official: {
    name: 'Anthropic 官方 API',
    baseUrl: 'https://api.anthropic.com',
    provider: 'anthropic',
    models: ['claude-3-5-sonnet-20241022', 'claude-sonnet-4-20250514', 'claude-opus-4-20250514']
  }
};

function readConfig() {
  if (!fs.existsSync(CONFIG_PATH)) {
    return null;
  }
  try {
    const content = fs.readFileSync(CONFIG_PATH, 'utf8');
    return JSON.parse(content);
  } catch (e) {
    return { error: e.message };
  }
}

function writeConfig(config) {
  const dir = path.dirname(CONFIG_PATH);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2));
}

function validateConfig(config) {
  const errors = [];

  // 检查必需字段
  if (!config.model) {
    errors.push('缺少 model 字段');
  } else if (!config.model.includes('/')) {
    errors.push('model 格式错误，必须为 provider/model-name 格式');
  }

  // 检查 JSON 语法（通过重新解析）
  try {
    JSON.parse(JSON.stringify(config));
  } catch (e) {
    errors.push(`JSON 语法错误: ${e.message}`);
  }

  return errors;
}

function fixConfig(config) {
  // 移除可能的尾随逗号问题（通过重新序列化）
  const fixed = JSON.parse(JSON.stringify(config));
  return fixed;
}

function showConfig() {
  const config = readConfig();
  if (config === null) {
    console.log('配置文件不存在:', CONFIG_PATH);
    return;
  }
  if (config.error) {
    console.log('配置文件有错误:', config.error);
    console.log('\n原始内容:');
    console.log(fs.readFileSync(CONFIG_PATH, 'utf8'));
    return;
  }
  console.log('当前配置:');
  console.log(JSON.stringify(config, null, 2));
}

function validateConfigFile() {
  const config = readConfig();
  if (config === null) {
    console.log('❌ 配置文件不存在');
    return false;
  }
  if (config.error) {
    console.log('❌ JSON 解析错误:', config.error);
    return false;
  }

  const errors = validateConfig(config);
  if (errors.length === 0) {
    console.log('✅ 配置文件有效');
    return true;
  } else {
    console.log('❌ 配置有问题:');
    errors.forEach(e => console.log('  -', e));
    return false;
  }
}

function fixConfigFile() {
  const config = readConfig();
  if (config === null) {
    console.log('配置文件不存在，无法修复');
    return;
  }
  if (config.error) {
    // 尝试修复常见的尾随逗号问题
    let content = fs.readFileSync(CONFIG_PATH, 'utf8');
    // 移除对象/数组末尾的逗号
    content = content.replace(/,\s*}/g, '}').replace(/,\s*]/g, ']');
    try {
      const fixed = JSON.parse(content);
      writeConfig(fixed);
      console.log('✅ 已修复配置文件');
      showConfig();
    } catch (e) {
      console.log('❌ 无法自动修复:', e.message);
    }
    return;
  }
  console.log('配置文件无需修复');
}

function setAnthropic(baseUrl, apiKey) {
  const config = readConfig() || {};
  config.anthropic = { baseUrl };
  if (!config.apiKeys) config.apiKeys = {};
  config.apiKeys.anthropic = apiKey;
  writeConfig(config);
  console.log('✅ 已设置 Anthropic 配置');
  showConfig();
}

function setOpenai(baseUrl, apiKey) {
  const config = readConfig() || {};
  config.openai = { baseUrl };
  if (!config.apiKeys) config.apiKeys = {};
  config.apiKeys.openai = apiKey;
  writeConfig(config);
  console.log('✅ 已设置 OpenAI 配置');
  showConfig();
}

function switchProxy(proxyName, model) {
  const template = PROXY_TEMPLATES[proxyName];
  if (!template) {
    console.log('❌ 未知的代理:', proxyName);
    console.log('可用代理:', Object.keys(PROXY_TEMPLATES).join(', '));
    return;
  }

  const config = readConfig() || {};
  const effectiveModel = model || template.models[0];

  // 设置 baseUrl
  if (template.provider === 'anthropic') {
    config.anthropic = { baseUrl: template.baseUrl };
  } else {
    config.openai = { baseUrl: template.baseUrl };
  }

  // 设置 model
  config.model = `${template.provider}/${effectiveModel}`;

  writeConfig(config);
  console.log(`✅ 已切换到 ${template.name}`);
  console.log(`   baseUrl: ${template.baseUrl}`);
  console.log(`   model: ${config.model}`);
}

function showHelp() {
  console.log(`
summarize-config - 配置 summarize CLI 工具

用法:
  summarize-config show              显示当前配置
  summarize-config validate          验证配置文件
  summarize-config fix               自动修复配置错误
  summarize-config set-anthropic <baseUrl> <apiKey>   设置 Anthropic 代理
  summarize-config set-openai <baseUrl> <apiKey>      设置 OpenAI 代理
  summarize-config switch <proxy> [model]  切换代理 (dashscope/aicodemirror/official)

示例:
  summarize-config show
  summarize-config switch aicodemirror claude-3-5-sonnet-20241022
  summarize-config switch dashscope
  summarize-config set-anthropic https://api.anthropic.com sk-ant-xxx
`);
}

// 主入口
const args = process.argv.slice(2);
const command = args[0];

switch (command) {
  case 'show':
    showConfig();
    break;
  case 'validate':
    validateConfigFile();
    break;
  case 'fix':
    fixConfigFile();
    break;
  case 'set-anthropic':
    setAnthropic(args[1], args[2]);
    break;
  case 'set-openai':
    setOpenai(args[1], args[2]);
    break;
  case 'switch':
    switchProxy(args[1], args[2]);
    break;
  case 'help':
  case '--help':
  case '-h':
    showHelp();
    break;
  default:
    if (command) {
      console.log('未知命令:', command);
    }
    showHelp();
}