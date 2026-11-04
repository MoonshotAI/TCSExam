export function getSettings(env = process.env) {
  const raw = env.SITE_BASE_PATH || '/TCSExam/';
  if (!raw.startsWith('/') || raw.includes('..') || /[?#]/.test(raw)) {
    throw new Error('SITE_BASE_PATH must be an absolute URL path without .., ? or #');
  }
  const projectBase = `${raw.replace(/\/+$/, '')}/`;
  const repositoryUrl = (env.SITE_REPOSITORY_URL || 'https://github.com/MoonshotAI/TCSExam').replace(/\/$/, '');
  if (!/^https:\/\/github\.com\/[^/]+\/[^/]+$/.test(repositoryUrl)) {
    throw new Error('SITE_REPOSITORY_URL must identify an HTTPS GitHub repository');
  }
  const repositoryRef = env.SITE_REPOSITORY_REF || 'master';
  return { projectBase, docsBase: `${projectBase}docs/`, repositoryUrl, repositoryRef };
}

export function sourceUrl(path, settings, directory = false) {
  const encodedPath = path.split('/').map(encodeURIComponent).join('/');
  return `${settings.repositoryUrl}/${directory ? 'tree' : 'blob'}/${encodeURIComponent(settings.repositoryRef)}/${encodedPath}`;
}
