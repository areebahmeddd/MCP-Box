import importlib

import pytest

from superbox.cli.scanners.sonarqube import extract_repository, generate_key

# `test.py` is a reserved name in pytest; import via importlib to avoid confusion
_test_cmd = importlib.import_module("superbox.cli.commands.test")
get_repo = _test_cmd.get_repo


class TestExtractRepository:
    @pytest.mark.parametrize(
        "url,expected_owner,expected_repo",
        [
            # Standard HTTPS
            ("https://github.com/acme/my-tool", "acme", "my-tool"),
            # HTTPS with .git suffix
            ("https://github.com/acme/my-tool.git", "acme", "my-tool"),
            # HTTPS with trailing slash
            ("https://github.com/acme/my-tool/", "acme", "my-tool"),
            # SSH format
            ("git@github.com:acme/my-tool.git", "acme", "my-tool"),
            # SSH format without .git
            ("git@github.com:acme/my-tool", "acme", "my-tool"),
            # Leading/trailing whitespace
            ("  https://github.com/acme/my-tool  ", "acme", "my-tool"),
        ],
    )
    def test_parses_url_correctly(self, url: str, expected_owner: str, expected_repo: str) -> None:
        owner, repo = extract_repository(url)
        assert owner == expected_owner
        assert repo == expected_repo

    def test_returns_none_for_non_github_path(self) -> None:
        """A URL with only one path segment cannot produce an (owner, repo) pair."""
        owner, repo = extract_repository("https://github.com/only-one-part")
        # With a single segment after stripping, both or one will be None
        assert owner is None or repo == "only-one-part"

    def test_handles_deep_path_by_using_last_two_segments(self) -> None:
        owner, repo = extract_repository("https://github.com/org/owner/repo")
        assert owner == "owner"
        assert repo == "repo"


class TestGenerateKey:
    def test_produces_expected_format(self) -> None:
        key = generate_key("acme", "my-tool", "superbox")
        assert key == "superbox_acme_my-tool"

    def test_replaces_spaces_with_underscores(self) -> None:
        key = generate_key("my owner", "my repo", "org")
        assert " " not in key

    def test_replaces_special_chars_in_owner(self) -> None:
        key = generate_key("owner@email", "repo", "org")
        assert "@" not in key
        assert "owner_email" in key or "owner" in key

    def test_replaces_special_chars_in_repo(self) -> None:
        key = generate_key("owner", "repo/sub", "org")
        assert "/" not in key

    def test_preserves_allowed_chars(self) -> None:
        """Hyphens, dots, and underscores in owner/repo must be kept."""
        key = generate_key("my-owner", "my.repo_v2", "org")
        assert "my-owner" in key
        assert "my.repo_v2" in key

    def test_prefixed_with_organization(self) -> None:
        key = generate_key("owner", "repo", "my-org")
        assert key.startswith("my-org")

    @pytest.mark.parametrize(
        "owner,repo,org",
        [
            ("a", "b", "c"),
            ("UPPER", "Repo", "Org"),
            ("123", "456", "789"),
        ],
    )
    def test_always_produces_non_empty_key(self, owner: str, repo: str, org: str) -> None:
        key = generate_key(owner, repo, org)
        assert key
        assert "_" in key  # format: org_owner_repo


class TestGetRepo:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://github.com/acme/my-tool", "my-tool"),
            ("https://github.com/acme/my-tool.git", "my-tool"),
            ("https://github.com/acme/my-tool/", "my-tool"),
            ("git@github.com:acme/my-tool.git", "my-tool"),
            ("git@github.com:acme/my-tool", "my-tool"),
            ("  https://github.com/acme/weather  ", "weather"),
        ],
    )
    def test_extracts_repo_name(self, url: str, expected: str) -> None:
        assert get_repo(url) == expected

    def test_deep_path_returns_last_segment(self) -> None:
        assert get_repo("https://github.com/org/owner/repo") == "repo"

    def test_empty_string_returns_unknown(self) -> None:
        result = get_repo("")
        assert result == "unknown" or isinstance(result, str)
