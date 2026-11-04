// The build records the content hash so a new release cannot reuse an older
// response cached under the unversioned public download URL.
export function dataUrl(name) {
  return `${import.meta.env.BASE_URL}data/${name}?v=${__SITE_DATA_VERSIONS__[name]}`;
}
