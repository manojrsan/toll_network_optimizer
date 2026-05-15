import os
import networkx as nx
import osmnx as ox

# Realistic free-flow speeds by highway type (mph).
# These reflect typical observed travel speeds, not posted limits.
_SPEED_MPH = {
    "motorway":      72.0,   # US-101: posted 65, people drive 70-75
    "motorway_link": 45.0,
    "trunk":         55.0,   # state routes (SR-1)
    "trunk_link":    35.0,
    "primary":       40.0,   # Foothill Blvd, Los Osos Valley Rd
    "secondary":     35.0,   # Broad St, South St
    "tertiary":      30.0,   # local arterials
    "unclassified":  25.0,
    "residential":   22.0,
    "service":       12.0,   # parking aisles, alleys
}
_SPEED_DEFAULT_MPH = 25.0

# When a maxspeed tag exists, scale it by this factor.
# Freeways: drivers exceed the limit; residential: slightly under.
_COMPLIANCE = {
    "motorway":      1.10,
    "motorway_link": 1.05,
    "trunk":         1.05,
    "trunk_link":    1.00,
    "primary":       1.00,
    "secondary":     0.95,
    "tertiary":      0.90,
    "unclassified":  0.90,
    "residential":   0.85,
    "service":       0.80,
}

# Realistic capacity per lane (vph) by highway type.
_CAPACITY_PER_LANE = {
    "motorway":      2200,
    "motorway_link": 1800,
    "trunk":         1900,
    "trunk_link":    1600,
    "primary":       1700,
    "secondary":     1600,
    "tertiary":      1400,
    "unclassified":  1200,
    "residential":    800,
    "service":        600,
}
_CAPACITY_DEFAULT = 1000

# Default lane count when OSM has no lanes tag.
_DEFAULT_LANES = {
    "motorway": 2, "motorway_link": 1,
    "trunk": 2,    "trunk_link": 1,
    "primary": 2,  "secondary": 2,
    "tertiary": 1, "unclassified": 1,
    "residential": 1, "service": 1,
}


def download_city_network(city_name: str, cache_dir: str) -> nx.DiGraph:
    city_slug = city_name.replace(",", "").replace(" ", "_").lower()[:30]
    cache_path = os.path.join(cache_dir, f"{city_slug}.graphml")

    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
        try:
            print(f"Loading cached network from {cache_path}")
            H = nx.read_graphml(cache_path)
            H = nx.relabel_nodes(H, {n: int(n) for n in H.nodes()})
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

    H = ox.convert.to_digraph(G, weight="length")

    keep_keys = {"length", "highway", "lanes", "maxspeed", "capacity"}
    for u, v, data in H.edges(data=True):
        for k in list(data.keys()):
            if k not in keep_keys:
                del data[k]
            else:
                data[k] = _safe_attr(data[k])

    for _, data in H.nodes(data=True):
        data.pop("geometry", None)
        for k, v in list(data.items()):
            data[k] = _safe_attr(v)

    _annotate_edges(H)

    os.makedirs(cache_dir, exist_ok=True)
    _sanitize_for_graphml(H)
    nx.write_graphml(H, cache_path)
    print(f"Cached network to {cache_path}")

    return H


def _safe_attr(v):
    if isinstance(v, list):
        return str(v[0]) if v else ""
    if v is None:
        return ""
    return v


def _sanitize_for_graphml(G: nx.DiGraph):
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
        hwy = str(hwy).lower()
        data["highway"] = hwy

        # --- realistic free-flow speed ---
        # If OSM has a maxspeed tag, scale it by a per-type compliance factor
        # (drivers exceed limits on freeways, go slightly under on residential).
        # If no tag, use the type-based table directly.
        parsed_mph = None
        ms = data.get("maxspeed", "")
        if ms not in ("", None):
            raw = str(ms)
            try:
                num = float(raw.split()[0])
                parsed_mph = num if "mph" in raw.lower() else num * 0.621371
            except (ValueError, IndexError):
                pass

        if parsed_mph is not None:
            speed_mph = parsed_mph * _COMPLIANCE.get(hwy, 1.0)
        else:
            speed_mph = _SPEED_MPH.get(hwy, _SPEED_DEFAULT_MPH)

        speed_mps = speed_mph * 0.44704

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
    per_lane = _CAPACITY_PER_LANE.get(hwy, _CAPACITY_DEFAULT)

    lanes_raw = data.get("lanes")
    if lanes_raw not in (None, ""):
        try:
            parts = str(lanes_raw).split(";")
            num_lanes = max(float(x) for x in parts)
            return per_lane * num_lanes
        except (ValueError, AttributeError):
            pass

    lanes = _DEFAULT_LANES.get(hwy, 1)
    return per_lane * lanes
