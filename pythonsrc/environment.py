from pathlib import Path
class Environment:
    CACHE_LOCATION = Path("cache/softfiles")
    @property
    def samples(self):
        return self.subseries.sample_array_dict('raw')
    @property
    def context(self):
        return {**self.samples, 'subseries': self.subseries}

environment = Environment()
