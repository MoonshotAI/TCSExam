"""Shared source and axiom checks for standalone Lean task verifiers.

Copies in task tests directories are maintained by tcsexam.lean_recipes.
"""
import json
from pathlib import Path
import re
import subprocess
import threading


FORBIDDEN = re.compile(
    r"\b(?:axiom|sorryAx|run_cmd|run_tac|run_elab|by_elab|elab|elab_rules|"
    r"macro|macro_rules|syntax|notation|initialize|builtin_initialize|"
    r"unsafe|extern|implemented_by|skipKernelTC|admitGoal|byAsSorry|"
    r"command_elab|term_elab|tactic_elab|builtin_command_elab|"
    r"builtin_term_elab|builtin_tactic|builtin_macro)\b|#\s*(?:eval|exec|exit|compile)\b"
)
CHAR = re.compile(r"'(?:\\(?:x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|.)|[^\\'\n])'")
# These fixed Lean commands take an interpolated string without an s!/m! prefix.
INTERPOLATED = re.compile(r'\b(?:dbg_trace|trace|throwError|throwErrorAt|logInfo|logWarning|logError)\s*$')


def source_views(text):
    """Return comment-free and code-only views, preserving character offsets.

    Strings, raw strings, characters and quoted identifiers are consumed before
    comment delimiters. Interpolated string expressions are scanned as code.
    Literal values remain intact in the comment-free view used for fixed-part
    comparisons. Malformed lexical input is rejected before compilation.
    """
    comments, code = list(text), list(text)
    n = len(text)

    def blank(target, start, end):
        for pos in range(start, end):
            if text[pos] != '\n':
                target[pos] = ' '

    def literal(start, end):
        blank(code, start, end)
        return end

    def string(i, interpolated):
        start = i
        i += 1
        while i < n:
            if text[i] == '\\':
                i += 2
            elif text[i] == '"':
                return literal(start, i + 1)
            elif interpolated and text[i] == '{':
                literal(start, i + 1)
                i = scan(i + 1, closing=True)
                start = i - 1
            else:
                i += 1
        raise ValueError('unterminated string literal')

    def scan(i, closing=False):
        depth = 0
        while i < n:
            if text.startswith('--', i):
                end = text.find('\n', i)
                end = n if end < 0 else end
                blank(comments, i, end); blank(code, i, end)
                i = end
            elif text.startswith('/-', i):
                start, nesting = i, 1
                i += 2
                while i < n and nesting:
                    if text.startswith('/-', i):
                        nesting += 1; i += 2
                    elif text.startswith('-/', i):
                        nesting -= 1; i += 2
                    else:
                        i += 1
                if nesting:
                    raise ValueError('unterminated block comment')
                blank(comments, start, i); blank(code, start, i)
            elif text[i] == '«':
                end = text.find('»', i + 1)
                if end < 0:
                    raise ValueError('unterminated quoted identifier')
                # Contents are identifiers, not literal data: keep them visible.
                i = end + 1
            elif (text[i] == 'r' and (i == 0 or not (text[i-1].isalnum() or text[i-1] in "_'"))
                  and (raw := re.match(r'r(#+)?"', text[i:]))):
                delimiter = '"' + (raw.group(1) or '')
                end = text.find(delimiter, i + len(raw.group()), n)
                if end < 0:
                    raise ValueError('unterminated raw string literal')
                i = literal(i, end + len(delimiter))
            elif text[i] == '"':
                i = string(i, (i > 0 and text[i-1] == '!') or
                           INTERPOLATED.search(''.join(comments[:i])) is not None)
            elif (text[i] == "'" and (i == 0 or not (text[i-1].isalnum() or text[i-1] in "_'"))
                  and (char := CHAR.match(text, i))):
                i = literal(i, char.end())
            elif closing and text[i] == '{':
                depth += 1; i += 1
            elif closing and text[i] == '}':
                if depth == 0:
                    return i + 1
                depth -= 1; i += 1
            else:
                i += 1
        if closing:
            raise ValueError('unterminated string interpolation')
        return i

    scan(0)
    return ''.join(comments), ''.join(code)


def strip_comments(text):
    return source_views(text)[0]


def certificate_source(text):
    """Replace an exact legacy certificate generator with its trusted module.

    Only tasks shipping the reviewed generator and compiled implementation opt
    into this compatibility path. Literal data and comments are never replaced.
    The submitted certificate data and mathematical declarations stay intact.
    """
    directory = Path(__file__).parent
    legacy = directory / 'r55-legacy-generator.txt'
    module = directory / 'TCSExamR55Certificate.lean'
    if not legacy.is_file() or not module.is_file():
        return text
    template = legacy.read_text()
    if not template or template not in text:
        return text
    _, code = source_views(text)
    _, expected_code = source_views(template)
    pieces, previous = [], 0
    for match in re.finditer(re.escape(template), text):
        start, end = match.span()
        if code[start:end] != expected_code:
            continue
        pieces.extend((text[previous:start], ''.join('\n' if c == '\n' else ' ' for c in template)))
        previous = end
    pieces.append(text[previous:])
    return ''.join(pieces)


def source_error(text, *, allow_native=True):
    try:
        text = certificate_source(text)
        _, code = source_views(text)
    except (ValueError, RecursionError) as error:
        return 'invalid Lean source: ' + str(error)
    match = FORBIDDEN.search(code)
    if match:
        return 'unsupported metaprogramming or axiom declaration: ' + match.group()
    if not allow_native and re.search(r'\bnative_decide\b', code):
        return 'native_decide is not allowed for this proof task'
    return None


def axioms_ok(output, full_name, allowed):
    """Read the final report for the exact declaration and compare full names.

    The grader emits this report from raw Lean names, without pretty-printing
    namespace shortening. No name suffix grants permission to an axiom.
    """
    structured = re.findall(r'(?m)^TCSEXAM_AXIOM_REPORT (.*)$', output)
    if structured:
        reports = []
        for line in structured:
            try:
                item = json.loads(line)
            except ValueError:
                return False
            if isinstance(item, dict) and item.get('declaration') == full_name:
                reports.append(item)
        if len(reports) != 1:
            return False
        report = reports[0]
        names, native = report.get('axioms'), report.get('native_verified')
        if not isinstance(names, list) or not isinstance(native, list):
            return False
        if not all(isinstance(name, str) and name for name in names + native):
            return False
        if not set(native) <= set(names):
            return False
        if any('._native.native_decide.ax_' not in name for name in native):
            return False
        if native and not ({'Lean.ofReduceBool', 'Lean.trustCompiler'} & set(allowed)):
            return False
        return all(name in allowed or name in native for name in names)
    pattern = (r"(?m)^'" + re.escape(full_name) +
               r"' (depends on axioms:|does not depend on any axioms)")
    reports = list(re.finditer(pattern, output))
    if not reports:
        return False
    last = reports[-1]
    if last.group(1) == 'does not depend on any axioms':
        return re.match(r'[^\S\n]*(?:\n|$)', output[last.end():]) is not None
    listing = re.match(r'\s*\[([^\[\]]*)\]', output[last.end():])
    if listing is None:
        return False
    names = [part.strip() for part in listing.group(1).split(',')]
    if names == ['']:
        return False
    return all(name in allowed for name in names)


def axiom_audit(full_name, *, allow_native=False):
    """Invoke the audit command from the separately compiled trusted module."""
    if not all(re.fullmatch(r"[\w']+", part) for part in full_name.split('.')):
        raise ValueError('Invalid configured theorem name')
    command = '#tcsexam_audit_native' if allow_native else '#tcsexam_audit'
    return f'\n{command} {json.dumps(full_name)}\n'


_AUDIT_LOCK = threading.Lock()
_AUDIT_PROJECTS = set()


def run_lean(cwd, path, timeout):
    """Compile trusted auditing code before any submitted Lean declarations.

    Its elaborators and typeclass instances are resolved in a separate module,
    so submission namespaces and instances cannot change the report generator.
    Only an image-owned project should be supplied as cwd.
    """
    cwd = Path(cwd).resolve()
    try:
        with _AUDIT_LOCK:
            if cwd not in _AUDIT_PROJECTS:
                modules = [Path(__file__).with_name('TCSExamVerifierAudit.lean')]
                certificate = Path(__file__).with_name('TCSExamR55Certificate.lean')
                if certificate.is_file():
                    modules.append(certificate)
                for module in modules:
                    target = cwd / '.lake/build/lib/lean' / (module.stem + '.olean')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    built = subprocess.run(['lake', 'env', 'lean', '-R', str(module.parent), '-o', str(target), str(module)],
                                           cwd=cwd, capture_output=True, text=True, timeout=timeout)
                    if built.returncode:
                        return False, 'Trusted module failed: ' + built.stdout + built.stderr
                _AUDIT_PROJECTS.add(cwd)
        # The generated grading file is outside the submitted tree. Keep the
        # caller's name for diagnostics, adding only the trusted import.
        path = Path(path)
        source = certificate_source(path.read_text())
        prefix = 'import TCSExamVerifierAudit\n'
        if Path(__file__).with_name('TCSExamR55Certificate.lean').is_file():
            prefix += 'import TCSExamR55Certificate\n'
        if not source.startswith(prefix):
            source = prefix + source
        path.write_text(source)
        proc = subprocess.run(['lake', 'env', 'lean', str(path)], cwd=cwd,
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, 'TIMEOUT'
    return proc.returncode == 0, proc.stdout + proc.stderr
