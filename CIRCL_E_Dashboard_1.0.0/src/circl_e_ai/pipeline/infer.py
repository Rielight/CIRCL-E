"""Single canonical AI inference entrypoint."""
from circl_e_ai.contracts.models import InferenceResult
from circl_e_ai.features.bundle import build_feature_bundle
from circl_e_ai.discovery.run import run_discovery
from circl_e_ai.attributes.run import run_attributes
from circl_e_ai.ood.distance_gate import evaluate_reference_state
from circl_e_ai.semantics.resolver import resolve_semantics
from circl_e_ai.semantics.publication import publication_filter
from circl_e_ai.postmapping.context import build_context
from circl_e_ai.postmapping.run import run_postmapping
from circl_e_ai.postmapping.publication import publication_filter as postmapping_publication_filter
from circl_e_ai.provenance.trace import build_provenance
from circl_e_ai.validation.invariants import validate_inference_result


def infer_feature_bundle(features, release) -> InferenceResult:
    """Frozen inference starting from an already reconstructed FeatureBundle.

    This is useful for parity tests and keeps the pixel feature extractor
    independently testable. No fitting is permitted.
    """
    discovery = run_discovery(features, release)
    reference = evaluate_reference_state(
        features.named_views[release.assets.method_config["root_selection_space"]["selected_view"]],
        discovery.provisional_parent_id, release
    )
    attributes = run_attributes(features, discovery, release)
    semantics_internal = resolve_semantics(discovery, attributes, release)
    semantics_public = publication_filter(
        semantics_internal, reference.state, discovery.discovery_status, release
    )
    context = build_context(reference, discovery, attributes, semantics_internal, release)
    post = run_postmapping(context, release)
    provenance = build_provenance(
        release, features, reference, discovery, attributes, semantics_internal, post
    )
    published_post = postmapping_publication_filter(post, reference.state)
    result = InferenceResult(
        release_id=release.manifest.release_id,
        image_sha256=features.image_sha256,
        reference=reference,
        discovery=discovery,
        attributes=attributes,
        semantics=semantics_public,
        decision_support=published_post["decision_support"],
        routes=published_post["routes"],
        sensitivity=published_post["sensitivity"],
        provenance=provenance,
    )
    validate_inference_result(result)
    return result


def infer_image(image, release) -> InferenceResult:
    """Pixels -> frozen features -> complete AI profile. Never fits anything."""
    return infer_feature_bundle(build_feature_bundle(image, release), release)
