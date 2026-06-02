import streamlit as st
import pandas as pd
import altair as alt
from helpers import get_param_name_by_id, get_value_name_by_id
from itertools import combinations
from typing import Dict, Set
from collections import defaultdict
from helpers import (
    get_param_name_by_id,
    get_value_name_by_id,
)
import math


def is_auto_concept_name(name: str) -> bool:
    return str(name).lstrip().startswith("_")


def sync_concept_register(
    formal_concepts,
    concept_values,
):
    concept_register = st.session_state.concepts
    selected_concept_intents = st.session_state.selected_concept_intents
    current_intent_tuples = set(formal_concepts.keys())

    # Keep only still-valid concepts from previous runs.
    for stale_key in list(concept_register.keys()):
        if stale_key not in current_intent_tuples:
            del concept_register[stale_key]

    manually_named_intents = {
        intent_tuple
        for intent_tuple, concept_info in concept_register.items()
        if not is_auto_concept_name(concept_info.get("name", "_"))
    }

    intents_to_keep = (set(selected_concept_intents) | manually_named_intents) & current_intent_tuples

    updated_register = {}
    auto_class_index = 0
    for intent_tuple in sorted(intents_to_keep):
        existing_info = concept_register.get(intent_tuple, {})
        existing_name = existing_info.get("name", "")
        if existing_name and not is_auto_concept_name(existing_name):
            concept_name = existing_name
        else:
            auto_class_index += 1
            concept_name = f"_klasse_{auto_class_index}"
        updated_register[intent_tuple] = {
            "name": concept_name,
            "extent": formal_concepts[intent_tuple]["extent"],
            "value": concept_values.get(intent_tuple),
        }

    concept_register.clear()
    concept_register.update(updated_register)

def build_formal_context(configurations: Dict[str, Dict[str, str]]):
    objects = list(configurations.keys())
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

    return {
        tuple(sorted(concept["intent"])): {
            "extent": concept["extent"],
            "intent": concept["intent"],
        }
        for concept in concepts
    }

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

def get_param_from_attribute(attr: str) -> str:
    return attr.split("=", 1)[0].strip()

def weighted_abstraction_loss(child, parent, attr_freq, param_weights):

    dropped = child["intent"] - parent["intent"]
    loss = 0.0

    for a in dropped:
        freq = attr_freq[a]
        param = get_param_from_attribute(a)
        weight = param_weights.get(param, 1.0)  # default weight = 1.0
        loss += weight * (1.0 / freq)

    return loss

def compute_persistence(concepts, attr_freq):

    persistence = {}
    PARAMETER_WEIGHTS = st.session_state.classification_params

    for cid, c in concepts.items():
        best = math.inf
        for pid, p in concepts.items():
            if c is p:
                continue
            if c["extent"].issubset(p["extent"]) and c["extent"] != p["extent"]:
                loss = weighted_abstraction_loss(c, p, attr_freq, PARAMETER_WEIGHTS)
                best = min(best, loss)
        persistence[cid] = 0.0 if best is math.inf else best

    return persistence


def rescale_persistence_0_1(persistence, tol=1e-9, min_value=None, max_value=None):

    finite_vals = [p for p in persistence.values() if p is not None]

    if not finite_vals:
        return persistence.copy()

    p_min = min_value if min_value is not None else min(finite_vals)
    p_max = max_value if max_value is not None else max(finite_vals)

    # avoid division by zero if all values are equal
    if abs(p_max - p_min) < tol:
        return {
            cid: (1.0 if p is not None else None)
            for cid, p in persistence.items()
        }

    return {
        cid: (
            1.0 * (p - p_min) / (p_max - p_min)
            if p is not None else None
        )
        for cid, p in persistence.items()
    }


def overlap(c1, c2):
    e1, e2 = c1["extent"], c2["extent"]
    return len(e1 & e2) / min(len(e1), len(e2))


def generate_concept_score_df(concepts, persistence, concept_labels=None):

    param_name_by_id = get_param_name_by_id(st.session_state.params)
    value_name_by_id = get_value_name_by_id(st.session_state.params)
    listed_concepts = st.session_state.get("listed_concepts", {})

    data = []
    for cid, concept in concepts.items():
        intent_values = concept.get("intent")
        if intent_values is None:
            intent_values = set(cid) if isinstance(cid, tuple) else set()

        intent_descriptions = []
        for intent in sorted(intent_values):
            param_id, value_id = intent.split(" = ")
            param_name = param_name_by_id.get(param_id, f"Param {param_id}")
            value_name = value_name_by_id.get(value_id, f"Verdi {value_id}")
            intent_descriptions.append(f"{param_name} = {value_name}")

        concept_name = (concept_labels or {}).get(cid, concept.get("name", ""))
        concept_list = listed_concepts.get(cid)
        data.append({
            "Konsept": concept_name,
            "Kombinasjoner": len(concept["extent"]),
            "Konseptverdi": persistence.get(cid),
            "Egenskaper": intent_descriptions,
            "Liste": "🟥 RØD" if concept_list == "red"
                else "🟩 GRØNN" if concept_list == "green"
                else None,
            "_intent_tuple": cid,
        })
    return pd.DataFrame(data)


def build_selection_history_chart(score_history):
    if not score_history:
        return None

    param_name_by_id = get_param_name_by_id(st.session_state.params)
    value_name_by_id = get_value_name_by_id(st.session_state.params)
    concept_register = st.session_state.get("concepts", {})
    concept_score_df = st.session_state.get("concept_score_df")
    listed_concepts = st.session_state.get("listed_concepts", {})

    concept_name_by_intent = {}
    concept_metadata_by_intent = {}
    if concept_score_df is not None and not concept_score_df.empty:
        if "_intent_tuple" in concept_score_df.columns and "Konsept" in concept_score_df.columns:
            for _, row in concept_score_df.iterrows():
                intent_tuple = row.get("_intent_tuple")
                concept_name = row.get("Konsept")
                if isinstance(intent_tuple, tuple) and pd.notna(concept_name):
                    concept_name_by_intent[intent_tuple] = str(concept_name)
                if isinstance(intent_tuple, tuple):
                    concept_metadata_by_intent[intent_tuple] = {
                        "Kombinasjoner": row.get("Kombinasjoner"),
                        "Konseptverdi": row.get("Konseptverdi"),
                    }

    def concept_label_and_properties_from_intent(concept_intent_tuple):
        concept_name = concept_name_by_intent.get(concept_intent_tuple, "")
        if not concept_name:
            concept_info = concept_register.get(concept_intent_tuple, {})
            concept_name = concept_info.get("name", "")

        intent_descriptions = []
        for intent in concept_intent_tuple:
            if " = " not in intent:
                continue
            param_id, value_id = intent.split(" = ", 1)
            param_name = param_name_by_id.get(param_id, f"Param {param_id}")
            value_name = value_name_by_id.get(value_id, f"Verdi {value_id}")
            intent_descriptions.append(f"{param_name} = {value_name}")

        concept_label = concept_name if concept_name else "; ".join(intent_descriptions)
        if not concept_label:
            concept_label = "(Tomt konsept)"
        concept_properties = "; ".join(intent_descriptions) if intent_descriptions else "Ingen egenskaper"

        metadata = concept_metadata_by_intent.get(concept_intent_tuple, {})
        combinations_count = metadata.get("Kombinasjoner")
        concept_value = metadata.get("Konseptverdi")

        if pd.isna(combinations_count):
            concept_info = concept_register.get(concept_intent_tuple, {})
            concept_extent = concept_info.get("extent") or []
            combinations_count = len(concept_extent)

        if pd.isna(concept_value):
            concept_value = None

        return concept_label, concept_properties, combinations_count, concept_value

    chart_rows = []
    for history_row in score_history:
        k = history_row.get("Antall klasser")
        selection = history_row.get("Utvalg") or []
        if k is None:
            continue

        for concept_intent_tuple in selection:
            if not isinstance(concept_intent_tuple, tuple):
                continue
            concept_label, concept_properties, combinations_count, concept_value = concept_label_and_properties_from_intent(concept_intent_tuple)
            list_state = listed_concepts.get(concept_intent_tuple)
            if list_state == "green":
                bar_color_state = "green"
            elif list_state == "red":
                bar_color_state = "red"
            else:
                bar_color_state = "standard"

            chart_rows.append(
                {
                    "Antall klasser": int(k),
                    "Konsept": concept_label,
                    "Egenskaper": concept_properties,
                    "Kombinasjoner": combinations_count,
                    "Konseptverdi": concept_value,
                    "Fargestatus": bar_color_state,
                    "x_start": float(k) - 0.5,
                    "x_end": float(k) + 0.5,
                }
            )

    if not chart_rows:
        return None

    chart_df = pd.DataFrame(chart_rows)
    min_k = int(chart_df["Antall klasser"].min())
    max_k = int(chart_df["Antall klasser"].max())
    concept_order_by_presence = (
        chart_df.groupby("Konsept")["Antall klasser"]
        .nunique()
        .sort_values(ascending=False)
        .index
        .tolist()
    )

    concept_order = []
    if concept_score_df is not None and not concept_score_df.empty:
        if (
            "_intent_tuple" in concept_score_df.columns
            and "Konseptverdi" in concept_score_df.columns
        ):
            sorted_concept_score_df = concept_score_df.sort_values(
                by="Konseptverdi",
                ascending=False,
                na_position="last",
            )
            for _, row in sorted_concept_score_df.iterrows():
                intent_tuple = row.get("_intent_tuple")
                if not isinstance(intent_tuple, tuple):
                    continue
                concept_label, _, _, _ = concept_label_and_properties_from_intent(intent_tuple)
                if concept_label in chart_df["Konsept"].values and concept_label not in concept_order:
                    concept_order.append(concept_label)

    for concept_label in concept_order_by_presence:
        if concept_label not in concept_order:
            concept_order.append(concept_label)

    chart_height = max(260, 30 * len(concept_order))

    return alt.Chart(chart_df).mark_bar(size=12).encode(
        x=alt.X(
            "x_start:Q",
            title="Antall klasser",
            scale=alt.Scale(domainMin=float(min_k) - 0.5, domainMax=float(max_k) + 0.5, nice=False),
            axis=alt.Axis(tickMinStep=1),
        ),
        x2="x_end:Q",
        y=alt.Y(
            "Konsept:N",
            title="Valgte konsepter",
            sort=concept_order,
            axis=alt.Axis(
                labelOverlap=False,
                labelLimit=1000,
            ),
        ),
        color=alt.Color(
            "Fargestatus:N",
            scale=alt.Scale(
                domain=["green", "red", "standard"],
                range=["#2E7D32", "#C62828", "#1f77b4"],
            ),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("Antall klasser:Q", format=".0f"),
            alt.Tooltip("Konsept:N"),
            alt.Tooltip("Kombinasjoner:Q", format=".0f"),
            alt.Tooltip("Konseptverdi:Q", format=".2f"),
            alt.Tooltip("Egenskaper:N"),
        ],
    ).properties(
        title="Klasseutvalg som gir høyest total konseptverdi",
        height=chart_height,
    )


# ----- GRAPHVIZ -----

def score_to_red_green_hex(score, min_score, max_score, tol=1e-9):
    if score is None:
        return "#444444"

    if abs(max_score - min_score) < tol:
        t = 0.5
    else:
        t = (float(score) - float(min_score)) / (float(max_score) - float(min_score))

    t = max(0.0, min(1.0, t))
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

def transform_nodes_to_graphviz(
    concepts,
    selected_concepts=None,
    concept_scores=None,
    concept_labels=None,
    listed_concepts=None,
):
    param_name_by_id = get_param_name_by_id(st.session_state.params)
    value_name_by_id = get_value_name_by_id(st.session_state.params)
    graphviz_nodes = []
    selected = set(selected_concepts or [])
    listed = listed_concepts or {}
    for concept_id, concept in concepts.items():
        concept_title = (concept_labels or {}).get(concept_id, str(concept_id))
        n_combinations = len(concept["extent"])
        combinations_text = f"Kombinasjoner: {n_combinations}<BR/>"
        score = (concept_scores or {}).get(concept_id)
        score_text = f"Konseptverdi: {score:.2f}<BR/>" if score is not None else ""
        intent_lines = sorted(concept["intent"])
        intent_text = ""
        for intent_line in intent_lines:
            param_id, value_id = intent_line.split(" = ")
            intent_text += f"{param_name_by_id[param_id]} = {value_name_by_id[value_id]}<BR/>"
        intent_text = intent_text if intent_lines else "Ingen egenskaper"
        label = f"<<B>{concept_title}</B><BR/>{combinations_text}{score_text}{intent_text}>".replace('"', '\\\\"')
        if listed.get(concept_id) == "red":
            graphviz_nodes.append(
                f'"{concept_id}" [label={label} style="filled" fillcolor="#FFB3B3"];'
            )
        elif listed.get(concept_id) == "green":
            graphviz_nodes.append(
                f'"{concept_id}" [label={label} style="filled" fillcolor="#B9F6CA"];'
            )
        elif concept_id in selected:
            graphviz_nodes.append(
                f'"{concept_id}" [label={label} style="filled" fillcolor="#7FC3FF"];'
            )
        else:
            graphviz_nodes.append(f'"{concept_id}" [label={label}];')
    return "\n".join(graphviz_nodes)


def transform_ranks_to_graphviz(concepts):
    concepts_by_specified_count = defaultdict(list)
    for concept_id, concept in concepts.items():
        specified_count = len(concept.get("intent", []))
        concepts_by_specified_count[specified_count].append(concept_id)

    rank_blocks = []
    for specified_count in sorted(concepts_by_specified_count.keys(), reverse=True):
        node_ids = " ".join(f'"{concept_id}";' for concept_id in concepts_by_specified_count[specified_count])
        rank_blocks.append(f"{{ rank=same; {node_ids} }}")

    return "\n".join(rank_blocks)

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