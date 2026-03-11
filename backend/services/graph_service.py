import networkx as nx
import re

def build_graph(file_tree, file_contents):
    G = nx.DiGraph()

    for file in file_tree:
        ext = file["path"].split(".")[-1] if "." in file["path"] else "unknown"
        G.add_node(file["path"],
            extension=ext,
            size=file.get("size", 0),
        )

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
                "connections": G.degree(node)
            }
            for node in G.nodes
        ],
        "edges": [
            {"source": u, "target": v}
            for u, v in G.edges
        ]
    }