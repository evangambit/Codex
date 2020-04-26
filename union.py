import copy, heapq, math

kFirstString = ''
kLastString = '~'

"""
Subclasses should create a (string) member variable named
"currentVal".

Nodes should not contain any valid values until after
"step()" has been called.  Before this nodes should return
kFirstString.

The user should *not* try to iterate *and* retrieve on the
same tree.
"""
class IterableNode:
  def __init__(self):
    self.currentVal = kFirstString
  def step(self):
    raise NotImplementedError('Subclasses must implement this method')
  def children(self):
    return []
  def is_leaf(self):
    return len(self.children()) == 0
  def name(self):
    raise NotImplementedError('Subclasses must implement this method')
  # Expected time it takes to emit one entry.
  def speed(self):
    raise NotImplementedError('Subclasses must implement this method')
  def retrieve(self, num_results):
    results = []
    self.step()
    while self.currentVal != kLastString:
      results.append(self.currentVal)
      if len(results) >= num_results:
        break
      self.step()
    return results
  def __lt__(a, b):
    return a.currentVal < b.currentVal
  def __iter__(self):
    self.step()
    while self.currentVal != kLastString:
      yield self.currentVal
      self.step()

class EmptyINode(IterableNode):
  def __init__(self):
    super().__init__()
  def step(self):
    self.currentVal = kLastString
  def name(self):
    return '0'
  def speed(self):
    return 0

kLineLength = 16
class FileINode(IterableNode):
  def __init__(self, path):
    super().__init__()
    self.path = path
    self.f = open(self.path, 'r')
  def step(self):
    self.currentVal = self.f.read(kLineLength)
    if len(self.currentVal) == 0:
      self.currentVal = kLastString
  def name(self):
    return self.path
  def speed(self):
    return 0.5

"""
A simple node that iterates over a list of strings. Used
for testing.
"""
class ListINode(IterableNode):
  def __init__(self, arr):
    super().__init__()
    self.arr = arr
    self.idx = -1
    self.id = 'list:' + str(ListINode.id)
    ListINode.id += 1
  def step(self):
    self.idx += 1
    if self.idx < len(self.arr):
      self.currentVal = self.arr[self.idx]
    else:
      self.currentVal = kLastString
      
  def name(self):
    return self.id
  def speed(self):
    return 0
ListINode.id = 0

"""
This is a generalization of the "And" and "Or" IterableNodes.

It is, however, marginally less efficient (and noticably
less readable) than the And/Or nodes, so we prefer using
And/Or nodes when possible.
"""
class AtLeastINode(IterableNode):
  # Automatically return an EmptyINode if there are no
  # children.
  def __new__(cls, k, *children):
    if len(children) == 0:
      return EmptyINode()
    return object.__new__(cls)

  def __init__(self, k, *children):
    super().__init__()
    if type(k) is not int:
      raise TypeError('k must be an integer')
    if k < 1:
      raise ValueError('k cannot be less than 1')
    if k > len(children):
      raise ValueError('k cannot exceed the number of children')
    self.k = k
    # Dedup 'children' and construct self._children
    self._children = []
    names = set()
    for child in children:
      n = child.name()
      if n not in names:
        names.add(n)
        self._children.append(child)

  def _min(self):
    A = [c.currentVal for c in self._children]
    low = min(A)
    return low, A.index(low)

  def step(self):
    # Increment the smallest self.k children.
    V = [x.currentVal for x in self._children]
    V.sort()
    threshold = V[self.k - 1]
    for child in self._children:
      if child.currentVal <= threshold:
        child.step()
    # Keep incrementing until the bottom k children match.
    low, idx = self._min()
    while sum([c.currentVal == low for c in self._children]) < self.k:
      self._children[idx].step()
      low, idx = self._min()
    if low == kFirstString:
      self.step()
    else:
      self.currentVal = low

  def children(self):
    return self._children

  # TODO: make this more accurate.
  def speed(self):
    raise NotImplementedError()
    return 0.1 * prod([x.speed() for x in self.iterables])
  
  def name(self):
    A = [x.name() for x in self.children()]
    A.sort()
    return '(' + '*'.join(A) + ')'

class AndINode(IterableNode):
  # Automatically return an EmptyINode if there are no
  # children.
  def __new__(cls, *children):
    if len(children) == 0:
      return EmptyINode()
    return object.__new__(cls)

  def __init__(self, *children):
    super().__init__()
    # Dedup 'children' and construct self._children
    self._children = []
    names = set()
    for child in children:
      n = child.name()
      if n not in names:
        names.add(n)
        self._children.append(child)

  def step(self):
    # The current children all point to self.currentVal,
    # which is the last value we just emitted.  So we
    # increment all children one.
    for child in self._children:
        child.step()
    # Now we keep incrementing children until they all equal
    # the largest child.
    high = max([c.currentVal for c in self._children])
    while True:
      for child in self._children:
        while child.currentVal < high:
          child.step()
      if sum([c.currentVal == high for c in self._children]) == len(self._children):
        self.currentVal = high
        return
      high = max([c.currentVal for c in self._children])

  def children(self):
    return self._children

  # TODO: make this more accurate.
  def speed(self):
    raise NotImplementedError()
    return 0.1 * prod([x.speed() for x in self.iterables])
  
  def name(self):
    A = [x.name() for x in self.children()]
    A.sort()
    return '(' + '*'.join(A) + ')'

class OrINode(IterableNode):
  # Automatically return an EmptyINode if there are no
  # children.
  def __new__(cls, *children):
    if len(children) == 0:
      return EmptyINode()
    return object.__new__(cls)

  def __init__(self, *children):
    super().__init__()
    # Dedup 'children' and construct self._children
    self._children = []
    names = set()
    for child in children:
      n = child.name()
      if n not in names:
        names.add(n)
        heapq.heappush(self._children, child)

  def step(self):
    newVal = self.currentVal
    while newVal == self.currentVal:
      child = heapq.heappop(self._children)
      child.step()
      heapq.heappush(self._children, child)
      newVal = self._children[0].currentVal
    self.currentVal = newVal

  def children(self):
    return self._children

  # TODO: make this more accurate.
  def speed(self):
    raise NotImplementedError()
    return 0.1 * prod([x.speed() for x in self.iterables])
  
  def name(self):
    A = [x.name() for x in self.children()]
    A.sort()
    return '(' + '*'.join(A) + ')'