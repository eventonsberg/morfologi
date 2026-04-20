import streamlit as st
from itertools import combinations
from typing import Dict, Set
from collections import defaultdict
from helpers import (
    get_param_name_by_id,
    get_value_name_by_id,
)

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

# ----- GRAPHVIZ -----

def transform_edges_to_graphviz(edges):
    graphviz_edges = []
    for id1, id2 in edges:
        graphviz_edges.append(f'"{id1}" -> "{id2}";')
    return "\n".join(graphviz_edges)

def transform_nodes_to_graphviz(concepts):
    graphviz_nodes = []
    for concept_id, concept in concepts.items():
        intent_lines = sorted(concept["intent"])
        intent_text = "<BR/>".join(intent_lines) if intent_lines else "Ingen egenskaper"
        label = f"<<B>{concept_id}</B><BR/>{intent_text}>".replace('"', '\\\\"')
        graphviz_nodes.append(f'"{concept_id}" [label={label}];')
    return "\n".join(graphviz_nodes)

# ----- MAIN FUNCTION -----

def classification():
    possible_combinations = st.session_state.possible_combinations
    param_name_by_id = get_param_name_by_id(st.session_state.params)
    value_name_by_id = get_value_name_by_id(st.session_state.params)

    configurations = {}
    for idx, combination in enumerate(possible_combinations):
        config = {f"{param_name_by_id[param_id]}": value_name_by_id[value_id]
                  for param_id, value_id in combination["combination_values"].items()}
        configurations[f"combination_{idx}"] = config
    concepts = compute_formal_concepts(configurations)
    edges = compute_edges(concepts)
    
    graphviz_nodes = transform_nodes_to_graphviz(concepts)
    graphviz_edges = transform_edges_to_graphviz(edges)
    st.graphviz_chart(f"""
        digraph G {{
            rankdir=LR;
            ranksep=1.5;
            node [fontsize=10];
            {graphviz_nodes}
            {graphviz_edges}
        }}
    """)

    # Calculate concepts, i.e. potential combination classes
    # Select most valuable concepts -> these are the combination classes
    # Assign combination classes to each combination
    # Display combination classes and their assigned combinations

