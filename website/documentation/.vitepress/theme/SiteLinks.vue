<script setup>
import { computed, onMounted, ref } from 'vue';
import { useData } from 'vitepress';
const props = defineProps({ type: String });
const { page, hash, lang, theme } = useData();
// Render the same href during SSR and hydration, then add the browser hash.
// Vue does not patch an initially different href while hydrating static HTML.
const mounted = ref(false);
onMounted(() => { mounted.value = true; });
const chinese = computed(() => lang.value === 'zh-CN');
const alternate = computed(() => {
  const frontmatter = page.value.frontmatter;
  const anchor = decodeURIComponent((mounted.value ? hash.value || '' : '').replace(/^#/, ''));
  const mapped = frontmatter.alternateAnchors?.[anchor];
  return (frontmatter.alternateUrl || '') + (mapped ? `#${encodeURIComponent(mapped)}` : '');
});
</script>

<template>
  <a v-if="props.type === 'home'" class="docs-home-link" :href="theme.projectHome"
    :aria-label="chinese ? '返回项目首页' : 'Back to project homepage'">
    <span aria-hidden="true">←</span><span class="docs-home-text">{{ chinese ? '项目首页' : 'Project home' }}</span>
  </a>
  <a v-else-if="alternate" class="docs-language-link" :href="alternate"
    :hreflang="chinese ? 'en' : 'zh-CN'" :lang="chinese ? 'en' : 'zh-CN'"
    :aria-label="chinese ? 'Read this page in English' : '阅读本页中文版'">
    {{ chinese ? 'English' : '中文' }}
  </a>
</template>
