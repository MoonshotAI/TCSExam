"""Check that public documentation describes usable, current interfaces."""
from pathlib import Path
import json
import re
import unittest
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[3]
LINK = re.compile(r'\[[^\]]+\]\(([^)\s]+)\)')
SCHEME = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*:')


def text(relative):
    return ' '.join((ROOT / relative).read_text().split())


class Documentation(unittest.TestCase):
    def test_relative_links_exist(self):
        paths = [ROOT / 'README.md', ROOT / '.github/CONTRIBUTING.md', ROOT / '.github/CONTRIBUTING.zh-CN.md', ROOT / 'assets/README.md',
                 *ROOT.glob('docs/**/*.md'), *ROOT.glob('assets/environments/**/*.md'),
                 *ROOT.glob('tasks/solver/*/maxcut-mqlib/environment/app/mqlib/**/README.md'),
                 *ROOT.glob('tasks/**/instruction.md'),
                 *ROOT.glob('tasks/**/tests/reference/*.md')]
        broken = []
        for path in paths:
            for match in LINK.finditer(path.read_text()):
                target = match.group(1).strip()
                if not target or target.startswith(('#', '/')) or SCHEME.match(target):
                    continue
                target = target.split('#', 1)[0].split('?', 1)[0]
                # Mathematical expressions such as f_[x](∅) are not links.
                if not re.fullmatch(r'[\w./%+@~-]+', target):
                    continue
                if target and not (path.parent / unquote(target)).resolve().exists():
                    broken.append(f'{path.relative_to(ROOT)} -> {target}')
        self.assertEqual(broken, [])

    def test_user_guides_cover_build_and_run_interfaces(self):
        from tcsexam.project_links import update
        update(ROOT, check=True)
        readme = text('README.md')
        running = text('docs/running.md')
        for command in ('tcsexam build', 'tcsexam doctor', 'tcsexam run'):
            self.assertIn(command, readme + ' ' + running)
        for guide in ('docs/running.md', 'docs/resources.md', 'docs/solver-protocols.md'):
            self.assertIn(guide, readme)
        self.assertIn('Harbor', running)
        self.assertIn('adapter: module:factory', text('docs/backend/docker.md'))

    def test_export_guide_documents_portable_source_and_required_inputs(self):
        resources = text('docs/resources.md')
        contributing = text('.github/CONTRIBUTING.md')
        self.assertIn('tcsexam export --normalize-modes --output', contributing)
        self.assertIn('new or empty', contributing)
        self.assertIn('MaxSAT', resources)
        manifest = json.loads((ROOT / 'assets/data/solver/solver-maxsat-mse-judging-data-files.json').read_text())
        self.assertIn(f"{len(manifest['files'])} MaxSAT", resources)
        self.assertIn('--input', resources)
        self.assertNotIn('git archive --format=tar.gz', resources)
        self.assertIn('source-inputs', text('docs/source-delivery.md'))

    def test_offline_guide_uses_the_ordinary_build_path(self):
        guide = text('docs/offline-adapters.md')
        for command in ('tcsexam build --suite lite', 'tcsexam doctor --suite lite',
                        'tcsexam run --suite lite'):
            self.assertIn(command, guide)
        self.assertNotIn('tcsexam run --suite lite --artifacts /path/to/artifacts.json', guide)

    def test_ci_and_contributor_guide_run_the_complete_test_suite(self):
        command = 'python -m pytest src/tcsexam/backend/tests src/tcsexam/tests -q'
        self.assertIn(command, text('.github/CONTRIBUTING.md'))
        configs = [ROOT / '.github/workflows/checks.yml']
        gitlab_config = ROOT / '.gitlab-ci.yml'
        if gitlab_config.exists():
            configs.append(gitlab_config)
        for config in configs:
            content = config.read_text()
            self.assertIn(command, content)
            self.assertNotIn('python -m unittest discover', content)

    def test_source_tree_has_no_private_progress_documents(self):
        self.assertFalse((ROOT / 'docs/integration-status.md').exists())
        dated_guides = [path.name for path in (ROOT / 'docs').glob('*.md')
                        if re.search(r'-\d{6,8}\.md$', path.name)]
        self.assertEqual(dated_guides, [])

    def test_distribution_guidance_keeps_licenses_and_private_answers_distinct(self):
        guide = text('docs/licenses/distribution.md')
        for target in ('third-party/qbf-data-distribution-source.json',
                       'third-party/ce-pace2021-source.json',
                       'third-party/dfvs-pace2022-source.json',
                       'third-party/vc-pace2019-source.json',
                       'third-party/claude-code-distribution.json', 'oracle-answers.md'):
            self.assertIn(target, guide)
        self.assertIn('local_prepare', guide)
        self.assertIn('private_only', guide)


if __name__ == '__main__':
    unittest.main()
