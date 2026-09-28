"""Original discovery operational status logic."""


def resolve_discovery_status(parent_id, parent_support, parent_reliability, fine_id, fine_support, residual_threshold=0.85):
    if parent_id is None or not parent_support.passed or parent_reliability < residual_threshold:
        return "unknown_mixed"
    if fine_id is None:
        return "reliable_parent_only"
    if fine_support is not None and fine_support.passed:
        return "reliable_parent_and_fine_group"
    return "reliable_parent_only"
