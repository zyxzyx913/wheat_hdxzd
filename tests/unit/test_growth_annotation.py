"""多标注者一致性统计测试，不生成或推断最终标签。"""
from wheat_phenotyping.growth_annotation import calculate_annotation_consistency


def record(image, annotator, label):
    return {"anonymous_id": image, "annotator_id": annotator, "label": label}


def test_waits_until_an_image_has_multiple_annotators():
    result = calculate_annotation_consistency([record("a", "one", "较好")])
    assert result["status"] == "waiting_for_multiple_annotators"
    assert result["fleiss_kappa"] is None


def test_two_annotators_perfect_agreement_has_kappa_one():
    rows = [record("a", "one", "较好"), record("a", "two", "较好"), record("b", "one", "一般"), record("b", "two", "一般")]
    result = calculate_annotation_consistency(rows)
    assert result["status"] == "ready"
    assert result["conflict_image_count"] == 0
    assert result["cohen_kappa"] == 1.0
    assert result["fleiss_kappa"] == 1.0


def test_conflicts_are_retained_and_reported():
    rows = [record("a", "one", "较好"), record("a", "two", "较弱"), record("b", "one", "一般"), record("b", "two", "较弱")]
    result = calculate_annotation_consistency(rows)
    assert result["conflict_image_count"] == 2
    assert result["cohen_kappa"] < 1.0
