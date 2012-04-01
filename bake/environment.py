import os
import re
from pprint import pformat

from bake.util import recursive_merge
from scheme.formats import Format, StructuredText

__all__ = ('Environment', 'EnvironmentStack')

null = object()

class Environment(object):
    """A bake runtime environment."""

    def __init__(self, environment=None):
        self.environment = environment or {}

    def __repr__(self):
        return 'Environment(%r)' % self.environment

    def dump(self):
        return pformat(self.environment)

    def find(self, path, default=None):
        if '.' not in path:
            return self.environment.get(path, default)

        tokens, name = path.rsplit('.', 1)
        while True:
            value = self.get('%s.%s' % (tokens, name), null)
            if value is not null:
                return value
            if '.' in tokens:
                tokens = tokens.rsplit('.', 1)[0]
            else:
                return self.environment.get(name, default)

    def get(self, path, default=None):
        if '.' not in path:
            return self.environment.get(path, default)

        tokens = path.split('.')
        tail = tokens.pop()

        ref = self.environment
        for token in tokens:
            if token in ref:
                ref = ref[token]
                if not isinstance(ref, dict):
                    return default
            else:
                return default
        else:
            return ref.get(tail, default)

    def has(self, path):
        if '.' not in path:
            return (path in self.environment)

        tokens = path.split('.')
        tail = tokens.pop()

        ref = self.environment
        for token in tokens:
            if token in ref:
                ref = ref[token]
                if not isinstance(ref, dict):
                    return False
            else:
                return False
        else:
            return (tail in ref)

    def merge(self, source):
        recursive_merge(self.environment, source)
        return self

    def overlay(self, environment=None):
        if not isinstance(environment, Environment):
            environment = Environment(environment)
        return EnvironmentStack(environment, self)

    def parse(self, path):
        if not os.path.exists(path):
            raise RuntimeError('cannot find %r' % path)

        try:
            data = Format.read(path)
        except Exception:
            raise RuntimeError('cannot parse %r' % path)

        if data:
            self.merge(data)
        return self

    def parse_pair(self, pair):
        path, value = pair.split('=', 1)
        self.set(path, StructuredText.unserialize(value, True))
        return self

    def set(self, path, value):
        if '.' not in path:
            self.environment[path] = value
            return self

        tokens = path.split('.')
        tail = tokens.pop()

        ref = self.environment
        for token in tokens:
            if token not in ref:
                ref[token] = {}
            ref = ref[token]
            if not isinstance(ref, dict):
                raise ValueError(path)

        ref[tail] = value
        return self

    def underlay(self, environment=None):
        if not isinstance(environment, Environment):
            environment = Environment(environment)
        return EnvironmentStack(self, environment)

    def write(self, path, format=None, **params):
        Format.write(path, self.environment, format, **params)
        return self

class EnvironmentStack(object):
    def __init__(self, *environments):
        self.stack = environments

    def find(self, path, default=None):
        for environment in self.stack:
            value = environment.find(path, null)
            if value is not null:
                return value
        else:
            return default

    def get(self, path, default=None):
        for environment in self.stack:
            value = environment.get(path, null)
            if value is not null:
                return value
        else:
            return default

    def has(self, path):
        for environment in self.stack:
            if environment.has(path):
                return True
        else:
            return False

    def overlay(self, environment=None):
        if not isinstance(environment, Environment):
            environment = Environment(environment)

        stack = [environment] + self.stack[:]
        return EnvironmentStack(*stack)

    def set(self, path, value):
        self.stack[0].set(path, value)
        return self

    def underlay(self, environment=None):
        if not isinstance(environment, Environment):
            environment = Environment(environment)

        stack = self.stack[:] + [environment]
        return EnvironmentStack(*stack)
