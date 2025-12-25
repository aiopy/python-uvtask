from unittest.mock import patch

import pytest

from uvtask.hooks import (
    ArgvHookFlagParser,
    HookCommandExtractor,
    HookDiscoverer,
    HookNameGenerator,
    HookStyleValidator,
)


class TestHookNameGenerator:
    def test_composer_names(self) -> None:
        pre, post = HookNameGenerator.composer_names("test")
        assert pre == "pre-test"
        assert post == "post-test"

    def test_npm_names(self) -> None:
        pre, post = HookNameGenerator.npm_names("test")
        assert pre == "pretest"
        assert post == "posttest"


class TestHookCommandExtractor:
    def test_extract_string(self) -> None:
        commands = HookCommandExtractor.extract_commands("echo hello")
        assert commands == ["echo hello"]

    def test_extract_list(self) -> None:
        commands = HookCommandExtractor.extract_commands(["echo hello", "echo world"])
        assert commands == ["echo hello", "echo world"]


class TestHookStyleValidator:
    def test_validate_consistent_composer(self) -> None:
        validator = HookStyleValidator(HookNameGenerator())
        validator.validate_consistency("test", True, True, False, False)

    def test_validate_consistent_npm(self) -> None:
        validator = HookStyleValidator(HookNameGenerator())
        validator.validate_consistency("test", False, False, True, True)

    def test_validate_mixed_styles_raises(self) -> None:
        validator = HookStyleValidator(HookNameGenerator())
        with pytest.raises(SystemExit) as exc_info:
            validator.validate_consistency("test", True, False, False, True)
        assert exc_info.value.code == 1

    def test_validate_no_hooks(self) -> None:
        validator = HookStyleValidator(HookNameGenerator())
        validator.validate_consistency("test", False, False, False, False)


class TestHookDiscoverer:
    def test_discover_composer_pre_post(self) -> None:
        scripts = {"pre-test": "echo pre", "post-test": "echo post", "test": "echo test"}
        discoverer = HookDiscoverer(HookNameGenerator(), HookStyleValidator(HookNameGenerator()), HookCommandExtractor())
        pre_hooks, post_hooks = discoverer.discover("test", scripts)
        assert pre_hooks == ["echo pre"]
        assert post_hooks == ["echo post"]

    def test_discover_npm_pre_post(self) -> None:
        scripts = {"pretest": "echo pre", "posttest": "echo post", "test": "echo test"}
        discoverer = HookDiscoverer(HookNameGenerator(), HookStyleValidator(HookNameGenerator()), HookCommandExtractor())
        pre_hooks, post_hooks = discoverer.discover("test", scripts)
        assert pre_hooks == ["echo pre"]
        assert post_hooks == ["echo post"]

    def test_discover_only_pre(self) -> None:
        scripts = {"pre-test": "echo pre", "test": "echo test"}
        discoverer = HookDiscoverer(HookNameGenerator(), HookStyleValidator(HookNameGenerator()), HookCommandExtractor())
        pre_hooks, post_hooks = discoverer.discover("test", scripts)
        assert pre_hooks == ["echo pre"]
        assert post_hooks == []

    def test_discover_only_post(self) -> None:
        scripts = {"post-test": "echo post", "test": "echo test"}
        discoverer = HookDiscoverer(HookNameGenerator(), HookStyleValidator(HookNameGenerator()), HookCommandExtractor())
        pre_hooks, post_hooks = discoverer.discover("test", scripts)
        assert pre_hooks == []
        assert post_hooks == ["echo post"]

    def test_discover_list_hooks(self) -> None:
        scripts = {"pre-test": ["echo pre1", "echo pre2"], "test": "echo test"}
        discoverer = HookDiscoverer(HookNameGenerator(), HookStyleValidator(HookNameGenerator()), HookCommandExtractor())
        pre_hooks, post_hooks = discoverer.discover("test", scripts)
        assert pre_hooks == ["echo pre1", "echo pre2"]
        assert post_hooks == []

    def test_discover_mixed_styles_raises(self) -> None:
        scripts = {"pre-test": "echo pre", "posttest": "echo post", "test": "echo test"}
        discoverer = HookDiscoverer(HookNameGenerator(), HookStyleValidator(HookNameGenerator()), HookCommandExtractor())
        with pytest.raises(SystemExit):
            discoverer.discover("test", scripts)

    def test_discover_no_hooks(self) -> None:
        scripts = {"test": "echo test"}
        discoverer = HookDiscoverer(HookNameGenerator(), HookStyleValidator(HookNameGenerator()), HookCommandExtractor())
        pre_hooks, post_hooks = discoverer.discover("test", scripts)
        assert pre_hooks == []
        assert post_hooks == []


class TestArgvHookFlagParser:
    @patch("uvtask.hooks.argv", ["uvtask", "--no-hooks", "test"])
    def test_parse_no_hooks_flag(self) -> None:
        assert ArgvHookFlagParser.parse_no_hooks() is True

    @patch("uvtask.hooks.argv", ["uvtask", "--ignore-scripts", "test"])
    def test_parse_ignore_scripts_flag(self) -> None:
        assert ArgvHookFlagParser.parse_no_hooks() is True

    @patch("uvtask.hooks.argv", ["uvtask", "test"])
    def test_parse_no_flag(self) -> None:
        assert ArgvHookFlagParser.parse_no_hooks() is False
