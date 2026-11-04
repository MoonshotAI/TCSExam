// Documentation lives on the public site; source links stay on the repository.
export function documentationLinks(env = process.env) {
  const siteUrl = env.SITE_URL ? new URL(env.SITE_URL) : null;
  if (siteUrl && (!['https:', 'http:'].includes(siteUrl.protocol) || siteUrl.username || siteUrl.password || siteUrl.search || siteUrl.hash)) {
    throw new Error('SITE_URL must be an HTTP(S) site URL without credentials, query or fragment');
  }
  const configuredBase = env.SITE_BASE_PATH || siteUrl?.pathname || '/';
  const base = configuredBase === './' ? '/' : `/${configuredBase.replace(/^\/+|\/+$/g, '')}/`.replace(/^\/\//, '/');
  if (/[?#\\]/.test(base) || base.split('/').some(part => part === '.' || part === '..')) {
    throw new Error('SITE_BASE_PATH must be a site path without query, fragment or parent segments');
  }
  // Keep navigation on the current host so the production build also works
  // unchanged on a preview host. SITE_URL still supplies the default base.
  const docsRoot = `${base}docs/`;
  return Object.fromEntries(Object.entries({
    documentation: '', guide: 'getting-started/', running: 'running/',
    requirements: 'runtime-availability/', backend: 'backend/docker/',
    scoring: 'scoring/', citation: 'citation/',
  }).map(([key, path]) => [key, `${docsRoot}${path}`]));
}

export function repositoryConfig(env = process.env) {
  const url = new URL(env.SITE_REPOSITORY_URL || 'https://github.com/MoonshotAI/TCSExam');
  if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error('SITE_REPOSITORY_URL must be an HTTP(S) repository URL without credentials, query or fragment');
  }
  const repository = url.href.replace(/\/$/, '').replace(/\.git$/, '');
  const ref = env.SITE_REPOSITORY_REF || 'HEAD';
  const encodedRef = encodeURIComponent(ref);
  const treeRoot = `${repository}/${url.hostname === 'github.com' ? 'tree' : '-/tree'}/${encodedRef}`;
  return {
    url: repository, cloneUrl: `${repository}.git`, ref,
    ...documentationLinks(env),
    tasks: `${treeRoot}/tasks`,
  };
}

export const withRepositoryLinks = (data, repository) => ({
  ...data,
  links: {...data.links, repository: repository.url, release: repository.tasks, documentation: repository.documentation},
});
