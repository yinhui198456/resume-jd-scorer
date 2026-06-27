from digest.cluster.group import cluster_items
from tests.unit.test_quality import item


def test_shared_topic_does_not_merge_unrelated_titles():
    first = item("https://example.com/1")
    second = item("https://example.com/2")
    first.normalized_title = "Codex release"
    second.normalized_title = "AI governance report"
    first.topic_tags = second.topic_tags = ["Agent"]

    assert len(cluster_items([first, second])) == 2


def test_equal_normalized_titles_cluster():
    first = item("https://example.com/1")
    second = item("https://example.com/2")
    first.normalized_title = " Codex   Release "
    second.normalized_title = "codex release"
    first.topic_tags = ["Codex"]
    second.topic_tags = ["Agent"]

    assert len(cluster_items([first, second])) == 1


def test_same_github_release_repository_versions_cluster():
    first = item("https://github.com/anthropics/claude-code/releases/tag/v2.1.191")
    second = item("https://github.com/anthropics/claude-code/releases/tag/v2.1.187")
    third = item("https://github.com/openai/codex/releases/tag/v0.142.2")
    first.normalized_title = "v2.1.191"
    second.normalized_title = "v2.1.187"
    third.normalized_title = "v0.142.2"

    clusters = cluster_items([first, second, third])

    assert sorted(len(cluster) for cluster in clusters) == [1, 2]
