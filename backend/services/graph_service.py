import networkx as nx
import re

def build_graph(file_tree, file_contents):
    G = nx.DiGraph()

    for file in file_tree:
        path = file["path"]
        ext = path.split(".")[-1] if "." in path else "unknown"
        content = file_contents.get(path, "")

        # Extract classes and functions for richer nodes
        classes, functions = _extract_symbols(path, content)

        G.add_node(path,
            extension=ext,
            size=file.get("size", 0),
            node_type="file",
            classes=classes,
            functions=functions,
        )

        # Add class/function sub-nodes linked to their parent file
        for cls in classes:
            cls_id = f"{path}::{cls}"
            G.add_node(cls_id, node_type="class", parent_file=path)
            G.add_edge(path, cls_id)

        for fn in functions:
            fn_id = f"{path}::{fn}"
            G.add_node(fn_id, node_type="function", parent_file=path)
            G.add_edge(path, fn_id)

    for file in file_tree:
        path = file["path"]
        content = file_contents.get(path, "")
        if content:
            imports = parse_imports(path, content)
            for imp in imports:
                matched = match_import_to_file(imp, list(G.nodes))
                if matched:
                    G.add_edge(path, matched)

    return G


def _extract_symbols(filepath, content):
    """Extract class and function names from source code."""
    classes = []
    functions = []
    if not content:
        return classes, functions

    if filepath.endswith(".py"):
        classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
        functions = re.findall(r'^(?:def|async\s+def)\s+(\w+)', content, re.MULTILINE)
    elif filepath.endswith((".js", ".ts", ".jsx", ".tsx")):
        classes = re.findall(r'class\s+(\w+)', content)
        functions = re.findall(
            r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[a-zA-Z_]\w*)\s*=>)',
            content,
        )
        functions = [f[0] or f[1] for f in functions if f[0] or f[1]]
    elif filepath.endswith((".java", ".go", ".cpp", ".c")):
        functions = re.findall(
            r'(?:public|private|protected|static|func)?\s*\w+\s+(\w+)\s*\(',
            content,
        )

    return classes, functions

def parse_imports(filepath, content):
    imports = []
    if filepath.endswith(".py"):
        pattern = r'^(?:from|import)\s+([\w.]+)'
        found = re.findall(pattern, content, re.MULTILINE)
        imports = [f.replace(".", "/") for f in found]
    elif filepath.endswith((".js", ".ts", ".jsx", ".tsx")):
        pattern = r'(?:from|require)\s*[\'"]([^\'\"]+)[\'"]'
        imports = re.findall(pattern, content)
    return imports

def match_import_to_file(import_path, all_files):
    for f in all_files:
        if import_path in f or f.endswith(import_path + ".py"):
            return f
    return None

def get_impact(G, file_path):
    if file_path not in G.nodes:
        return {
            "affected_files": [],
            "risk_level": "unknown",
            "affected_count": 0
        }

    affected = list(nx.ancestors(G, file_path))
    risk_score = len(affected) / max(len(G.nodes), 1)

    return {
        "affected_files": affected,
        "risk_level": (
            "high" if risk_score > 0.3
            else "medium" if risk_score > 0.1
            else "low"
        ),
        "affected_count": len(affected)
    }

def export_graph(G):
    return {
        "nodes": [
            {
                "id": node,
                "extension": G.nodes[node].get("extension", ""),
                "size": G.nodes[node].get("size", 0),
                "connections": G.degree(node),
                "node_type": G.nodes[node].get("node_type", "file"),
                "classes": G.nodes[node].get("classes", []),
                "functions": G.nodes[node].get("functions", []),
            }
            for node in G.nodes
            if G.nodes[node].get("node_type", "file") == "file"
        ],
        "edges": [
            {"source": u, "target": v}
            for u, v in G.edges
            # Only export file-to-file edges for the main graph view
            if G.nodes.get(u, {}).get("node_type", "file") == "file"
            and G.nodes.get(v, {}).get("node_type", "file") == "file"
        ],
    }


# ── Graph Traversal Utilities ────────────────────────────────────────────────

def get_file_nodes(G):
    """Return only file-type nodes (exclude class/function sub-nodes)."""
    return [n for n in G.nodes if G.nodes[n].get("node_type", "file") == "file"]


def get_neighbors(G, filepath, depth=1):
    """
    Get all neighbors of a file up to `depth` hops.
    Returns {file: distance} dict.
    """
    neighbors = {}
    queue = [(filepath, 0)]
    visited = {filepath}

    while queue:
        node, d = queue.pop(0)
        if d > depth:
            continue
        if d > 0 and G.nodes.get(node, {}).get("node_type", "file") == "file":
            neighbors[node] = d

        if d < depth:
            for succ in G.successors(node):
                if succ not in visited:
                    visited.add(succ)
                    queue.append((succ, d + 1))
            for pred in G.predecessors(node):
                if pred not in visited:
                    visited.add(pred)
                    queue.append((pred, d + 1))

    return neighbors


def get_dependency_subgraph(G, filepaths, depth=2):
    """
    Extract a subgraph centered on the given files, including
    their dependencies up to `depth` levels.
    """
    relevant_nodes = set()
    for fp in filepaths:
        if fp in G:
            relevant_nodes.add(fp)
            neighbors = get_neighbors(G, fp, depth=depth)
            relevant_nodes.update(neighbors.keys())

    return G.subgraph(relevant_nodes).copy()