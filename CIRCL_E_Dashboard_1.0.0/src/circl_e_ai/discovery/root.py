"""Frozen root KMeans inference."""


def predict_root(named_views: dict, release) -> int:
    cfg = release.assets.method_config["root_selection_space"]
    x = named_views[cfg["selected_view"]]
    raw = int(release.assets.root_model.predict(x)[0])
    return int(release.assets.root_remap[raw])
