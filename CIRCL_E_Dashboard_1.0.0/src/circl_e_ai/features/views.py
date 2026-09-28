"""Exact named representation composition used by final fine/raw model selection."""
from .math import weighted_feature_concat


def compose_named_views(G_whole, G_foreground, L_whole, L_foreground) -> dict:
    G_dual = weighted_feature_concat(G_whole, G_foreground, .5, .5)
    L_dual = weighted_feature_concat(L_whole, L_foreground, .5, .5)
    return {
        "G_whole": G_whole,
        "G_foreground": G_foreground,
        "G_dual": G_dual,
        "L_whole": L_whole,
        "L_foreground": L_foreground,
        "L_dual": L_dual,
        "Gdual_Lf25": weighted_feature_concat(G_dual, L_foreground, .75, .25),
        "Gdual_Lf40": weighted_feature_concat(G_dual, L_foreground, .60, .40),
        "whole_G35_L65": weighted_feature_concat(G_whole, L_whole, .35, .65),
        "whole_G50_L50": weighted_feature_concat(G_whole, L_whole, .50, .50),
        "whole_G65_L35": weighted_feature_concat(G_whole, L_whole, .65, .35),
        "dual_G35_L65": weighted_feature_concat(G_dual, L_dual, .35, .65),
    }
