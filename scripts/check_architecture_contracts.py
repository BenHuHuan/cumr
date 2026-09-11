#!/usr/bin/env python3
"""Check CUMR's declared architecture boundaries without numerical dependencies.

This is an executable subset of CONTRACTS.md, not a proof of runtime semantics.
"""
from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

from sync_agent_guides import check_guides

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/architecture/contracts.json"


def python_boundary_errors(source, label, allowed_external_roots):
    try:
        tree = ast.parse(source, filename=label)
    except SyntaxError as error:
        return [f"{label}: invalid Python: {error}"]
    allowed = set(sys.stdlib_module_names) | set(allowed_external_roots)
    errors = []
    bindings = {}
    for node in ast.walk(tree):
        imports = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
                bindings[alias.asname or alias.name.split('.')[0]] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                errors.append(f"{label}:{node.lineno}: relative import escapes the declared script boundary")
            imports.append(node.module or "")
            for alias in node.names:
                bindings[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        for name in imports:
            root = name.split('.')[0]
            if root not in allowed or root in {"importlib", "runpy"}:
                errors.append(f"{label}:{node.lineno}: forbidden dependency {name!r}")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = ast.unparse(node.func)
        first, _, rest = name.partition('.')
        qualified = bindings.get(first, first) + ('.' + rest if rest else '')
        if qualified.rsplit('.', 1)[-1] in {"__import__", "eval", "exec"}:
            errors.append(f"{label}:{node.lineno}: dynamic code/import bypass is forbidden")
    return errors


def shared_contact_errors(source, label):
    tree = ast.parse(source, filename=label)
    main = next((node for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main"), None)
    calls = [] if main is None else [node for node in ast.walk(main) if isinstance(node, ast.Call)]
    if not any(ast.unparse(call.func).rsplit('.', 1)[-1] == "finalize_contact_motion" for call in calls):
        return [f"{label}: main must call the shared finalize_contact_motion"]
    return []


def documentation_errors(root, paths):
    errors = []
    for relative in paths:
        path = root / relative
        if not path.is_file():
            errors.append(f"Missing required document: {relative}")
            continue
        if path.suffix != ".md":
            continue
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" in target or target.startswith(("#", "mailto:")):
                continue
            local = target.split('#', 1)[0]
            if local and not (path.parent / local).exists():
                errors.append(f"{relative}: broken local link {target}")
    return errors


def protected_path_errors(paths, patterns):
    return [f"Forbidden tracked/unignored artifact: {path}"
            for path in paths if any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)]


def evidence_errors(root, policy):
    manifest_path = root / policy["frozen_evidence_manifest"]
    manifest = json.loads(manifest_path.read_text())
    errors = []
    for name, expected in manifest["files"].items():
        path = manifest_path.parent / name
        if not path.is_file():
            errors.append(f"Missing published evidence: {name}")
            continue
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            errors.append(f"Evidence checksum mismatch: {name}; fetch LFS or investigate the changed evidence")
            continue
        if name in {"baseline.npz", "stabilized.npz"}:
            with zipfile.ZipFile(path) as archive:
                fields = {Path(item).stem for item in archive.namelist()}
            missing = set(policy["robot_output_required_fields"]) - fields
            if missing:
                errors.append(f"{name}: missing public result metadata {sorted(missing)}")
    return errors


def main():
    policy = json.loads(POLICY.read_text())
    if policy.get("schema_version") != 1:
        raise SystemExit("Unsupported architecture policy schema")
    errors = check_guides(ROOT)
    for path, rule in policy["python_boundaries"].items():
        errors.extend(python_boundary_errors((ROOT / path).read_text(), path, rule["allowed_external_roots"]))
    for path in policy["shared_contact_callers"]:
        errors.extend(shared_contact_errors((ROOT / path).read_text(), path))
    errors.extend(documentation_errors(ROOT, policy["required_documents"]))
    paths = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT,
    ).decode().split('\0')
    errors.extend(protected_path_errors((p for p in paths if p), policy["protected_git_patterns"]))
    errors.extend(evidence_errors(ROOT, policy))
    if errors:
        raise SystemExit("Architecture contract violations:\n- " + "\n- ".join(errors))
    print("CUMR contracts passed: owner imports, shared contact calls, agent guides, docs, artifacts and evidence")


if __name__ == "__main__":
    main()
