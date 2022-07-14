class _PluginManager:
    def __init__(self):
        self._registered_plugins = []
        self._cached_base_callbacks = {}
        self._built_functions = {}

    def register(self, *plugins):
        """
        Makes it possible to register your plugin.
        """
        self._registered_plugins.extend(plugins)
        self._build_functions()

    def decorate(self, name=None):
        def decorator(callback):
            @wraps(callback)
            def wrapper(*args, **kwargs):
                return built_functions[public_name](*args, **kwargs)

            public_name = name or callback.__name__