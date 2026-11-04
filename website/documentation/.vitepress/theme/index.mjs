import DefaultTheme from 'vitepress/theme';
import { h } from 'vue';
import SiteLinks from './SiteLinks.vue';
import './style.css';

export default {
  extends: DefaultTheme,
  Layout() {
    return h(DefaultTheme.Layout, null, {
      'nav-bar-content-before': () => h(SiteLinks, { type: 'home' }),
      'nav-bar-content-after': () => h(SiteLinks, { type: 'language' }),
    });
  },
};
