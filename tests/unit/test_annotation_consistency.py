from wheat_phenotyping.growth_annotation import calculate_annotation_consistency


def test_empty_annotation_library_is_explicitly_not_ready():
    result = calculate_annotation_consistency([])
    assert result["status"] == "insufficient_annotations"
    assert result["annotation_record_count"] == 0
    assert result["fleiss_kappa"] is None


def test_multi_annotator_conflicts_are_retained_in_consistency_summary():
    rows = [
        {"anonymous_id": "GV-1", "annotator_id": "A", "label": "较好"},
        {"anonymous_id": "GV-1", "annotator_id": "B", "label": "一般"},
        {"anonymous_id": "GV-2", "annotator_id": "A", "label": "较弱"},
        {"anonymous_id": "GV-2", "annotator_id": "B", "label": "较弱"},
    ]
    result = calculate_annotation_consistency(rows)
    assert result["status"] == "ready"
    assert result["annotation_record_count"] == 4
    assert result["annotator_count"] == 2
    assert result["conflict_image_count"] == 1
    assert result["cohen_kappa_pair_count"] == 2
