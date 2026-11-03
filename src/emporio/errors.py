class EmporioError(Exception):
    pass


class ConfigError(EmporioError):
    def __init__(self, setting: str, problem: str) -> None:
        super().__init__(f"{setting}: {problem}")
        self.setting = setting


class ProviderError(EmporioError):
    pass
