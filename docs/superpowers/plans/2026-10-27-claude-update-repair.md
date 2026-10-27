# Claude 自动更新与 Pages 发布修复实施计划

> 日期：2026-10-27

## 目标

修复 Claude 自动更新在“检查日没有同日新事件”时误失败的问题；将官方资料更新和 GitHub Pages 发布拆分为权限独立的工作流；补收 2026-10-23 与 2026-10-26 的两条官方内容，并重新生成离线网页。

## 文件范围

- 修改 `tests/test_claude_evolution_panorama.py`：修正日期截止边界测试，保留未来事件保护。
- 修改 `tests/test_workflow_static.py`：分别验证更新工作流与发布工作流的触发器、权限和职责边界。
- 修改 `.github/workflows/update-claude-panorama.yml`：仅负责抓取、构建、测试、受限提交并调用发布工作流。
- 新增 `.github/workflows/deploy-claude-pages.yml`：监听 `main` 推送、手动触发和复用调用，负责构建、验证和 Pages 发布。
- 更新 `work/timeline-data.json`、`work/source-state.json`、`CHANGELOG.md`：纳入最新官方检查结果。
- 更新 `outputs/claude-evolution-panorama.html`：基于最新数据重新生成。
- 更新 `README.md`：同步目录、工作流职责、测试命令和自动发布说明。

## 实施步骤

1. 将本地 `main` 以 fast-forward 方式同步到远程最新提交，确认没有用户未提交改动。
2. 先修改日期边界测试，使其明确覆盖“最新事件早于 cutoff 合法”和“未来事件非法”；运行相关测试记录 RED。
3. 用最小改动修复日期边界断言，运行相关测试进入 GREEN。
4. 先补充工作流静态测试，要求更新与部署职责分离；运行测试记录 RED。
5. 拆分工作流：更新任务仅授予 `contents: write`，发布任务仅授予 `contents: read`、`pages: write`、`id-token: write`。
6. 运行官方来源更新器，收录符合规则的新内容；重新生成单文件 HTML。
7. 同步更新 README 与 CHANGELOG，确保说明和真实结构一致。
8. 运行完整单元测试、Python 语法检查、JSON 校验、YAML 基础解析或结构检查、内嵌 JavaScript 语法检查及 `git diff --check`。
9. 审阅全部差异，确保没有无关改动；本轮不创建提交、不推送，等待用户单独授权。

## 关键设计决策

- `cutoff` 表示页面允许收录的截止日，不代表该日必有事件，因此正确约束是每条事件日期 `<= cutoff`。
- 日期验证不能删除；测试将使用独立校验函数证明未来事件仍会被拒绝。
- 更新和发布采用两个工作流，降低定时抓取任务的 Pages 权限，并确保人工推送到 `main` 后也会发布。
- 不新增第三方依赖；继续使用 Python 标准库、原生 HTML/CSS/JavaScript 与 GitHub 官方 Actions。
- 自动收录内容继续遵循官方 HTTPS 域名、发布日期和保守摘要规则，不补写官方未明确说明的性能结论。
