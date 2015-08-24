import jsonpickle


class ConfigurationService:

    def __init__(self, path):
        self._config_loaded = False
        self._path = path

    def _load_config_file(self, from_cache=True):
        if not self._config_loaded or not from_cache:
            self._config_file = ConfigurationFile.read(self._path)
            print "Read config file from {0}".format(self._path)
            print self._config_file
        self._config_loaded = True

    def get_setting(self, prop):
        self._load_config_file()
        setting = self._config_file.get(prop)

        if setting:
            return setting
        else:
            raise LookupError("Couldn't lookup setting {0} in {1}".
                              format(prop, self._path))


class ConfigurationFile:
    """Represents a json serialized configuration file with key-value pairs"""
    def __init__(self):
        pass

    @staticmethod
    def read(path):
        with open(path, 'r') as f:
            json = f.read()
            return jsonpickle.decode(json)

    @staticmethod
    def write(path, obj):
        jsonpickle.set_encoder_options(
            'simplejson', sort_keys=True, indent=4)
        with open(path, 'w') as f:
            json = jsonpickle.encode(obj, unpicklable=False)
            f.write(json)
