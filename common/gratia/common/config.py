
Config = None

class ConfigProxy:

    def __getattr__(self, attrname):
        return getattr(Config, attrname)

