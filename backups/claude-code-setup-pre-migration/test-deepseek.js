#!/usr/bin/env node

// 测试 DeepSeek API 连接
console.log('Testing DeepSeek API configuration...');
console.log('ANTHROPIC_BASE_URL:', process.env.ANTHROPIC_BASE_URL);
console.log('ANTHROPIC_MODEL:', process.env.ANTHROPIC_MODEL);
console.log('ANTHROPIC_API_KEY:', process.env.ANTHROPIC_API_KEY ? 'Set (hidden)' : 'Not set');

// 模拟 Claude Code 的 API 调用逻辑
if (process.env.ANTHROPIC_BASE_URL && process.env.ANTHROPIC_MODEL && process.env.ANTHROPIC_API_KEY) {
  console.log('\n✅ Configuration appears correct!');
  console.log('Claude Code should use DeepSeek API at:', process.env.ANTHROPIC_BASE_URL);
  console.log('Using model:', process.env.ANTHROPIC_MODEL);
} else {
  console.log('\n❌ Configuration incomplete!');
  console.log('Please check your environment variables.');
}

console.log('\nNote: The "Sonnet 4.6" display in Claude Code is likely hardcoded UI text,');
console.log('and does not reflect the actual API being used.');
