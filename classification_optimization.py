from itertools import combinations
import altair as alt
from ortools.sat.python import cp_model
import math
import pandas as pd
from classification_calculation import overlap


def build_score_history_chart(score_history):
    if not score_history:
        return None

    chart_df = pd.DataFrame(score_history)
    chart_data = chart_df.melt(
        id_vars="Antall klasser",
        value_vars=["Gjennomsnittsscore", "Totalscore"],
        var_name="Type",
        value_name="Score",
    )
    return alt.Chart(chart_data).mark_line(point=True).encode(
        x=alt.X(
            "Antall klasser:Q",
            scale=alt.Scale(domainMin=2, nice=False),
            axis=alt.Axis(tickMinStep=1),
        ),
        y=alt.Y("Score:Q"),
        color=alt.Color("Type:N", legend=alt.Legend(orient="bottom")),
        tooltip=["Antall klasser:Q", "Type:N", alt.Tooltip("Score:Q", format=".4f")],
    ).properties(title="Gjennomsnittlig og total konseptverdi for optimalt klasseutvalg")

def compute_conflicts(concepts, epsilon):
    conflicts = []
    keys = list(concepts.keys())
    for i, j in combinations(keys, 2):
        if overlap(concepts[i], concepts[j]) > epsilon:
            conflicts.append((i, j))
    return conflicts


def solve_for_k(
   concepts,
   scores,
   conflicts,
   coverage_map,
   max_k,
   listed_concepts=None,
):
   model = cp_model.CpModel()

   x = {c: model.new_bool_var(f"x_{c}") for c in concepts}

   listed_concepts = listed_concepts or {}

   for c, list_state in listed_concepts.items():
       if c not in x:
           continue
       if list_state == "red":
           model.add(x[c] == 0)
       elif list_state == "green":
           model.add(x[c] == 1)

   for i, j in conflicts:
       model.add(x[i] + x[j] <= 1)

   for cfg, covering in coverage_map.items():
       model.add(sum(x[c] for c in covering) >= 1)

   model.add(sum(x[c] for c in concepts) <= max_k)

   model.maximize(sum(scores[c] * x[c] for c in concepts))

   solver = cp_model.CpSolver()
   solver.parameters.max_time_in_seconds = 5.0
   status = solver.Solve(model)

   if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
       return None, None

   selected = [c for c in concepts if solver.Value(x[c]) == 1]
   total_score = sum(scores[c] for c in selected)

   return selected, total_score



def compute_optimal_selection(
    concepts,
    scores,
    optimization_strategy,
    max_classes,
    epsilon=0,
    listed_concepts=None,
    score_plot_placeholder=None,
    score_history_output=None,
    ):
    conflicts = compute_conflicts(concepts, epsilon)

    all_configs = set().union(*[c["extent"] for c in concepts.values()])
    coverage_map = {
        cfg: [cid for cid, c in concepts.items() if cfg in c["extent"]]
        for cfg in all_configs
    }

    best_solution = None
    best_score = -math.inf
    score_history = []

    n = len(concepts)

    for k in range(2, max_classes + 1):
        selected, total_score = solve_for_k(
            concepts,
            scores,
            conflicts,
            coverage_map,
            k,
            listed_concepts=listed_concepts,
        )

        if selected is None or total_score is None or len(selected) == 0:
            if score_plot_placeholder is not None:
                score_history.append(
                    {
                        "Antall klasser": k,
                        "Gjennomsnittsscore": None,
                        "Totalscore": None,
                        "Utvalg": None,
                    }
                )
                chart = build_score_history_chart(score_history)
                if chart is not None:
                    score_plot_placeholder.altair_chart(chart)
            continue

        avg_score = total_score / len(selected)
        if optimization_strategy == "Høyest totalscore":
            improved = total_score > best_score
        else:
            improved = avg_score > best_score
        if improved:
            if optimization_strategy == "Høyest totalscore":
                best_score = total_score
            else:
                best_score = avg_score
            best_solution = {
                "k": len(selected),
                "total_score": total_score,
                "average_score": avg_score,
                "selection": selected,
            }

        if score_plot_placeholder is not None:
            score_history.append(
                {
                    "Antall klasser": k,
                    "Gjennomsnittsscore": avg_score,
                    "Totalscore": total_score,
                    "Utvalg": selected,
                }
            )
            chart = build_score_history_chart(score_history)
            if chart is not None:
                score_plot_placeholder.altair_chart(chart)

    if score_history_output is not None:
        score_history_output.clear()
        score_history_output.extend(score_history)

    return best_solution