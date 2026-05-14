import pulp
import networkx as nx


def solve_toll_placement(subG: nx.DiGraph, K_pairs: list, demand_map: dict,
                         kappa: int, P_l: int, P_u: int,
                         n_breaks: int, time_limit: int,
                         solver: str = "highs") -> dict:
    """
    MILP toll placement with OD-pair-indexed flow and SP variables.

    Using destination-only indexing (y[(a,q)], delta[(v,q)]) allows the LP
    to split one destination's flow across paths that use BOTH (u,v) and (v,u),
    which forces y[(u,v),q]=1 and y[(v,u),q]=1 simultaneously when rounded to
    binary — creating the cycle  delta[u] = t + delta[v] = t + t + delta[u],
    i.e. 0 = 2t > 0, which is infeasible.

    Indexing by OD pair (o,d) instead gives each pair its own y and delta
    variables.  A single simple SP from o to d is acyclic, so binary y is
    always MIP-feasible.
    """
    V = list(subG.nodes())
    A = list(subG.edges())
    K = K_pairs  # list of (o, d) pairs

    t_free_map = {a: max(float(subG.edges[a]["t_free"]), 1.0) for a in A}
    capacity_map = {a: max(float(subG.edges[a].get("capacity", 1000.0)), 1.0) for a in A}

    alpha = {}
    beta = {}
    for a in A:
        hwy = str(subG.edges[a].get("highway", "")).lower()
        if hwy in ("motorway", "trunk"):
            alpha[a], beta[a] = 4.0, 0.15
        elif hwy in ("primary", "secondary", "tertiary"):
            alpha[a], beta[a] = 3.0, 0.20
        elif hwy in ("unclassified", "residential", "service"):
            alpha[a], beta[a] = 2.0, 0.25
        else:
            alpha[a], beta[a] = 2.0, 0.30

    eps = 1e-3
    S = sum(demand_map.values())

    OUT = {v: [] for v in V}
    IN = {v: [] for v in V}
    for u, v in A:
        OUT[u].append((u, v))
        IN[v].append((u, v))

    # M2 must exceed max(t_free_a + w_a + delta_v - delta_u) for non-SP arcs.
    # delta is bounded by sum of all t_free (no path can exceed total network cost).
    # Using sum(t_free) + P_u instead of 1e7 eliminates cut-generator numerical
    # false-infeasibility from ill-conditioned big-M constraints.
    M2 = max(sum(t_free_map.values()) + max(t_free_map.values()) + P_u + 1.0, 1e4)
    M3 = max(1e4, max(demand_map.values()) * 2)

    prob = pulp.LpProblem("Toll_PWL_OD", pulp.LpMinimize)

    # ── decision variables ────────────────────────────────────────────────────
    p = {a: pulp.LpVariable(f"p_{a[0]}_{a[1]}", cat="Binary") for a in A}
    w = {a: pulp.LpVariable(f"w_{a[0]}_{a[1]}", lowBound=0, upBound=P_u,
                             cat="Integer") for a in A}

    # OD-pair indexed flow and SP variables
    x = {(a, k): pulp.LpVariable(f"x_{a[0]}_{a[1]}_{k[0]}_{k[1]}",
                                  lowBound=0, cat="Continuous")
         for a in A for k in K}
    ell = {a: pulp.LpVariable(f"ell_{a[0]}_{a[1]}", lowBound=0,
                               cat="Continuous") for a in A}
    # delta[(v, (o,d))]: shortest-path potential at v for OD pair (o,d)
    delta = {(v, k): pulp.LpVariable(f"delta_{v}_{k[0]}_{k[1]}",
                                      lowBound=0, cat="Continuous")
             for v in V for k in K}
    # y[(a, (o,d))]: 1 if arc a is on the SP for OD pair (o,d)
    y = {(a, k): pulp.LpVariable(f"y_{a[0]}_{a[1]}_{k[0]}_{k[1]}",
                                  cat="Binary")
         for a in A for k in K}
    # phi/psi scaled by S for numerical conditioning
    phi = {a: pulp.LpVariable(f"phi_{a[0]}_{a[1]}", lowBound=0,
                               cat="Continuous") for a in A}
    psi = {a: pulp.LpVariable(f"psi_{a[0]}_{a[1]}", lowBound=0,
                               cat="Continuous") for a in A}

    print(f"Variables: {len(A)} arcs, {len(K)} OD pairs | "
          f"S={S:.0f} M2={M2:.2f} M3={M3:.0e}")

    # ── link flow ────────────────────────────────────────────────────────────
    for a in A:
        prob += ell[a] == pulp.lpSum(x[(a, k)] for k in K), f"LinkFlow_{a}"

    # ── flow conservation (OD-pair indexed) ──────────────────────────────────
    # For pair k=(o,d): inject demand at origin o, absorb at dest d,
    # conserve at all intermediate nodes.
    for k in K:
        o, d = k
        for v in V:
            if v == d:
                continue  # skip destination (implicit sink)
            dvk = demand_map[k] if v == o else 0.0
            prob += (pulp.lpSum(x[(a, k)] for a in OUT[v])
                     - pulp.lpSum(x[(a, k)] for a in IN[v])
                     == dvk), f"FlowCons_{v}_{k[0]}_{k[1]}"

    # ── toll bounds & budget ─────────────────────────────────────────────────
    for a in A:
        prob += w[a] >= P_l * p[a], f"TollLo_{a}"
        prob += w[a] <= P_u * p[a], f"TollUp_{a}"
    prob += pulp.lpSum(p[a] for a in A) == kappa, "Budget"

    # ── shortest-path big-M constraints (OD-pair indexed) ───────────────────
    # For pair k=(o,d): destination d has zero potential.
    # CRITICAL: for any arc (d,n) leaving destination d, y[(d,n),k] must be 0.
    # If y=1 for such an arc, SPhigh forces delta[d,k] ≥ t_free > 0, but
    # delta[d,k]=0 is forced → infeasible. We fix y=0 explicitly.
    dest_set = {k: k[1] for k in K}

    for k in K:
        o, d = k
        prob += delta[(d, k)] == 0, f"Delta_dest_{d}_{k[0]}_{k[1]}"

    for a in A:
        u, v = a
        for k in K:
            # block y=1 for arcs leaving the destination of this pair
            if u == dest_set[k]:
                y[(a, k)].upBound = 0
                continue
            expr = (t_free_map[a] + eps) + w[a] + delta[(v, k)] - delta[(u, k)]
            prob += expr >= 0,                     f"SPpos_{a}_{k}"
            prob += expr <= M2 * (1 - y[(a, k)]), f"SPhigh_{a}_{k}"
            prob += x[(a, k)] <= M3 * y[(a, k)],  f"LinkXY_{a}_{k}"

    # ── piecewise-linear BPR (scaled by S) ──────────────────────────────────
    for a in A:
        cap = capacity_map[a]
        t_a = t_free_map[a]
        Xs = [i / n_breaks * cap for i in range(n_breaks + 1)]
        phi_sc = [X * t_a * (1 + beta[a] * (X / cap) ** alpha[a]) for X in Xs]

        for i in range(1, len(Xs)):
            x0, x1 = Xs[i - 1], Xs[i]
            f0, f1 = phi_sc[i - 1], phi_sc[i]
            m = (f1 - f0) / (x1 - x0) if x1 != x0 else 0.0
            b = f1 - m * x1
            prob += m * ell[a] + b <= phi[a], f"over_{a}_{i}"

        for i in range(1, len(Xs)):
            xm = (Xs[i - 1] + Xs[i]) / 2.0
            m_mid = t_a * (1 + (1 + alpha[a]) * beta[a] * (xm / cap) ** alpha[a])
            f_mid = xm * t_a * (1 + beta[a] * (xm / cap) ** alpha[a])
            b_mid = f_mid - m_mid * xm
            prob += m_mid * ell[a] + b_mid <= psi[a], f"under_{a}_{i}"

    # ── objective ────────────────────────────────────────────────────────────
    prob += pulp.lpSum(phi[a] for a in A), "Scaled_Congestion_Cost"

    if solver == "highs":
        print("Solving with HiGHS...")
        slvr = pulp.HiGHS(msg=True, timeLimit=time_limit)
    elif solver == "gurobi":
        print("Solving with Gurobi...")
        slvr = pulp.GUROBI_CMD(msg=True, timeLimit=time_limit)
    else:
        print("Solving with CBC...")
        slvr = pulp.PULP_CBC_CMD(msg=True, timeLimit=time_limit)
    status = prob.solve(slvr)
    status_str = pulp.LpStatus[status]
    print(f"Status: {status_str}")

    tolled_arcs = [(a, pulp.value(w[a])) for a in A if (pulp.value(p[a]) or 0) > 0.5]

    arc_data = {}
    for a in A:
        arc_data[a] = {
            "tolled": (pulp.value(p[a]) or 0) > 0.5,
            "toll":   pulp.value(w[a]) or 0.0,
            "flow":   pulp.value(ell[a]) or 0.0,
            "phi":    (pulp.value(phi[a]) or 0.0) / S,
            "psi":    (pulp.value(psi[a]) or 0.0) / S,
        }

    return {
        "status":      status_str,
        "objective":   (pulp.value(prob.objective) or 0.0) / S,
        "tolled_arcs": tolled_arcs,
        "arc_data":    arc_data,
    }
