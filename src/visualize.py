import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from matplotlib.collections import LineCollection
import matplotlib.patches as mpatches
import networkx as nx


def plot_city_tolls(subG: nx.DiGraph, zone_nodes: list, solution: dict,
                   city_name: str, out_path: str,
                   kappa: int = None, P_l: int = 1, P_u: int = 5):
    fig, ax = plt.subplots(figsize=(14, 11))
    ax.set_facecolor("#f5f5f5")

    pos = {n: (data["x"], data["y"]) for n, data in subG.nodes(data=True)}
    tolled_set = {a for a, _ in solution["tolled_arcs"]}

    # Normal edges as a single rasterized LineCollection — fast and crisp at any zoom
    normal_segs = [
        [(pos[u][0], pos[u][1]), (pos[v][0], pos[v][1])]
        for u, v in subG.edges()
        if (u, v) not in tolled_set and u in pos and v in pos
    ]
    if normal_segs:
        ax.add_collection(LineCollection(normal_segs, colors="#cccccc",
                                         linewidths=0.6, zorder=1, rasterized=True))

    # Tolled edges colored by toll price: PuRd (light purple → dark red)
    toll_cmap = cm.get_cmap("PuRd")
    norm = mcolors.Normalize(vmin=P_l, vmax=P_u)
    for u, v in subG.edges():
        if (u, v) in tolled_set and u in pos and v in pos:
            toll = solution["arc_data"].get((u, v), {}).get("toll", P_l)
            color = toll_cmap(norm(max(float(toll), float(P_l))))
            ax.add_collection(LineCollection(
                [[(pos[u][0], pos[u][1]), (pos[v][0], pos[v][1])]],
                colors=[color], linewidths=0.6, zorder=3
            ))

    # Zone centroid nodes
    zone_xs = [pos[n][0] for n in zone_nodes if n in pos]
    zone_ys = [pos[n][1] for n in zone_nodes if n in pos]
    ax.scatter(zone_xs, zone_ys, c="#457b9d", s=80, zorder=5, linewidths=0)
    for i, n in enumerate(zone_nodes, 1):
        if n in pos:
            ax.annotate(str(i), xy=pos[n], fontsize=6.5, color="white",
                        ha="center", va="center", fontweight="bold", zorder=6)

    ax.autoscale()
    ax.set_aspect("equal")
    ax.axis("off")

    kappa_val = kappa if kappa is not None else len(solution["tolled_arcs"])
    ax.set_title(f"Toll Placement — {city_name} (κ={kappa_val})", fontsize=13, pad=12)

    # Colorbar: toll price scale
    sm = cm.ScalarMappable(cmap=toll_cmap, norm=mcolors.Normalize(vmin=P_l, vmax=P_u))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.35, pad=0.02, aspect=15)
    cbar.set_label("Toll price ($)", fontsize=9)
    cbar.set_ticks(list(range(P_l, P_u + 1)))

    # Legend for road network and zone centroids
    ax.legend(handles=[
        mpatches.Patch(color="#cccccc", label="Road arc"),
        mpatches.Patch(color="#457b9d", label="Zone centroid"),
    ], loc="lower left", fontsize=8, framealpha=0.8)

    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved map to {out_path}")
