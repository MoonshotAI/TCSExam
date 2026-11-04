// Shared by standalone pages and older task-dialog links. Load the example only
// when requested, and stop its playback whenever the disclosure is closed.
export function mountOptionalExample(task) {
  const details = document.querySelector('#task-example');
  if (!details) return () => {};
  const root = document.querySelector('#task-lab-root');
  let disposed = false, generation = 0, dispose = () => {};
  const toggle = async () => {
    const current = ++generation;
    dispose();
    dispose = () => {};
    root.replaceChildren();
    if (!details.open || disposed) return;
    root.textContent = 'Loading example…';
    const stillOpen = () => !disposed && details.isConnected && details.open && current === generation;
    try {
      const {mountTaskLab} = await import('./index.js');
      if (stillOpen()) dispose = mountTaskLab(root, task);
    } catch {
      if (stillOpen()) root.textContent = 'The example could not be loaded. The task specification is available above.';
    }
  };
  details.addEventListener('toggle', toggle);
  return () => {
    disposed = true;
    generation++;
    details.removeEventListener('toggle', toggle);
    dispose();
    root.replaceChildren();
  };
}
