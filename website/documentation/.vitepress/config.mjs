import { defineConfig } from 'vitepress';
import { getSettings } from '../scripts/settings.mjs';
import { sidebar } from '../scripts/navigation.mjs';
import { searchOptions } from '../scripts/search.mjs';
const settings = getSettings();

export default defineConfig({
  srcDir: '.generated',
  base: settings.docsBase,
  title: 'TCSExam Docs',
  description: 'Run TCSExam evaluations, understand verified results, and maintain the judging backend.',
  lang: 'en',
  cleanUrls: false,
  lastUpdated: false,
  head: [
    ['meta', { name: 'theme-color', content: '#286a93' }],
    ['link', { rel: 'icon', type: 'image/svg+xml', href: `${settings.docsBase}brand/favicon.svg` }],
  ],
  markdown: { lineNumbers: false },
  locales: {
    root: { label: 'English', lang: 'en', themeConfig: {
      siteTitle: '<span class="docs-title-suffix">Docs</span>',
      nav: [{ text: 'Documentation', link: '/' }, { text: 'Get started', link: '/getting-started/' }],
      sidebar: sidebar('en'),
      outline: { label: 'On this page', level: [2, 3] },
      docFooter: { prev: 'Previous page', next: 'Next page' },
      editLink: { pattern: ({ frontmatter }) => frontmatter.sourceUrl, text: 'View Markdown source on GitHub' },
    } },
    zh: { label: '简体中文', lang: 'zh-CN', description: '运行 TCSExam 评测，理解经验证的结果，并维护判分后端。', themeConfig: {
      siteTitle: '<span class="docs-title-suffix">文档</span>',
      footer: { message: '原创文档采用 CC BY 4.0 许可；第三方材料保留各自条款。' },
      nav: [{ text: '文档', link: '/zh/' }, { text: '开始使用', link: '/zh/getting-started/' }],
      sidebar: sidebar('zh'),
      outline: { label: '本页目录', level: [2, 3] },
      docFooter: { prev: '上一页', next: '下一页' },
      sidebarMenuLabel: '文档目录', returnToTopLabel: '返回顶部', darkModeSwitchLabel: '外观',
      editLink: { pattern: ({ frontmatter }) => frontmatter.sourceUrl, text: '在 GitHub 查看 Markdown 原文' },
    } },
  },
  themeConfig: {
    logo: { src: '/brand/tcsexam-wordmark.svg', alt: 'TCSExam' },
    projectHome: settings.projectBase,
    search: { provider: 'local', options: searchOptions },
    socialLinks: [{ icon: 'github', link: settings.repositoryUrl }],
    footer: { message: 'Original documentation: CC BY 4.0 · Third-party materials retain their terms.' },
  },
});
