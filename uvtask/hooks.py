from __future__ import annotations

from sys import argv, exit, stderr

from uvtask.colors import color_service


class HookNameGenerator:
    @staticmethod
    def composer_names(command_name: str) -> tuple[str, str]:
        return f"pre-{command_name}", f"post-{command_name}"

    @staticmethod
    def npm_names(command_name: str) -> tuple[str, str]:
        return f"pre{command_name}", f"post{command_name}"


class HookStyleValidator:
    def __init__(self, name_generator: HookNameGenerator):
        self._name_generator = name_generator

    def validate_consistency(
        self,
        command_name: str,
        has_composer_pre: bool,
        has_composer_post: bool,
        has_npm_pre: bool,
        has_npm_post: bool,
    ) -> None:
        uses_composer_style = has_composer_pre or has_composer_post
        uses_npm_style = has_npm_pre or has_npm_post

        if uses_composer_style and uses_npm_style:
            composer_pre, composer_post = self._name_generator.composer_names(command_name)
            npm_pre, npm_post = self._name_generator.npm_names(command_name)

            error_text = color_service.bold_red("error")
            composer_pre_name = color_service.yellow(composer_pre)
            composer_post_name = color_service.yellow(composer_post)
            npm_pre_name = color_service.yellow(npm_pre)
            npm_post_name = color_service.yellow(npm_post)

            print(
                f"{error_text}: inconsistent hook naming style for command '{color_service.yellow(command_name)}'",
                file=stderr,
            )
            print(
                f"  Use either Composer-style ({composer_pre_name}, {composer_post_name}) or NPM-style ({npm_pre_name}, {npm_post_name}), but not both.",
                file=stderr,
            )
            exit(1)


class HookCommandExtractor:
    @staticmethod
    def extract_commands(hook_value: str | list[str]) -> list[str]:
        if isinstance(hook_value, list):
            return hook_value
        return [hook_value]


class HookDiscoverer:
    def __init__(
        self,
        name_generator: HookNameGenerator,
        validator: HookStyleValidator,
        extractor: HookCommandExtractor,
    ):
        self._name_generator = name_generator
        self._validator = validator
        self._extractor = extractor

    def discover(self, command_name: str, all_scripts: dict[str, str | list[str]]) -> tuple[list[str], list[str]]:
        composer_pre, composer_post = self._name_generator.composer_names(command_name)
        npm_pre, npm_post = self._name_generator.npm_names(command_name)

        has_composer_pre = composer_pre in all_scripts
        has_composer_post = composer_post in all_scripts
        has_npm_pre = npm_pre in all_scripts
        has_npm_post = npm_post in all_scripts

        self._validator.validate_consistency(command_name, has_composer_pre, has_composer_post, has_npm_pre, has_npm_post)

        pre_hooks = []
        post_hooks = []

        if has_composer_pre:
            pre_hooks.extend(self._extractor.extract_commands(all_scripts[composer_pre]))
        elif has_npm_pre:
            pre_hooks.extend(self._extractor.extract_commands(all_scripts[npm_pre]))

        if has_composer_post:
            post_hooks.extend(self._extractor.extract_commands(all_scripts[composer_post]))
        elif has_npm_post:
            post_hooks.extend(self._extractor.extract_commands(all_scripts[npm_post]))

        return pre_hooks, post_hooks


class ArgvHookFlagParser:
    @staticmethod
    def parse_no_hooks() -> bool:
        return "--no-hooks" in argv or "--ignore-scripts" in argv


name_generator = HookNameGenerator()
hook_discoverer = HookDiscoverer(
    name_generator,
    HookStyleValidator(name_generator),
    HookCommandExtractor(),
)
argv_hook_flag_parser = ArgvHookFlagParser()
