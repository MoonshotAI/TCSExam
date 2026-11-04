const sections = [
  ['Start here', '开始使用', [
    ['', 'Documentation guide', '文档导读'], ['overview', 'Project overview', '项目概览'],
    ['getting-started', 'Quickstart', '快速开始'], ['running-suites', 'Run Lite or Full', '运行 Lite 或 Full'], ['tasks', 'Task catalogue', '题目目录'],
  ]],
  ['Configure and run', '配置与运行', [
    ['running', 'Run configuration', '运行配置'], ['resources', 'Prepare resources', '准备资源'],
    ['runtime-availability', 'Host requirements', '主机要求'], ['solver-protocols', 'Solver protocols', 'Solver 协议'],
    ['offline-adapters', 'Offline adapters', 'Offline 适配器'],
  ]],
  ['Understand evaluation', '理解评测', [
    ['scoring', 'Scoring and results', '计分与结果'],
    ['judge-execution-isolation', 'Judge isolation checks', '判分隔离检查'],
    ['oracle-answers', 'Reference answers', '标准答案'], ['citation', 'Cite TCSExam', '引用 TCSExam'],
  ]],
  ['Deploy and maintain', '部署与维护', [
    ['solver-backend', 'Backend overview', '后端概览'], ['backend/docker', 'Docker backend', 'Docker 后端'],
    ['backend/service', 'Service configuration', '服务配置'], ['backend/public-images', 'Public self-test images', '公开自测镜像'],
  ]],
  ['Contribute', '参与贡献', [
    ['contributing', 'Contribution guide', '贡献指南'], ['source-delivery', 'Source packages', '源码包'],
    ['licenses', 'Licensing', '许可'], ['licenses/distribution', 'Distribution conditions', '分发条件'],
    ['licenses/THIRD_PARTY_NOTICES', 'Third-party notices', '第三方声明'],
  ]],
];
const detailed = [
  ['licenses/full-review', 'Component records', '组件记录'],
  ['licenses/cpsolver-source', 'CPSolver source and build', 'CPSolver 源码与构建'],
  ['resources/assets', 'Build resources', '构建资源'], ['environments/harbor', 'Harbor environment', 'Harbor 环境'],
  ['environments/lean-base', 'Lean environment', 'Lean 环境'],
  ['environments/lean-base/NOTICE', 'Lean environment notices', 'Lean 环境声明'],
  ['environments/lean-base/lean-components', 'Lean component licenses', 'Lean 组件许可'],
  ['environments/lean-base/browser-components', 'Browser component materials', '浏览器组件材料'],
  ['environments/lean-base/graphviz-epl', 'Graphviz materials', 'Graphviz 材料'],
  ['environments/lean-base/graphviz-epl/SOURCE-OFFER', 'Graphviz source offer', 'Graphviz 源码提供声明'],
  ['environments/lean-base/proofwidgets-npm', 'ProofWidgets npm materials', 'ProofWidgets npm 材料'],
];
export function sidebar(lang) {
  const zh = lang === 'zh';
  const item = ([route, en, cn]) => ({ text: zh ? cn : en, link: `/${zh ? 'zh/' : ''}${route ? `${route}/` : ''}` });
  return [
    ...sections.map(([en, cn, items]) => ({ text: zh ? cn : en, ...(en === 'Deploy and maintain' ? { collapsed: true } : {}), items: items.map(item) })),
    { text: zh ? '依赖与许可详录' : 'Dependency and license details', collapsed: true, items: detailed.map(item) },
  ];
}
