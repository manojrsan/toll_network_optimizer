import os
import networkx as nx
import osmnx as ox


def download_city_network(city_name: str, cache_dir: str) -> nx.DiGraph:
    city_slug = city_name.replace(",", "").replace(" ", "_").lower()[:30]
    cache_path = os.path.join(cache_dir, f"{city_slug}.graphml")

    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
        try:
            print(f"Loading cached network from {cache_path}")
            H = nx.read_graphml(cache_path)
            H = nx.relabel_nodes(H, {n: int(n) for n in H.nodes()})
            # restore numeric edge attributes that graphml reads back as strings
            for u, v, data in H.edges(data=True):
                for key in ("length", "t_free", "capacity"):
                    if key in data:
                        try:
                            data[key] = float(data[key])
                        except (ValueError, TypeError):
                            pass
            return H
        except Exception as e:
            print(f"Cache corrupt ({e}), re-downloading...")
            os.remove(cache_path)

    ox.settings.use_cache = True
    ox.settings.cache_folder = cache_dir

    print(f"Downloading network for {city_name}...")
    G = ox.graph_from_place(city_name, network_type="drive", simplify=True)

    # collapse MultiDiGraph → simple DiGraph using osmnx's built-in converter
    # (keeps the minimum-length edge for each parallel pair)
    H = ox.convert.to_digraph(G, weight="length")

    # strip geometry objects and non-essential attributes from edges
    keep_keys = {"length", "highway", "lanes", "maxspeed", "capacity"}
    for u, v, data in H.edges(data=True):
        for k in list(data.keys()):
            if k not in keep_keys:
                del data[k]
            else:
                data[k] = _safe_attr(data[k])

    # strip geometry from nodes
    for _, data in H.nodes(data=True):
        data.pop("geometry", None)
        for k, v in list(data.items()):
            data[k] = _safe_attr(v)

    _annotate_edges(H)

    os.makedirs(cache_dir, exist_ok=True)
    # sanitize for graphml before writing
    _sanitize_for_graphml(H)
    nx.write_graphml(H, cache_path)
    print(f"Cached network to {cache_path}")

    return H


def _safe_attr(v):
    """Convert a value to a graphml-safe scalar."""
    if isinstance(v, list):
        return str(v[0]) if v else ""
    if v is None:
        return ""
    return v


def _sanitize_for_graphml(G: nx.DiGraph):
    """Ensure all node/edge attributes are graphml-compatible scalars."""
    for _, data in G.nodes(data=True):
        for k, v in list(data.items()):
            if isinstance(v, (list, tuple)):
                data[k] = str(v[0]) if v else ""
            elif v is None:
                data[k] = ""

    for _, _, data in G.edges(data=True):
        for k, v in list(data.items()):
            if isinstance(v, (list, tuple)):
                data[k] = str(v[0]) if v else ""
            elif v is None:
                data[k] = ""


def _annotate_edges(G: nx.DiGraph):
    for u, v, data in G.edges(data=True):
        # normalize highway tag
        hwy = data.get("highway", "")
        if isinstance(hwy, list):
            hwy = hwy[0]
        data["highway"] = str(hwy).lower()

        # parse maxspeed → m/s
        speed_mps = 9.72  # fallback: 35 km/h
        if "maxspeed" in data and data["maxspeed"] not in ("", None):
            s = data["maxspeed"]
            if isinstance(s, (list, tuple)):
                s = s[0]
            s = str(s)
            try:
                num = float(s.split()[0])
                if "mph" in s.lower():
                    speed_mps = num * 0.44704
                else:
                    speed_mps = num / 3.6
            except (ValueError, IndexError):
                pass

        length = data.get("length", 0)
        try:
            length = float(length)
        except (ValueError, TypeError):
            length = 0.0
        data["length"] = length
        data["t_free"] = length / speed_mps if speed_mps > 0 else 0.0

        # capacity
        if "capacity" in data and data["capacity"] not in ("", None):
            try:
                data["capacity"] = float(data["capacity"])
            except (ValueError, TypeError):
                data["capacity"] = _lanes_capacity(data)
        else:
            data["capacity"] = _lanes_capacity(data)


def _lanes_capacity(data: dict) -> float:
    hwy = str(data.get("highway", "")).lower()
    per_lane = 2000.0 if hwy in ("motorway", "trunk") else 1800.0

    lanes_raw = data.get("lanes")
    if lanes_raw not in (None, ""):
        try:
            parts = str(lanes_raw).split(";")
            num_lanes = max(float(x) for x in parts)
            return per_lane * num_lanes
        except (ValueError, AttributeError):
            pass

    return 1000.0
