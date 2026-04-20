import streamlit as st
from itertools import combinations
from typing import Dict, Set
from collections import defaultdict
from helpers import (
    get_param_name_by_id,
    get_value_name_by_id,
)
import math
import heapq

# ----- CONCEPTS CALCULATION -----

def build_formal_context(configurations: Dict[str, Dict[str, str]]):
   objects = sorted(configurations.keys())
   attributes = set()
   incidence = {}

   for cid, cfg in configurations.items():
       attrs = set()
       for param, value in cfg.items():
           attrs.add(f"{param} = {value}")
           attributes.add(f"{param} = {value}")
       incidence[cid] = attrs

   return objects, attributes, incidence


def extent_from_intent(intent: Set[str], incidence: Dict[str, Set[str]]) -> Set[str]:
   return {obj for obj, attrs in incidence.items() if intent.issubset(attrs)}


def intent_from_extent(extent: Set[str], incidence: Dict[str, Set[str]]) -> Set[str]:
   if not extent:
       return set()
   shared = incidence[next(iter(extent))].copy()
   for obj in extent:
       shared &= incidence[obj]
   return shared

def compute_formal_concepts(configurations: Dict[str, Dict[str, str]]):
   objects, attributes, incidence = build_formal_context(configurations)

   concepts = []
   seen = set()
   attr_list = sorted(attributes)

   for r in range(1, len(attr_list) + 1):
       for subset in combinations(attr_list, r):
           extent = extent_from_intent(set(subset), incidence)
           if not extent:
               continue
           intent = intent_from_extent(extent, incidence)
           key = (frozenset(extent), frozenset(intent))
           if key not in seen:
               seen.add(key)
               concepts.append({"extent": set(extent), "intent": set(intent)})

   # Top concept
   top_extent = set(objects)
   top_intent = intent_from_extent(top_extent, incidence)
   key = (frozenset(top_extent), frozenset(top_intent))
   if key not in seen:
       concepts.append({"extent": top_extent, "intent": top_intent})

   return {f"Konsept {i+1}": c for i, c in enumerate(concepts)}

def compute_edges(concepts):
   edges = []
   for id1, c1 in concepts.items():
       for id2, c2 in concepts.items():
           if id1 == id2:
               continue
           if c1["extent"].issubset(c2["extent"]):
               is_cover = True
               for id3, c3 in concepts.items():
                   if id3 in (id1, id2):
                       continue
                   if (
                       c1["extent"].issubset(c3["extent"])
                       and c3["extent"].issubset(c2["extent"])
                       and c1["extent"] != c3["extent"]
                       and c3["extent"] != c2["extent"]
                   ):
                       is_cover = False
                       break
               if is_cover:
                   edges.append((id1, id2))
   return edges

# ----- EVALUATE CONCEPTS -----

def compute_attribute_frequencies(concepts):
    freq = defaultdict(int)
    total = 0
    for c in concepts.values():
        for a in c["intent"]:
            freq[a] += 1
            total += 1
    return {a: freq[a] / total for a in freq}

def abstraction_loss(c_child, c_parent, attr_freq):

    dropped_attrs = c_child["intent"] - c_parent["intent"]

    # Cost: sum of inverse attribute frequencies
    return sum(1 / (attr_freq.get(a, 1e-6)) for a in dropped_attrs)

def compute_persistence(concepts, edges, attr_freq):

    graph = defaultdict(list)
    for child, parent in edges:
        cost = abstraction_loss(
            concepts[child],
            concepts[parent],
            attr_freq
        )
        graph[child].append((parent, cost))

    persistence = {}

    for start in concepts:
        # Dijkstra from this concept upward
        dist = {start: 0.0}
        pq = [(0.0, start)]
        best = math.inf

        while pq:
            d, u = heapq.heappop(pq)
            if d >= best:
                continue

            # first encounter of a *strictly more abstract* concept
            if len(concepts[u]["extent"]) > len(concepts[start]["extent"]):
                best = d
                break

            for v, cost in graph.get(u, []):
                nd = d + cost
                if nd < dist.get(v, math.inf):
                    dist[v] = nd
                    heapq.heappush(pq, (nd, v))

        persistence[start] = best if best < math.inf else None

    return persistence

def rescale_persistence_0_100(persistence, tol=1e-9):

    finite_vals = [p for p in persistence.values() if p is not None]

    if not finite_vals:
        return persistence.copy()

    p_min = min(finite_vals)
    p_max = max(finite_vals)

    # avoid division by zero if all values are equal
    if abs(p_max - p_min) < tol:
        return {
            cid: (100.0 if p is not None else None)
            for cid, p in persistence.items()
        }

    return {
        cid: (
            100.0 * (p - p_min) / (p_max - p_min)
            if p is not None else None
        )
        for cid, p in persistence.items()
    }

# Konsept-verdi (slik at man enkelt senere kan endre på denne

def concept_score(cid, concepts, persistence):

    return persistence[cid]

def overlap(c1, c2):
    e1, e2 = c1["extent"], c2["extent"]
    return len(e1 & e2) / min(len(e1), len(e2))


def select_portfolio(concepts, persistence, params):
    tau = params["persistence_threshold"]
    epsilon = params["overlap_epsilon"]

    # Step 1: candidate pool
    candidates = [
        cid for cid, c in concepts.items()
        if persistence[cid] is not None
        and persistence[cid] >= tau
        and len(c["extent"]) >= 1
    ]

    # Step 2: rank candidates
    candidates.sort(
        key=lambda cid: concept_score(cid, concepts, persistence),
        reverse=True
    )

    selected = []
    uncovered = set().union(*[c["extent"] for c in concepts.values()])

    # Step 3: greedy selection
    for cid in candidates:
        if all(
            overlap(concepts[cid], concepts[s]) <= epsilon
            for s in selected
        ):
            selected.append(cid)
            uncovered -= concepts[cid]["extent"]

        if not uncovered:
            break

    # Step 4: patch uncovered
    for cid, c in concepts.items():
        if len(c["extent"]) == 1:
            g = next(iter(c["extent"]))
            if g in uncovered:
                selected.append(cid)
                uncovered.remove(g)

    return set(selected)

# ----- GRAPHVIZ -----

def score_to_red_green_hex(score, min_score, max_score, tol=1e-9):
    if score is None:
        return "#444444"

    if abs(max_score - min_score) < tol:
        t = 0.5
    else:
        t = (float(score) - float(min_score)) / (float(max_score) - float(min_score))

    t = max(0.0, min(1.0, t))
    # Keep a clearly saturated green->red ramp, but avoid neon brightness.
    low_rgb = (0, 220, 0)      # readable dark green
    high_rgb = (255, 0, 0)     # readable deep red
    red = int(low_rgb[0] + t * (high_rgb[0] - low_rgb[0]))
    green = int(low_rgb[1] + t * (high_rgb[1] - low_rgb[1]))
    blue = int(low_rgb[2] + t * (high_rgb[2] - low_rgb[2]))
    return f"#{red:02x}{green:02x}{blue:02x}"

def transform_edges_to_graphviz(edges, edge_losses=None):
    graphviz_edges = []
    finite_losses = [value for value in (edge_losses or {}).values() if value is not None]
    min_loss = min(finite_losses) if finite_losses else 0.0
    max_loss = max(finite_losses) if finite_losses else 1.0

    for id1, id2 in edges:
        if edge_losses and (id1, id2) in edge_losses:
            loss = edge_losses[(id1, id2)]
            font_color = score_to_red_green_hex(loss, min_loss, max_loss)
            graphviz_edges.append(
                f'"{id1}" -> "{id2}" [label=<<B><FONT COLOR="{font_color}">{loss:.2f}</FONT></B>> fontsize=9];'
            )
        else:
            graphviz_edges.append(f'"{id1}" -> "{id2}";')
    return "\n".join(graphviz_edges)

def generate_graphviz_legend():
    return """
        digraph Legend {
            rankdir=LR;
            margin=0;
            node [fontsize=10];

            legend_from [label="Konsept X"];
            legend_to [label="Konsept Y"];
            legend_from -> legend_to [label="Tap av unikhet ved abstraksjon" fontsize=10];
        }
    """

def transform_nodes_to_graphviz(concepts, selected_concepts=None):
    param_name_by_id = get_param_name_by_id(st.session_state.params)
    value_name_by_id = get_value_name_by_id(st.session_state.params)
    graphviz_nodes = []
    selected = set(selected_concepts or [])
    for concept_id, concept in concepts.items():
        intent_lines = sorted(concept["intent"])
        intent_text = ""
        for intent_line in intent_lines:
            param_id, value_id = intent_line.split(" = ")
            intent_text += f"{param_name_by_id[param_id]} = {value_name_by_id[value_id]}<BR/>"
        intent_text = intent_text if intent_lines else "Ingen egenskaper"
        label = f"<<B>{concept_id}</B><BR/>{intent_text}>".replace('"', '\\\\"')
        if concept_id in selected:
            graphviz_nodes.append(
                f'"{concept_id}" [label={label} style="filled" fillcolor="#7FC3FF"];'
            )
        else:
            graphviz_nodes.append(f'"{concept_id}" [label={label}];')
    return "\n".join(graphviz_nodes)