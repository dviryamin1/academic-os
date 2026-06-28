import ast
from pathlib import Path


def test_domain_has_no_persistence_dependencies() -> None:
    domain_root = Path("src/academic_os/domain")
    forbidden_roots = {
        "alembic",
        "sqlite3",
        "sqlalchemy",
        "academic_os.infrastructure",
    }

    violations: list[str] = []
    for source_path in domain_root.rglob("*.py"):
        syntax_tree = ast.parse(source_path.read_text(encoding="utf-8"))

        for node in ast.walk(syntax_tree):
            imported_modules: list[str] = []
            if isinstance(node, ast.Import):
                imported_modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules = [node.module]

            for imported_module in imported_modules:
                if any(
                    imported_module == forbidden
                    or imported_module.startswith(f"{forbidden}.")
                    for forbidden in forbidden_roots
                ):
                    violations.append(f"{source_path}: {imported_module}")

    assert violations == []

