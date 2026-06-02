# ai-clinic-engine

AI 驱动的诊所 / 行业内容生产引擎。支持关键词研究、文章生成、质量检查、RAG 知识库、ReAct 事实核验与微信发布。

## 环境要求

- Python 3.10+

## 快速开始

```bash
# 1. 安装依赖
pip install -e .

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填写 ANTHROPIC_AUTH_TOKEN 或 OPENAI_API_KEY

# 3. Web 界面（推荐）
python web.py
# 或 Windows 双击 start.bat
# 访问 http://localhost:8080
```

## CLI

```bash
clinic-engine generate --topic "春季过敏防护"
clinic-engine check --file output/article.md
clinic-engine keywords --seed "儿童疫苗"
```

## 配置说明

| 变量 | 说明 |
|---|---|
| `LLM_BACKEND` | `anthropic` 或 `openai` |
| `ANTHROPIC_AUTH_TOKEN` | Anthropic 兼容 API Token |
| `OPENAI_API_KEY` | OpenAI 兼容 API Key |
| `INDUSTRY` | `medical`（诊所）或 `ai_career` |
| `CLINIC_NAME` | 机构名称 |
| `SERPAPI_KEY` | 可选，关键词研究 |
| `WECHAT_APP_ID` / `WECHAT_APP_SECRET` | 可选，微信公众号发布 |

完整变量见 `.env.example`。

## 项目结构

```
ai-clinic-engine/
├── clinic_engine/       # 核心引擎（生成、检查、RAG、发布）
├── templates/           # Web 模板
├── static/              # 静态资源
├── scripts/             # 辅助脚本
├── web.py               # Web 入口
└── start.bat            # Windows 一键启动
```

## 安全提示

- 勿将 `.env` 提交到 Git；密钥仅放在本地环境变量文件中。
