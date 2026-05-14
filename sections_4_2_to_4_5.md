# Senior Project Sections 4.2–4.5

## 4.2 Notation and Variables

We model the transportation network as a directed graph $G = (V, A)$, where $V$ is the set of nodes representing street and road intersections, and $A$ is the set of directed arcs representing road segments. Each arc $a \in A$ is defined as an ordered pair $a = (a_t, a_h)$, where $a_t \in V$ is the tail (starting node) and $a_h \in V$ is the head (ending node). Associated with each arc are two parameters: the free-flow travel time $t_a$, representing the time required to traverse arc $a$ under no congestion, and the capacity $c_a$, indicating the maximum traffic flow it can support before significant delays occur.

Let $K = \{(o(1), d(1)),(o(2),d(2)), \dots , (o(\vert K\vert),d(\vert K\vert))\} \subseteq V \times V$ be the set of origin–destination (OD) pairs, where each $(o(k), d(k))$ corresponds to a source node and a destination node, respectively, and is associated with a demand value $d_k$, representing the volume of traffic that must be routed from $o(k)$ to $d(k)$. The total demand in the network is denoted by $S = \sum_{k=1}^{|K|} d_k$. Let $Q \subseteq V$ denote the set of all destination nodes. For any node $v \in V$, we define $\text{IN}(v)$ as the set of incoming arcs to node $v$, and $\text{OUT}(v)$ as the set of outgoing arcs from node $v$. We also define $A^2_{\text{OUT}(v)}$ as the set of all ordered pairs of distinct arcs in $\text{OUT}(v)$.

To describe the routing of traffic, we introduce several variables. For each destination $q \in Q$ and arc $a \in A$, let $x^q_a \in \mathbb{R}_{\geq 0}$ denote the amount of flow on arc $a$ destined for node $q$. The total flow across arc $a$, summed over all destinations, is denoted $\ell_a \in \mathbb{R}_{\geq 0}$. To model congestion pricing, we define $w_a$ as the toll charged on arc $a$, where $w_a \in \{0, P_l, P_l +1, \dots P_u\}$ and $P_l, P_u \in \mathbb{N}_+$ are fixed lower and upper bounds. The binary variable $p_a \in \{0, 1\}$ indicates whether a tollbooth is deployed on arc $a$. We constrain the total number of tollbooths to a fixed constant $\kappa \in \mathbb{N}$.

To enforce shortest-path routing, we define the variable $y^q_a \in \{0, 1\}$ which indicates whether arc $a$ is part of a shortest path to destination $q$. The corresponding shortest-path cost from node $v \in V$ to destination $q \in Q$ is given by $\delta^q_v \in \mathbb{R}_{\geq 0}$. Additionally, we make use of large constants $M_1, M_2, M_3$ in constraints involving logical conditions and flow enforcement.

## 4.3 Model for Tollbooth Placement and Flow Optimization

$$\text{minimize } \Phi = \sum_{a\in A} \frac{\ell_a}{S}t_a \left[1 + \beta_a\left(\frac{\ell_a}{c_a}\right)^{\alpha_a}\right]$$

Subject to:

$$\ell_a = \sum_{q\in Q}x_a^q \quad  \forall a \in A,$$

$$\sum_{a \in OUT(v)} x_a^q - \sum_{a\in IN(v)} x_a^q = d_{v,q}, \quad \forall v\in V \setminus \{q\}, \forall q\in Q,,$$

$$C_a + w_a + \delta_{a_h}^q - \delta_{a_t}^q \geq 0,\quad \forall a\in A, \forall q \in Q,$$

$$\delta_q^q = 0, \quad \forall q\in Q,$$

$$C_a + w_a + \delta_{a_h}^q - \delta_{a_t}^q \geq (1 - y_a^q)/M_1, \quad \forall a\in A, \forall q\in Q,$$

$$C_a + w_a + \delta_{a_h}^q - \delta_{a_t}^q \leq (1 - y_a^q)M_2, \quad \forall a\in A, \forall q\in Q,$$

$$M_3y_a^q \geq x_a^q, \quad \forall a\in A, \forall q\in Q,$$

$$M_3y_a^q + M_3y_b^q \leq 2M_3 - x_a^q + x_b^q, \quad \forall a,b \in A^2_{OUT(v)}, \forall v\in V, \forall q \in Q,$$

$$P_lp_a \leq w_a \leq P_up_a, \quad \forall a \in A,$$

$$\sum_{a\in A} p_a = \kappa, \quad \forall a\in A,$$

$$x_a^q \geq 0, \quad \forall a \in A, \forall q \in Q,$$

$$\ell_a \geq 0, \quad \forall a \in A,$$

$$w_a \geq 0, \quad \forall a\in A,$$

$$\delta_v^q \geq 0, \quad \forall q\in Q, \forall v\in V,$$

$$p_a \in \{0,1\}, \quad \forall a \in A.$$

The objective function is a congestion-aware potential function. For each arc $a$, we compute the cost of traffic as: $$\Phi_a = \frac{\ell_a}{S} t_a \left[1 + \beta_a \left(\frac{\ell_a}{c_a} \right)^{\alpha_a} \right],$$ which increases with traffic volume. This function is strictly increasing and convex in $\ell_a$, ensuring that heavier congestion leads to disproportionately higher costs. The parameters $\alpha_a$ and $\beta_a$ are two real-valued constants that parameterize $\Phi_a$, allowing the model to capture arc-specific sensitivity to congestion. Summing over all arcs, the total network cost $\Phi$ reflects the average cost of routing all demand under congestion effects.

The decision variables in this model are $x^q_a$, $\ell_a$, $w_a$, $p_a$, $y^q_a$, and $\delta^q_v$. These variables determine both how traffic is routed and where tollbooths are placed. Specifically, $x^q_a$ controls the routing of demand across the network, and $\ell_a$ aggregates that routing across all destinations. The binary variable $p_a$ decides whether a tollbooth is installed on arc $a$, and $w_a$ sets the corresponding toll, bounded if and only if $p_a = 1$. The variable $y^q_a$ identifies which arcs form part of shortest paths to each destination $q$, and $\delta^q_v$ quantifies the cost of those shortest paths.

**(2) Total Arc Load:** $\ell_a = \sum_{q \in Q} x^q_a$. The load on arc $a$ is the sum of all flow on it across every destination. This defines how congested each arc becomes due to aggregate routing.

**(3) Flow Conservation:** For each $v \in V \setminus \{q\}$, $\sum_{a \in \text{OUT}(v)} x^q_a - \sum_{a \in \text{IN}(v)} x^q_a = d_{v,q}$. This ensures that traffic is preserved as it flows from origins to destinations. If $v$ is the origin of flow to $q$, then $d_{v,q} > 0$; if $v$ is a middle node, $d_{v,q} = 0$, preserving flow balance.

**(4) Shortest-Path Cost Consistency:** $C_a + w_a + \delta^q_{a_h} - \delta^q_{a_t} \geq 0$. This constraint ensures that our estimate of the shortest-path cost does not undercut actual costs. It enforces consistency in cost labelling across adjacent nodes.

**(5) Base Case for Shortest Path:** $\delta^q_q = 0$. The cost from a node to itself is defined as zero, anchoring all other distance estimates.

**(6) Shortest-Path Exclusion:** $C_a + w_a + \delta^q_{a_h} - \delta^q_{a_t} \geq \frac{1 - y^q_a}{M_1}$. If arc $a$ is not part of the shortest path to $q$, i.e. $y^q_a = 0$, this forces the cost through $a$ to be strictly worse than the best path, preventing $a$ from being selected.

**(7) Shortest-Path Equality:** $C_a + w_a + \delta^q_{a_h} - \delta^q_{a_t} \leq (1 - y^q_a) M_2$. When $y^q_a = 1$, this constraint, together with (5), forces equality: $C_a + w_a + \delta^q_{a_h} - \delta^q_{a_t} = 0$, confirming that $a$ is indeed on the shortest path.

**(8) Flow-Path Binding:** $M_3 y^q_a \geq x^q_a$. If $y^q_a = 0$, then $x^q_a = 0$; flow cannot occur along arcs not in the shortest path. If $y^q_a = 1$, the constraint becomes non-binding due to the large value of $M_3 = \max_{q\in Q} \left(\sum_{v\in V}d_{v,q}\right)$.

**(9) Even Flow Splitting:** For any $v \in V$, if two outgoing arcs $a, b \in A^2_{\text{OUT}(v)}$ are both on shortest paths to $q$, then $x^q_a = x^q_b$. This constraint enforces symmetric routing when multiple equally optimal paths exist from a node.

**(10) Toll Price Bounds:** $P_l p_a \leq w_a \leq P_u p_a$. If $p_a = 0$, then $w_a = 0$, i.e. no toll is charged on untolled arcs. If $p_a = 1$, the toll must lie between allowable limits.

**(11) Tollbooth Count:** $\sum_{a \in A} p_a = \kappa$. Exactly $\kappa$ tollbooths are installed in the network; no more, no fewer.

**(12–16) Feasibility Conditions:** These constraints enforce non-negativity of continuous variables and binary enforcement for $p_a$, reflecting practical and physical feasibility of the model.

## 4.4 Piecewise-Linear Approximations in Tollbooth Optimization

In tollbooth optimization, one of the primary challenges lies in modelling and minimizing traffic congestion across a network. This congestion is often captured by a nonlinear objective function

$$\Phi = \sum_{a \in A} \Phi_a.$$

where $\Phi_a$ represents the cost on arc $a$ as a function of traffic load. While accurate, this formulation introduces convexity and nonlinearity that are incompatible with standard mixed-integer linear programming (MILP) solvers. As a result, the need arises for a tractable approximation that retains the core structure of the problem while allowing for efficient computation. We will address this by introducing two piecewise-linear approximations of $\Phi$, enabling the use of MILP solvers while preserving solution quality through bounding.

### Motivation for Linearization

The function $\Phi_a$ is inherently nonlinear due to how travel time increases disproportionately with arc load, especially as usage approaches or exceeds capacity. Although modern MILP solvers have become more powerful, they still require linear formulations to ensure reasonable solve times on large instances. The piecewise-linear approximation approach is well-suited here: it simplifies the nonlinear form into a series of linear segments while maintaining key convexity properties. This strategy builds on earlier work in routing and congestion modelling, such as Fortz and Thorup [@dial2004toll] and Ekström et al. [@li2012modeling], who used similar techniques in related contexts.

### Overestimation ($\varphi^u$)

The overestimation approximation, denoted $\varphi^u$, constructs a piecewise-linear function that sits entirely above the original nonlinear function $\Phi_a$. It connects a predefined set of points $(X_i, \Phi_a(X_i))$, with increasing values $X_0 < X_1 < \cdots < X_n$, representing different levels of arc load relative to capacity. The slope and intercept of each segment are calculated to ensure that the resulting function always overestimates the true cost. This conservative approach guarantees feasibility and avoids underestimating traffic impacts.

### Underestimation ($\varphi^\ell$)

Conversely, the underestimation approximation, $\varphi^\ell$, provides a lower bound on the true cost. Instead of segment endpoints, this version calculates linear tangents at the midpoint of each interval $(X_{i-1}, X_i)$, using the derivative of $\Phi_a$ with respect to load. This function lies entirely below $\Phi_a$ and provides a benchmark for how good a given solution is relative to the minimum possible cost.

## 4.5 Piecewise-linear Functions for the Model for Tollbooth Placement and Flow Optimization

$$\min\sum_{a \in A} \varphi_a^u \quad \text{and}\quad \min\sum_{a \in A}\varphi_a^l$$

Subject to:

$$\text{Constraints } \Omega \text{ are satisfied},$$

$$\left(\frac{m_a^i}{c_a}\right)\ell_a + b_a^i \leq \varphi_a^u,\quad \forall a\in A, \quad \forall i = 1,\dots,n,$$

$$\varphi_a^u \geq  0, \quad \forall a\in A.$$

where

$$m_a^i = \frac{\left(\Phi_a(X_i) - \Phi_a(X_{i-1})\right)}{\left(X_i - X_{i-1}\right)}$$

$$b_a^i = \Phi_a(X_i) - X_im_a^i.$$

where

$$\Phi_a(X_i) = \frac{X_ic_at_a(1 + \beta_a(X_i)^{\alpha_a})}{S}$$

for $X_0 = 0 < X_1 < \dots < X_n$.

A similar formulation is used for the underestimation $\varphi^\ell_a$, except that instead of using linear segments between known points, the approximation is built using **tangent lines** at the **midpoints** of each segment interval $(X_{i-1}, X_i)$. Specifically, for each midpoint $$x = \frac{X_{i-1} + X_i}{2},$$ one must compute the *derivative of the nonlinear cost function* $\Phi_a$:

$$m_a(x) = \frac{t_a}{S} + \frac{(\alpha_a + 1) t_a \beta_a x^{\alpha_a}}{c_a^{\alpha_a} S}.$$ This slope $m_a(x)$ is then used to construct a tangent line at $x$ that underestimates $\Phi_a$. The corresponding intercept is computed as: $$b_a(x) = \Phi_a(x) - m_a(x) \cdot x,$$ and the linear underestimation constraint becomes: $$\frac{\ell_a}{c_a} \cdot m_a(x) + b_a(x) \leq \varphi^\ell_a.$$ These constraints ensure that $\varphi^\ell_a$ lies entirely **below** the convex cost curve, and thus forms a valid lower bound on the arc cost.

**(18) Model Constraints:** All constraints from the base model (constraints (2)-(16)), denoted $\Omega$, must be satisfied. These include flow conservation, toll placement limits, shortest-path consistency, and capacity bounds. This ensures that the routing and toll decisions remain feasible within the structure of the transportation network.

**(19) Piecewise Arc Cost Approximation:** For each arc $a \in A$ and segment $i = 1,\dots,n$, the linear approximation depends on whether we are constructing an upper or lower bound:

- *Overestimation:* $$\frac{m^i_a}{c_a} \ell_a + b^i_a \leq \varphi^u_a.$$

  This guarantees that the estimated cost $\varphi^u_a$ lies **above** each linear segment of the convex cost function $\Phi_a$. The segments are defined using known points on the cost curve, forming a piecewise-linear upper bound. The resulting objective value $\sum_a \varphi^u_a$ overestimates the total user travel cost, providing a feasible solution.

- *Underestimation:* $$\frac{m_a(x)}{c_a} \ell_a + b_a(x) \leq \varphi^\ell_a,$$

  where $x = \frac{X_{i-1} + X_i}{2}$ and $m_a(x)$ is the derivative of $\Phi_a$ at $x$. This uses the slope of a tangent line to construct a linear under-approximation of the cost. It ensures that $\varphi^\ell_a$ lies **below** the true cost function, resulting in a valid lower bound on the total cost.

**(20) Non-Negative Arc Cost:** $\varphi^u_a \geq 0$ or $\varphi^\ell_a \geq 0$. These constraints enforce that the estimated arc costs remain non-negative, reflecting the reality that toll or travel time cannot be less than zero.

### Trade off Between Accuracy and Complexity

A key design trade off involves choosing the number and location of the breakpoints $X_i$. More points lead to a better approximation but increase the number of constraints (specifically, $|A| \times n$). This adds computational overhead and must be balanced based on problem size and solver capacity.

### Theoretical Properties

The paper presents

> **Proposition.** Let $$\varphi^u = \sum_{a \in A}\varphi_a^u ,\quad \varphi^l = \sum_{a \in A}\varphi_a^l,$$ and as before $$\Phi = \sum_{a \in A}\Phi_a.$$ Let $X_0,X_1,\dots,X_n$ be the values for which the approximation is computed. If $\ell_a/c_a \leq X_n$ $\forall a\in A$, then $\varphi^l \leq \Phi \leq \varphi^u$

This result is guaranteed by the convexity of $\Phi_a$ and confirms that the two approximations serve as legitimate lower and upper bounds. This is particularly useful in practice, as it gives the model both a feasible solution and a quantifiable optimality gap.

### Practical Considerations

The authors note that flow in real transportation networks tends to cluster around capacity. Therefore, they recommend placing more breakpoints near $\ell_a / c_a = 1$, where congestion effects are most pronounced. This increases the fidelity of the approximation in critical regions. The paper’s figure illustrates this strategy and the resulting curve behavior. This breakpoint placement is a clever modelling decision that increases accuracy without requiring a large number of points across the entire domain.

### Broader Implications and Extensions

This dual approximation framework is general and can be extended to other network design or pricing problems involving nonlinear costs. It also supports hybrid approaches like branch-and-bound or metaheuristics (e.g., BRKGA), where the bounds help evaluate solution quality. Potential extensions could include adaptive breakpoint selection, piecewise-quadratic models, or solver-guided refinement based on instance-specific data.
