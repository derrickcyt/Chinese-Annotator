from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import object
import io
import simplejson
import os
import six

# Describes where to search for the config file if no location is specified

DEFAULT_CONFIG_LOCATION = "config.json"

# TODO this default config should consider more later
DEFAULT_CONFIG = {
    "project": None,
    "fixed_model_name": None,
    "config": DEFAULT_CONFIG_LOCATION,
    "data": None,
    "emulate": None,
    "language": "zh",
    "log_file": None,
    "log_level": 'INFO',
    # "word2vec_file": os.path.join("data", "word2vec_feature_extractor.dat"),
    "num_threads": 1,
    "max_training_processes": 1,
    "path": "projects",
    "port": 5000,
    "embedding_path": "tests/data/vec.txt",
    "embedding_type": "text",
    "pipeline": [],
    # "response_log": "logs",
    # "aws_endpoint_url": None,
    # "duckling_dimensions": None,
    # "duckling_http_url": None,
    "classifier_sklearn": {
        "C": [1, 2, 5, 10, 20, 100],
        "kernel": "linear"
    }
}


class InvalidConfigError(ValueError):
    """Raised if an invalid configuration is encountered."""

    def __init__(self, message):
        # type: (Text) -> None
        super(InvalidConfigError, self).__init__(message)


class AnnotatorConfig(object):
    DEFAULT_PROJECT_NAME = "default"

    def __init__(self, filename=None, env_vars=None, cmdline_args=None):

        if filename is None and os.path.isfile(DEFAULT_CONFIG_LOCATION):
            filename = DEFAULT_CONFIG_LOCATION

        self.override(DEFAULT_CONFIG)
        if filename is not None:
            try:
                with io.open(filename, encoding='utf-8') as f:
                    file_config = simplejson.loads(f.read())
            except ValueError as e:
                raise InvalidConfigError("Failed to read configuration file '{}'. Error: {}".format(filename, e))
            self.override(file_config)

        if env_vars is not None:
            env_config = self.create_env_config(env_vars)
            self.override(env_config)

        if cmdline_args is not None:
            cmdline_config = self.create_cmdline_config(cmdline_args)
            self.override(cmdline_config)

        if isinstance(self.__dict__['pipeline'], six.string_types):
            from chi_annotator.algo_factory import registry
            if self.__dict__['pipeline'] in registry.registered_pipeline_templates:
                self.__dict__['pipeline'] = registry.registered_pipeline_templates[self.__dict__['pipeline']]
            else:
                raise InvalidConfigError("No pipeline specified and unknown pipeline template " +
                                         "'{}' passed. Known pipeline templates: {}".format(
                                                 self.__dict__['pipeline'],
                                                 ", ".join(registry.registered_pipeline_templates.keys())))

        for key, value in self.items():
            setattr(self, key, value)

    def __getitem__(self, key):
        return self.__dict__[key]

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __delitem__(self, key):
        del self.__dict__[key]

    def __contains__(self, key):
        return key in self.__dict__

    def __len__(self):
        return len(self.__dict__)

    def __getstate__(self):
        return self.as_dict()

    def __setstate__(self, state):
        self.override(state)

    def items(self):
        return list(self.__dict__.items())

    def as_dict(self):
        return dict(list(self.items()))

    def view(self):
        return simplejson.dumps(self.__dict__, indent=4)

    def split_arg(self, config, arg_name):
        if arg_name in config and isinstance(config[arg_name], six.string_types):
            config[arg_name] = config[arg_name].split(",")
        return config

    def split_pipeline(self, config):
        if "pipeline" in config and isinstance(config["pipeline"], six.string_types):
            config = self.split_arg(config, "pipeline")
            if "pipeline" in config and len(config["pipeline"]) == 1:
                config["pipeline"] = config["pipeline"][0]
        return config

    def create_cmdline_config(self, cmdline_args):
        cmdline_config = {k: v
                          for k, v in list(cmdline_args.items())
                          if v is not None}
        cmdline_config = self.split_pipeline(cmdline_config)
        cmdline_config = self.split_arg(cmdline_config, "duckling_dimensions")
        return cmdline_config

    def create_env_config(self, env_vars):
        keys = [key for key in env_vars.keys() if "RASA_" in key]
        env_config = {key.split('RASA_')[1].lower(): env_vars[key] for key in keys}
        env_config = self.split_pipeline(env_config)
        env_config = self.split_arg(env_config, "duckling_dimensions")
        return env_config

    def make_paths_absolute(self, config, keys):
        abs_path_config = dict(config)
        for key in keys:
            if key in abs_path_config and abs_path_config[key] is not None and not os.path.isabs(abs_path_config[key]):
                abs_path_config[key] = os.path.join(os.getcwd(), abs_path_config[key])
        return abs_path_config

    # noinspection PyCompatibility # TODO may remove in py3
    def make_unicode(self, config):
        if six.PY2:
            # Sometimes (depending on the source of the config value) an argument will be str instead of unicode
            # to unify that and ease further usage of the config, we convert everything to unicode
            for k, v in config.items():
                if type(v) is bytes:
                    config[k] = str(v).encode("utf-8")
        return config

    def override(self, config):
        abs_path_config = self.make_unicode(self.make_paths_absolute(config, ["path", "response_log"]))
        self.__dict__.update(abs_path_config)
