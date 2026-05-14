import math
import networkx as nx


def detect_zone_nodes(G: nx.DiGraph, n_zones: int) -> list:
    nodes = list(G.nodes(data=True))
    xs = [d.get("x", 0) for _, d in nodes]
    ys = [d.get("y", 0) for _, d in nodes]

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    cols = math.ceil(math.sqrt(n_zones))
    rows = math.ceil(n_zones / cols)

    x_step = (x_max - x_min) / cols
    y_step = (y_max - y_min) / rows

    seen = set()
    zone_nodes = []

    for r in range(rows):
        for c in range(cols):
            if len(zone_nodes) >= n_zones:
                break
            cx = x_min + (c + 0.5) * x_step
            cy = y_min + (r + 0.5) * y_step
            nearest = _nearest_node(G, cx, cy)
            if nearest not in seen:
                seen.add(nearest)
                zone_nodes.append(nearest)

    return zone_nodes


def _nearest_node(G: nx.DiGraph, lon: float, lat: float):
    best_node = None
    best_dist = float("inf")
    for n, data in G.nodes(data=True):
        dx = data.get("x", 0) - lon
        dy = data.get("y", 0) - lat
        d2 = dx * dx + dy * dy
        if d2 < best_dist:
            best_dist = d2
            best_node = n
    return best_node


def build_path_subgraph(G: nx.DiGraph, zone_nodes: list, k_paths: int, demand_default: float):
    K_pairs = [(u, v) for u in zone_nodes for v in zone_nodes if u != v]

    edge_set = set()
    feasible_pairs = []
    total = len(K_pairs)
    for idx, (o, d) in enumerate(K_pairs, 1):
        print(f"  Path enum {idx}/{total}: {o} → {d}", end="\r")
        found = False
        try:
            path_gen = nx.shortest_simple_paths(G, o, d, weight="t_free")
            for _ in range(k_paths):
                try:
                    path = next(path_gen)
                    for u, v in zip(path[:-1], path[1:]):
                        edge_set.add((u, v))
                    found = True
                except StopIteration:
                    break
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass
        if found:
            feasible_pairs.append((o, d))

    skipped = len(K_pairs) - len(feasible_pairs)
    print(f"\n  {len(feasible_pairs)} feasible pairs ({skipped} skipped — no directed path)")

    subG = G.edge_subgraph(edge_set).copy()
    demand_map = {pair: demand_default for pair in feasible_pairs}

    return subG, feasible_pairs, demand_map
