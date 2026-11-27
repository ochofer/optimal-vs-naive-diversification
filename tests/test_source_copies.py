"""The code and the tables copied from the repository risk-models-for-index-tracking at constants.SOURCE_COMMIT.

Each copied module is the source file unchanged below its first line, which names the source file and the commit, and
its SHA-256 below that line is in constants.SOURCE_MODULES. src/bp/source/constants.py holds exactly the names the
copies read, and no module outside src/bp/source/ reads it. Each copied table's SHA-256 is in constants.SOURCE_TABLES.
In a checkout that holds the commit, every copy, every value of the source constants and its line number are also
compared with the file at the commit, read with git; those comparisons are skipped elsewhere.
"""
import ast
import hashlib
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp import constants as C  # noqa: E402
from bp.source import constants as SC  # noqa: E402

MODULES = ROOT / C.SOURCE_MODULES_DIR
TABLES = ROOT / C.SOURCE_TABLES_DIR
COPIES = sorted(p for p in MODULES.glob("*.py") if p.name not in ("__init__.py", "constants.py"))
FIRST_LINE = re.compile(r"^# Copied verbatim from (src/bp/\w+\.py) at commit (\w+) of github\.com/ochofer/risk-models-for-index-tracking; "
                        r"every line below this one is the source file unchanged\.$")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def at_commit(path):
    """The file at the source commit, read with git from this checkout, or None where the checkout does not hold it."""
    if not (ROOT / ".git").exists():
        return None
    r = subprocess.run(["git", "cat-file", "-p", f"{C.SOURCE_COMMIT}:{path}"], cwd=ROOT, capture_output=True)
    return r.stdout if r.returncode == 0 else None


def test_the_copied_modules_and_tables_are_the_listed_ones():
    assert {p.name for p in COPIES} == set(C.SOURCE_MODULES)
    assert {p.name for p in TABLES.glob("*.csv")} == set(C.SOURCE_TABLES)


@pytest.mark.parametrize("path", COPIES, ids=lambda p: p.name)
def test_each_copy_is_the_source_file_below_its_first_line(path):
    first, rest = path.read_bytes().split(b"\n", 1)
    m = FIRST_LINE.match(first.decode())
    assert m, f"{path.name}: the first line does not name the source file and the commit"
    source_path, digest = C.SOURCE_MODULES[path.name]
    assert m.group(1) == source_path and m.group(2) == C.SOURCE_COMMIT
    assert sha256(rest) == digest, f"{path.name} differs from the source file"


@pytest.mark.parametrize("name", sorted(C.SOURCE_TABLES))
def test_each_copied_table_matches_its_hash(name):
    assert sha256((TABLES / name).read_bytes()) == C.SOURCE_TABLES[name][1]


def test_the_source_constants_hold_exactly_the_names_the_copies_read():
    referenced = set()
    for path in COPIES:
        referenced |= set(re.findall(r"\bC\.([A-Z_][A-Z0-9_]*)", path.read_text()))
    held = {n for n in dir(SC) if n.isupper()}
    assert held == referenced, f"held and not read: {sorted(held - referenced)}; read and not held: {sorted(referenced - held)}"


def test_no_module_outside_the_copies_reads_the_source_constants():
    pattern = re.compile(r"source\s+import\s+[^\n]*\bconstants\b|source\.constants|from\s+\.source\s+import\s+constants")
    readers = []
    paths = list((ROOT / "src").rglob("*.py")) + list((ROOT / "notebooks").glob("*.ipynb")) + [ROOT / "build_notebooks.py"]
    for path in paths:
        if path.is_file() and MODULES not in path.parents and pattern.search(path.read_text()):
            readers.append(str(path.relative_to(ROOT)))
    assert not readers, f"files outside {C.SOURCE_MODULES_DIR} that read its constants: {readers}"


def test_the_copies_import():
    from bp.source import attribution, benchmark, covariance, evaluation, optimiser, paired  # noqa: F401
    assert covariance.S.__name__ == "bp.source.rules" and evaluation.O.__name__ == "bp.source.optimiser"


@pytest.fixture(scope="module")
def source_constants():
    data = at_commit("src/bp/constants.py")
    if data is None:
        pytest.skip("this checkout does not hold the source commit")
    assert sha256(data) == C.SOURCE_CONSTANTS_SHA256
    values = {}
    exec(compile(data.decode(), "constants.py", "exec"), values)
    return data.decode(), values


def test_the_copies_and_tables_equal_the_files_at_the_commit():
    for path in COPIES:
        source = at_commit(C.SOURCE_MODULES[path.name][0])
        if source is None:
            pytest.skip("this checkout does not hold the source commit")
        assert path.read_bytes().split(b"\n", 1)[1] == source, path.name
    for name, (source_path, _) in C.SOURCE_TABLES.items():
        assert (TABLES / name).read_bytes() == at_commit(source_path), name


def test_the_source_constants_equal_the_file_at_the_commit(source_constants):
    text, source = source_constants
    ours = {n: getattr(SC, n) for n in dir(SC) if n.isupper()}
    differ = {n: (v, source.get(n)) for n, v in ours.items() if source.get(n) != v}
    assert not differ, f"values that differ from the source: {differ}"
    lines = {}
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    lines.setdefault(t.id, node.lineno)
    held = (MODULES / "constants.py").read_text()
    for n in ours:
        m = re.search(rf"^{n} = .*# line (\d+)$", held, flags=re.M)
        assert m and int(m.group(1)) == lines[n], n
