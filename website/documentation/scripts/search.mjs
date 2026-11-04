// This function must be self-contained: VitePress serializes it for the browser.
export function tokenizeSearch(text) {
  const normalized = text.normalize('NFKC').toLowerCase();
  const words = normalized.match(/[\p{L}\p{N}_]+/gu) || [];
  const tokens = [];
  for (const word of words) {
    // CJK bigrams match a phrase inside a longer unspaced sentence. Single
    // characters also allow one-character queries; Latin identifiers stay whole.
    if (/\p{Script=Han}/u.test(word)) {
      const parts = word.match(/\p{Script=Han}+|[^\p{Script=Han}]+/gu) || [];
      for (const part of parts) {
        if (!/\p{Script=Han}/u.test(part)) { tokens.push(part); continue; }
        const chars = [...part];
        tokens.push(...chars);
        for (let i = 0; i < chars.length - 1; i++) tokens.push(chars[i] + chars[i + 1]);
      }
    } else tokens.push(word);
  }
  return [...new Set(tokens)];
}

export const searchOptions = {
  miniSearch: {
    options: { tokenize: tokenizeSearch },
    searchOptions: { combineWith: 'AND', prefix: true, fuzzy: false, boost: { title: 4, titles: 2 } },
  },
  locales: {
    zh: {
      translations: {
        button: { buttonText: '搜索文档', buttonAriaLabel: '搜索文档' },
        modal: {
          displayDetails: '显示详细结果', resetButtonTitle: '清空搜索', backButtonTitle: '返回',
          noResultsText: '没有找到相关内容',
          footer: { selectText: '选择', selectKeyAriaLabel: '回车', navigateText: '切换', navigateUpKeyAriaLabel: '向上', navigateDownKeyAriaLabel: '向下', closeText: '关闭', closeKeyAriaLabel: 'Esc' },
        },
      },
    },
  },
};
