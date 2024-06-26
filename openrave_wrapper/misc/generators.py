from collections import Iterator
from itertools import islice
from .numerical import INF

def safe_next(generator, i=None):
  if i is None:
    values = list(islice(generator, 1))
    if len(values) == 0: return None
    return values[0]
  return list(islice(generator, i))

def take(iterable, n=INF):
  if n == INF: n = None # NOTE - islice takes None instead of INF
  elif n == None: n = 0 # NOTE - for some of the uses
  return islice(iterable, n)

class GeneratorWrapper(Iterator):
  def __init__(self, generator):
    self.generator = generator
  def __next__(self):
    return next(self.generator)
  def __call__(self):
    return next(self)

class SafeGeneratorWrapper(GeneratorWrapper):
  def __init__(self, generator):
    self.generator = generator
    self.stop = False
    self.generations = 0
  def __iter__(self):
    while True:
      result = next(self)
      if result is False: break
      yield result
  def __next__(self):
    try:
      result = next(self.generator)
      assert result is not False
      self.generations += 1
      return result
    except StopIteration:
      self.stop = True
      return False

class Counter(Iterator):
  def __init__(self, initial=0):
    self.value = initial
  def __int__(self):
    return self.value
  def __next__(self):
    self.value += 1
    return int(self)
  def __repr__(self):
    return str(int(self))
