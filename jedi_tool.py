#!/usr/bin/env python3
"""
jedi_tool.py — CLI for Python code analysis.

Structure via ast (fast, reliable). References/search via jedi.

Usage:
    python jedi_tool.py overview <file> [--json]
    python jedi_tool.py members <file> <name|line> [--json]
    python jedi_tool.py refs <file> <line> <col> [--scope file|project] [--json]
    python jedi_tool.py search <dir> <name> [--json]
    python jedi_tool.py body <file> <line> [--json]
"""

import sys
import json
import re
import ast
from pathlib import Path


def _imports(code):
    return [l.strip() for l in code.splitlines()
            if l.strip().startswith(('import ', 'from '))]


def _sig(lines, line):
    if line < 1 or line > len(lines):
        return ''
    text = lines[line - 1].rstrip()
    stripped = text.lstrip()
    if not stripped.startswith(('def ', 'class ', 'async ')):
        return stripped
    sig = text
    depth = sig.count('(') - sig.count(')')
    i = line
    while depth > 0 and i < len(lines):
        i += 1
        sig += ' ' + lines[i - 1].strip()
        depth += lines[i - 1].count('(') - lines[i - 1].count(')')
    if sig.rstrip().endswith(':'):
        sig = sig.rstrip()[:-1]
    return re.sub(r'\s+', ' ', sig).strip()


def _clean(sig, selfless=True):
    s = sig
    for p in ('async def ', 'def ', 'class '):
        if s.startswith(p):
            s = s[len(p):]
            break
    if selfless:
        s = s.replace('(self, ', '(').replace('(self)', '()')
    return s


def _docstring(node):
    if (node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)):
        return node.body[0].value.value.split('\n')[0][:150]
    return None


def _parse(fp):
    code = Path(fp).read_text(encoding='utf-8', errors='replace')
    lines = code.splitlines()
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return None, code, lines, str(e)

    classes, funcs, vars_ = [], [], []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            members = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    doc = _docstring(item)
                    members.append({
                        'name': item.name, 'line': item.lineno,
                        'sig': _sig(lines, item.lineno), 'doc': doc,
                    })
            bases = []
            for b in node.bases:
                try:
                    bases.append(ast.unparse(b))
                except Exception:
                    bases.append('?')
            classes.append({
                'name': node.name, 'line': node.lineno,
                'bases': bases, 'members': members,
            })
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append({
                'name': node.name, 'line': node.lineno,
                'sig': _sig(lines, node.lineno),
            })
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    vars_.append({'name': t.id, 'line': node.lineno})

    return {
        'classes': classes, 'functions': funcs, 'variables': vars_,
    }, code, lines, None


def cmd_overview(fp):
    result, code, lines, err = _parse(fp)
    if err:
        return {'error': f'Parse error: {err}'}
    return {
        'file': Path(fp).name, 'path': str(fp),
        'lines': len(lines), 'imports': _imports(code),
        'classes': result['classes'],
        'functions': result['functions'],
        'variables': result['variables'],
    }


def _method_end_line(fp, lineno):
    try:
        code = Path(fp).read_text(encoding='utf-8', errors='replace')
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.lineno == lineno:
                    return getattr(node, 'end_lineno', None) or lineno
    except Exception:
        pass
    return lineno


def _find_node_by_line(tree, target_line):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.lineno == target_line:
                return node
            if hasattr(node, 'end_lineno') and node.end_lineno:
                if node.lineno <= target_line <= node.end_lineno:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        return node
    return None


def cmd_members(fp, target):
    result, code, lines, err = _parse(fp)
    if err:
        return {'error': f'Parse error: {err}'}

    for cls in result['classes']:
        if cls['name'] == target or str(cls['line']) == str(target):
            return {
                'name': cls['name'], 'type': 'class', 'line': cls['line'],
                'bases': cls.get('bases', []),
                'members': cls['members'],
            }

    for f in result['functions']:
        if f['name'] == target or str(f['line']) == str(target):
            return {'name': f['name'], 'type': 'function', 'line': f['line'],
                    'members': []}

    for cls in result['classes']:
        for m in cls['members']:
            if m['name'] == target:
                end = m.get('end_line') or _method_end_line(fp, m['line'])
                source_lines = lines[m['line'] - 1:end]
                return {
                    'name': m['name'], 'type': 'method', 'line': m['line'],
                    'end_line': end, 'total_lines': end - m['line'] + 1,
                    'class': cls['name'], 'class_line': cls['line'],
                    'sig': m['sig'], 'doc': m.get('doc'),
                    'source': '\n'.join(source_lines),
                }

    return {'error': f"'{target}' not found in {Path(fp).name}"}


def cmd_refs(fp, line, col, scope='project'):
    from jedi import Script
    code = Path(fp).read_text(encoding='utf-8', errors='replace')
    script = Script(code, path=str(fp))
    refs = script.get_references(int(line), int(col),
                                 include_builtins=False, scope=scope)
    return [{'name': r.name,
             'path': str(r.module_path) if r.module_path else str(fp),
             'line': r.line, 'col': r.column,
             'def': r.is_definition(), 'desc': r.description}
            for r in refs]


def cmd_search(dp, name):
    from jedi import Project
    proj = Project(str(dp))
    return [{'name': r.name, 'type': r.type,
             'path': str(r.module_path) if r.module_path else '?',
             'line': r.line, 'desc': r.description}
            for r in proj.search(name)]


# ---- Formatters ----

def cmd_body(fp, line):
    code = Path(fp).read_text(encoding='utf-8', errors='replace')
    lines = code.splitlines()
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {'error': f'Parse error: {e}'}

    target = int(line)
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.lineno == target:
                best = node
                break
            if hasattr(node, 'end_lineno') and node.end_lineno:
                if node.lineno < target <= node.end_lineno:
                    if best is None or (hasattr(best, 'end_lineno') and best.end_lineno and node.end_lineno < best.end_lineno):
                        best = node

    if best is None:
        return {'error': f'No function/class at line {target}'}

    end = getattr(best, 'end_lineno', None) or best.lineno
    source = '\n'.join(lines[best.lineno - 1:end])
    kind = 'class' if isinstance(best, ast.ClassDef) else 'function'
    return {
        'name': best.name, 'type': kind,
        'line': best.lineno, 'end_line': end,
        'total_lines': end - best.lineno + 1,
        'source': source,
    }


def _f_overview(d):
    if 'error' in d:
        return f"ERROR: {d['error']}"
    o = [f"=== {d['file']} ({d['lines']} lines) ===", '']
    if d['imports']:
        o.append('IMPORTS:')
        for i in d['imports']:
            o.append(f'  {i}')
        o.append('')
    for c in d['classes']:
        bases = f"({', '.join(c['bases'])})" if c.get('bases') else ''
        o.append(f"class {c['name']}{bases} (L{c['line']}, {len(c['members'])} methods):")
        for m in c['members']:
            o.append(f"  {_clean(m['sig']):<58s} L{m['line']}")
        o.append('')
    if d['functions']:
        o.append('FUNCTIONS:')
        for f in d['functions']:
            o.append(f"  {_clean(f['sig'], False):<58s} L{f['line']}")
        o.append('')
    if d['variables']:
        o.append('VARIABLES:')
        for v in d['variables']:
            o.append(f"  {v['name']:<48s} L{v['line']}")
    return '\n'.join(o)


def _f_members(d):
    if 'error' in d:
        return f"ERROR: {d['error']}"
    if d.get('type') == 'method':
        o = [f"=== {d['name']} (method of {d['class']}, L{d['line']}, {d['total_lines']} lines) ===",
             f"  {_clean(d['sig'])}"]
        if d.get('doc'):
            o.append(f"  doc: {d['doc']}")
        o.append('')
        o.append(d['source'])
        return '\n'.join(o)
    bases = f" inherits {', '.join(d['bases'])}" if d.get('bases') else ''
    o = [f"=== {d['name']} ({d['type']}, L{d['line']}){bases} ===", '']
    for m in d['members']:
        s = _clean(m.get('sig', m['name']))
        parts = [f"  L{m['line']:>4d}  {s}"]
        if m.get('doc'):
            parts.append(f"         doc: {m['doc']}")
        o.append('\n'.join(parts))
    if not d['members']:
        o.append('  (no members)')
    return '\n'.join(o)


def _f_body(d):
    if 'error' in d:
        return f"ERROR: {d['error']}"
    o = [f"=== {d['name']} ({d['type']}, L{d['line']}-L{d['end_line']}, {d['total_lines']} lines) ===",
         '']
    o.append(d['source'])
    return '\n'.join(o)


def _f_refs(data):
    if not data:
        return 'No references found.'
    o = []
    defs = [r for r in data if r['def']]
    refs = [r for r in data if not r['def']]
    if defs:
        o.append('DEFINITIONS:')
        for r in defs:
            o.append(f"  {r['path']}:{r['line']}  {r['name']}")
    if refs:
        o.append(f'REFERENCES ({len(refs)}):')
        for r in refs:
            o.append(f"  {r['path']}:{r['line']}:{r['col']}  {r['name']}")
    return '\n'.join(o)


def _f_search(data):
    if not data:
        return 'No results found.'
    return '\n'.join(
        f"  {r['type']:<10s} {r['path']}:L{r['line']}  {r['name']}"
        for r in data
    )


FMT = {'overview': _f_overview, 'members': _f_members,
        'refs': _f_refs, 'search': _f_search, 'body': _f_body}


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    raw = sys.argv[1:]
    if not raw:
        print(__doc__); sys.exit(0)

    as_json = '--json' in raw
    scope = 'project'
    if '--scope' in raw:
        i = raw.index('--scope')
        if i + 1 < len(raw):
            scope = raw[i + 1]
    args = [a for a in raw if not a.startswith('-')]
    if not args:
        print(__doc__); sys.exit(0)

    cmd = args[0]
    try:
        if cmd == 'overview':
            data = cmd_overview(args[1])
        elif cmd == 'members':
            data = cmd_members(args[1], args[2])
        elif cmd == 'refs':
            data = cmd_refs(args[1], args[2], args[3], scope)
        elif cmd == 'search':
            data = cmd_search(args[1], args[2])
        elif cmd == 'body':
            data = cmd_body(args[1], args[2])
        else:
            print(f"Unknown: {cmd}\n{__doc__}"); sys.exit(1)

        if as_json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(FMT[cmd](data))
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr); sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr); sys.exit(1)


if __name__ == '__main__':
    main()
