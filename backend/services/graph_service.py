import networkx as nx
import re

# In-memory graph cache for impact reuse
_graph_cache = {}

SKIP_FOLDERS = {
    "test", "tests", "docs", "doc",
    "examples", "example", "__pycache__",
    ".github", "benchmark", "benchmarks",
    "build", "dist", "vendor", "migrations",
    "node_modules", "static", "assets", "scripts",
    "fixtures", "mocks", "stubs", "typings"
}

SKIP_FILENAMES = {
    "setup.py", "setup.cfg", "conftest.py", "manage.py",
    "wsgi.py", "asgi.py", "celery.py", "gunicorn.py"
}

CORE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rb"}

def is_core_file(path):
    ext = "." + path.split(".")[-1] if "." in path else ""
    if ext not in CORE_EXTENSIONS:
        return False
    parts = path.lower().replace("\\", "/").split("/")
    for part in parts[:-1]:
        for skip in SKIP_FOLDERS:
            if part == skip or part.startswith(skip + "_") or part.endswith("_" + skip):
                return False
    filename = parts[-1]
    if filename.startswith("test_") or filename.endswith("_test.py"):
        return False
    if filename in SKIP_FILENAMES:
        return False
    return True

def parse_imports(filepath, content):
    imports = []
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('#') or line.startswith('//'):
            continue
        if filepath.endswith(".py"):
            if line.startswith('import '):
                parts = line.replace('import ', '').split(' as ')[0]
                for part in parts.split(','):
                    imports.append(part.strip().replace(".", "/"))
            elif line.startswith('from '):
                module_part = line.split(' import ')[0].replace('from ', '').strip()
                if module_part and not module_part.startswith('.'):
                    imports.append(module_part.replace(".", "/"))
                elif module_part.startswith('.'):
                    base = '/'.join(filepath.replace('\\', '/').split('/')[:-1])
                    clean = module_part.lstrip('.')
                    if clean:
                        imports.append(base + '/' + clean.replace(".", "/"))
        elif filepath.endswith(('.js', '.ts', '.jsx', '.tsx')):
            found = re.findall(r'(?:from|require)\s*[\'"]([^\'\"]+)[\'"]', line)
            imports.extend(found)
        elif filepath.endswith('.java'):
            # Java: import com.google.common.base.Preconditions;
            m = re.match(r'^import\s+(?:static\s+)?([\w.]+)\s*;', line)
            if m:
                full_import = m.group(1)
                # Convert com.foo.bar.ClassName -> ClassName
                parts = full_import.split('.')
                # Try the last part as a class name and second to last as package
                if parts:
                    imports.append(parts[-1])
                    if len(parts) >= 2:
                        imports.append('/'.join(parts[-2:]))
        elif filepath.endswith('.go'):
            # Go: "github.com/foo/bar"
            found = re.findall(r'"([^"]+)"', line)
            for f in found:
                # Use last segment of the import path
                parts = f.split('/')
                if parts:
                    imports.append(parts[-1])
        elif filepath.endswith('.rb'):
            # Ruby: require 'foo' or require_relative 'bar'
            m = re.match(r"require(?:_relative)?\s+['\"]([^'\"]+)['\"]", line)
            if m:
                imports.append(m.group(1).replace('/', '/'))
    return imports

def match_import_to_file(import_str, all_nodes):
    import_str = import_str.strip()
    import_last = import_str.split('/')[-1].lower()
    for node in all_nodes:
        node_clean = node.replace('\\', '/').lower()
        node_filename = node_clean.split('/')[-1]
        node_name = node_filename.rsplit('.', 1)[0]
        if import_last == node_name:
            return node
        if import_str.lower() in node_clean:
            return node
    return None

def build_graph(file_tree, file_contents, repo_key=None):
    G = nx.DiGraph()
    core_files = [f for f in file_tree if is_core_file(f["path"])]
    core_files.sort(key=lambda x: x.get("size", 0), reverse=True)
    core_files = core_files[:60]
    for file in core_files:
        ext = "." + file["path"].split(".")[-1] if "." in file["path"] else "unknown"
        G.add_node(file["path"], extension=ext, size=file.get("size", 0))
    edge_count = 0
    for file in core_files:
        path = file["path"]
        content = file_contents.get(path, "")
        if not content:
            continue
        imports = parse_imports(path, content)
        for imp in imports:
            matched = match_import_to_file(imp, list(G.nodes))
            if matched and matched != path:
                G.add_edge(path, matched)
                edge_count += 1
    print(f"[Graph] Total edges found: {edge_count}")
    isolated = [n for n in G.nodes if G.degree(n) == 0]
    G.remove_nodes_from(isolated)
    print(f"[Graph] Nodes after filtering isolated: {len(G.nodes)}")
    print(f"[Graph] Edges remaining: {len(G.edges)}")
    if len(G.nodes) > 50:
        sorted_nodes = sorted(G.nodes, key=lambda n: G.degree(n), reverse=True)
        G = G.subgraph(sorted_nodes[:50]).copy()
    # Cache graph in memory for impact simulator
    if repo_key:
        _graph_cache[repo_key] = G
        print(f"[Graph] Stored graph for key: {repo_key}")
    return G

def get_graph_for_repo(repo_key: str):
    """
    Retrieve a previously built graph from memory cache.
    Returns None if not found.
    """
    return _graph_cache.get(repo_key, None)

def get_impact(G, file_path):
    if file_path not in G.nodes:
        matches = [n for n in G.nodes if n.endswith(file_path) or file_path.endswith(n.split('/')[-1])]
        if matches:
            file_path = matches[0]
        else:
            print(f"[Impact] File not found in graph: {file_path}")
            return {"affected_files": [], "risk_level": "low", "affected_count": 0, "centrality_score": 0}

    # Bidirectional impact:
    # ancestors = files that IMPORT this file (would break if this file changes)
    # descendants = files this file IMPORTS (scope of what this file touches)
    try:
        ancestors = list(nx.ancestors(G, file_path))
    except Exception as e:
        print(f"[Impact] Error getting ancestors: {e}")
        ancestors = []

    try:
        descendants = list(nx.descendants(G, file_path))
    except Exception as e:
        print(f"[Impact] Error getting descendants: {e}")
        descendants = []

    # Combine both for full impact picture
    affected = list(set(ancestors + descendants))

    try:
        centrality = nx.betweenness_centrality(G)
        central_score = centrality.get(file_path, 0)
    except Exception:
        central_score = 0

    total_nodes = max(len(G.nodes), 1)
    risk_score = len(affected) / total_nodes
    degree = G.degree(file_path)
    degree_ratio = degree / total_nodes

    risk_level = (
        "high" if risk_score > 0.3 or central_score > 0.4 or degree_ratio > 0.3
        else "medium" if risk_score > 0.1 or central_score > 0.15 or degree_ratio > 0.15
        else "low"
    )
    print(f"[Impact] File: {file_path}, Ancestors: {len(ancestors)}, Descendants: {len(descendants)}, Total affected: {len(affected)}, Risk: {risk_level}, Score: {risk_score:.2f}, Centrality: {central_score:.3f}, Degree: {degree}")
    return {"affected_files": affected, "risk_level": risk_level, "affected_count": len(affected), "centrality_score": round(central_score, 3)}

def export_graph(G):
    return {
        "nodes": [{"id": node, "extension": G.nodes[node].get("extension", ""), "size": G.nodes[node].get("size", 0), "connections": G.degree(node)} for node in G.nodes],
        "edges": [{"source": u, "target": v} for u, v in G.edges],
        "summary": {"total_nodes": G.number_of_nodes(), "total_edges": G.number_of_edges()}
    }
