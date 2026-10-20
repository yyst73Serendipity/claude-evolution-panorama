# Claude 演进全景

一个以 Anthropic、Claude、Claude Platform 官方资料为主的数据化项目，用单文件交互网页梳理 Claude 从早期研究基础到 2026-10-15 的模型、产品、开发者生态和订阅计划演进。

## ✨ 功能介绍

- 86 条关键时间线事件，覆盖 2022-12 至 2026-10-15。
- 可按关键词、年份、类别和时间顺序筛选，支持展开或收起全部详情。
- 每条事件说明更新时间、更新类别、相对前代变化、优化重点、适用范围、战略意义和官方来源。
- 提供模型谱系、产品全景、订阅计划、API 标准价格、模型退役迁移和战略转折专题。
- 单文件 HTML，CSS、JavaScript 和时间线数据全部内嵌，不依赖 CDN、外部字体或第三方脚本。
- 支持深浅主题、键盘操作、移动端布局、打印样式和 `prefers-reduced-motion`。

## 📁 项目目录结构

```text
claude/
├── .github/
│   └── workflows/
│       └── update-claude-panorama.yml
├── .gitignore
├── AGENTS.md
├── CHANGELOG.md
├── README.md
├── outputs/
│   └── claude-evolution-panorama.html
├── tests/
│   ├── test_auto_update.py
│   └── test_claude_evolution_panorama.py
└── work/
    ├── build-page.py
    ├── source-config.json
    ├── source-state.json
    ├── timeline-data.json
    └── update-claude-panorama.py
```

## 🧰 技术栈

- Python 3 标准库：数据校验、统计和静态页面构建
- 原生 HTML5 / CSS3 / JavaScript：页面结构、响应式视觉和本地交互
- `unittest`：交付文件、内容覆盖、日期边界、链接安全和单文件依赖测试

项目不引入第三方运行时依赖。

## 🚀 生成和使用方式

在项目根目录执行：

```bash
python3 work/build-page.py
```

生成文件：

```text
outputs/claude-evolution-panorama.html
```

直接使用现代浏览器打开该文件即可。页面不需要本地服务器，也不会在运行时请求时间线数据。

## 🧪 测试方式

```bash
python3 -m unittest tests/test_claude_evolution_panorama.py -v
```

测试覆盖：

- 数据规模、事件类别和日期截止边界
- 必要章节、模型、产品及价格快照
- 搜索、筛选、排序、重置和展开控件
- 官方 HTTPS 来源及新窗口安全属性
- 无外部 CSS、JavaScript、CDN 或网络字体依赖
- 跳转链接、无障碍提示、减少动画和打印样式

## 📚 数据来源与日期口径

- 主要来源：Anthropic News / Research、Claude 官方资源、Claude Help Center、Claude Platform 文档。
- 数据截止日期：**2026-10-15**。
- 2026-10-16 及以后发布的事件不纳入时间线。
- 订阅价格按美国公开网页快照整理；地区、税费和企业合同可能不同。
- API 表格展示标准输入/输出价格，不包含 Batch、Prompt Caching、Fast mode、区域端点或云平台差异。
- 模型退役信息用于全景梳理；生产迁移前应再次核对官方 deprecations 页面。

## 🔄 全自动更新与发布

仓库包含 GitHub Actions 工作流 `.github/workflows/update-claude-panorama.yml`：

1. 每天北京时间 08:00 自动检查 Anthropic News、Claude 官方资源、应用与 Platform 发布说明、模型弃用页面和价格页面。
2. 新文章仅在官方 HTTPS 域名、发布时间晚于现有数据且不晚于检查日时加入时间线。
3. 自动生成的事件会显示“自动收录”，描述只使用官方页面标题和摘要，不猜测官方未明确说明的指标。
4. 定价、发布说明和弃用页面通过稳定正文摘要监测变化；检测到变化时生成保守的页面更新记录。
5. 自动重建单文件网页并运行完整测试；任何步骤失败都会阻止提交和发布。
6. 测试通过后由 Actions 提交数据与网页，并发布到 GitHub Pages。

也可在 GitHub 仓库的 **Actions → 更新并发布 Claude 演进全景 → Run workflow** 手动触发。

本地手动检查需要能够访问官方站点：

```bash
python3 work/update-claude-panorama.py
python3 work/build-page.py
python3 -m unittest discover -s tests -p "test_*.py" -v
```

### 首次启用 GitHub Pages

推送仓库后，在 GitHub 打开：

```text
Settings → Pages → Build and deployment → Source → GitHub Actions
```

首次运行工作流成功后，站点地址为：

```text
https://yyst73serendipity.github.io/claude-evolution-panorama/
```

自动更新器不用 API Key，也不会把密钥写入网页。由于完全自动模式依赖官方页面结构，建议定期查看 Actions 运行结果和 `CHANGELOG.md`。
