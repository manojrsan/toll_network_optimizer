#!/usr/bin/env python3
import argparse
import json
import os
import csv
import networkx as nx
from tabulate import tabulate

from src import network, zones, optimizer, visualize


def main():
    parser = argparse.ArgumentParser(description="City toll placement optimizer")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    parser.add_argument("--no-plot", action="store_true", help="Skip map output")
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)

    city_name = cfg["city_name"]
    n_zones = cfg["n_zones"]
    k_paths = cfg["k_paths"]
    kappa = cfg["kappa"]
    P_l = cfg["P_l"]
    P_u = cfg["P_u"]
    n_breakpoints = cfg["n_breakpoints"]
    demand_default = cfg["demand_default"]
    time_limit = cfg["solver_time_limit"]
    solver = cfg.get("solver", "highs")

    city_slug = city_name.replace(",", "").replace(" ", "_").lower()[:30]
    cache_dir = "data"

    # 1) Download / load network
    G = network.download_city_network(city_name, cache_dir=cache_dir)
    print(f"Network: {G.number_of_nodes()} nodes, {G.number_of_edges()} arcs")

    # 2) Detect zone centroids
    zone_nodes = zones.detect_zone_nodes(G, n_zones)
    print(f"Zones detected: {len(zone_nodes)}")

    # 3) Build path-union subgraph
    print("Building path subgraph (this may take 1-2 min)...")
    subG, K_pairs, demand_map = zones.build_path_subgraph(
        G, zone_nodes, k_paths, demand_default
    )
    print(f"Subgraph: {subG.number_of_nodes()} nodes, {subG.number_of_edges()} arcs, "
          f"{len(K_pairs)} OD pairs")

    # override demands if specified
    if "demand_overrides" in cfg:
        for key, val in cfg["demand_overrides"].items():
            o_str, d_str = key.split("_to_")
            o_node = int(o_str.replace("node_", ""))
            d_node = int(d_str.replace("node_", ""))
            if (o_node, d_node) in demand_map:
                demand_map[(o_node, d_node)] = float(val)

    # 4) Solve MILP
    solution = optimizer.solve_toll_placement(
        subG, K_pairs, demand_map,
        kappa=kappa, P_l=P_l, P_u=P_u,
        n_breaks=n_breakpoints, time_limit=time_limit,
        solver=solver
    )
    print(f"GLPK status: {solution['status']}")
    print(f"Tolled arcs: {len(solution['tolled_arcs'])}")

    # 5) Per-OD revenue table
    print("\nPer-OD Revenue:")
    od_rows = []
    for (o, d) in K_pairs:
        try:
            arc_data = solution["arc_data"]
            path = nx.shortest_path(
                subG, o, d,
                weight=lambda u, v, data: data["t_free"] + arc_data.get((u, v), {}).get("toll", 0.0)
            )
            trip_toll = sum(
                arc_data.get((u, v), {}).get("toll", 0.0)
                for u, v in zip(path[:-1], path[1:])
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            trip_toll = 0.0

        demand = demand_map.get((o, d), demand_default)
        hourly_rev = demand * trip_toll
        daily_rev = hourly_rev * 24
        od_rows.append([f"{o} → {d}", f"{trip_toll:.2f}", f"{hourly_rev:.2f}", f"{daily_rev:.2f}"])

    print(tabulate(od_rows,
                   headers=["OD Pair", "Toll/Trip ($)", "Hourly Rev ($)", "Daily Rev ($)"],
                   tablefmt="simple"))

    # 6) Full arc results table
    arc_rows = []
    for a, data in solution["arc_data"].items():
        gap = data["phi"] - data["psi"]
        arc_rows.append([
            f"{a[0]}→{a[1]}",
            "Yes" if data["tolled"] else "No",
            f"{data['toll']:.1f}",
            f"{data['flow']:.1f}",
            f"{data['phi']:.6f}",
            f"{data['psi']:.6f}",
            f"{gap:.6f}",
        ])

    headers = ["Arc", "Tolled", "Toll ($)", "Flow (vph)", "φ_a (over)", "ψ_a (under)", "φ−ψ gap"]
    print("\nArc Results:")
    print(tabulate(arc_rows, headers=headers, tablefmt="simple"))

    # 7) Save CSV
    csv_path = os.path.join(cache_dir, f"{city_slug}_arc_results.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(arc_rows)
    print(f"\nArc results saved to {csv_path}")

    # 8) Plot
    if not args.no_plot:
        png_path = os.path.join(cache_dir, f"{city_slug}_tolls.png")
        visualize.plot_city_tolls(subG, zone_nodes, solution, city_name, png_path,
                                  kappa=kappa, P_l=P_l, P_u=P_u)

    # 9) Summary
    sum_phi = sum(d["phi"] for d in solution["arc_data"].values())
    sum_psi = sum(d["psi"] for d in solution["arc_data"].values())
    print(f"\nΣφ = {sum_phi:.6f}, Σψ = {sum_psi:.6f}, total gap = {sum_phi - sum_psi:.6f}")


if __name__ == "__main__":
    main()
