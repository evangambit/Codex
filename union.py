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
    self.negate = False
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
  def __init__(self, arr, negate=False):
    super().__init__()
    self.arr = arr
    self.idx = -1
    self.id = 'list:' + str(ListINode.id)
    self.negate = negate
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
        if child.negate:
          self._children.append(_ExplicitNegatedNode(child))
        else:
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

  # TODO: what parameter should I use instead of 0.1?
  def speed(self):
    a = math.pow(0.1, len(self.k))
    b = sum([x.speed() for x in self._children])
    return a * b / len(self._children)
  
  def name(self):
    A = [x.name() for x in self.children()]
    A.sort()
    return '(' + '*'.join(A) + ')'

"""
The normal way to implement negation is to iterate over
allposts.json and remove a node's lines from it.

However, a negated node can be implemented more efficiently
if it is the AndINode's child.  Since this is by far the
most common use of negation, it's worth making our code
terrible if it allows us to support it.

As part of this, '_ExplicitNegatedNode' is a protected
class that should only be used by OrINode and AtLeastINode
"""
class _ExplicitNegatedNode(IterableNode):
  def __init__(self, child):
    super().__init__()
    self.all = _ExplicitNegatedNode.allnode(None)
    self.child = child
  def step(self):
    self.all.step()
    while True:
      if self.all.currentVal == kLastString:
        self.currentVal = kLastString
        break
      if self.child.currentVal == self.all.currentVal:
        self.all.step()
        self.child.step()
      elif self.child.currentVal < self.all.currentVal:
        self.child.step()
      else:
        self.currentVal = self.all.currentVal
        break
  def children(self):
    return [self.child, self.all]
  def speed(self):
    return self.child.speed()
  def name(self):
    return '-' + self.child.name()
_ExplicitNegatedNode.allnode = lambda x: FileINode('index/score/allposts.json')

class AndINode(IterableNode):
  # Automatically return an EmptyINode if there are no
  # children.
  def __new__(cls, *children):
    if len(children) == 0:
      return EmptyINode()
    if len(children) == 1:
      if not children[0].negate:
        return children[0]
      else:
        return ExplicitNegatedNode(children[0])
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
    self._hasnegation = sum([c.negate for c in self._children])

  def step(self):
    if sum([c.currentVal == kLastString for c in self._children if not c.negate]):
      self.currentVal = kLastString
      return
    # The current children all point to self.currentVal,
    # which is the last value we just emitted.  So we
    # increment all children one.
    for child in self._children:
      if not child.negate:
        child.step()

    # Now we keep incrementing children until they all equal
    # the largest child.
    high = max([c.currentVal for c in self._children if not c.negate])
    while True:
      for child in self._children:
        while child.currentVal < high:
          child.step()
      high = max([c.currentVal for c in self._children if not c.negate])
      if sum([(c.currentVal == high) != (c.negate) for c in self._children]) == len(self._children):
        self.currentVal = high
        return
      if sum([c.currentVal >= high for c in self._children]) == len(self._children):
        for child in self._children:
          child.step()
      high = max([c.currentVal for c in self._children if not c.negate])
      if high == kLastString:
        self.currentVal = kLastString
        return


  def children(self):
    return self._children

  # TODO: what parameter should I use instead of 0.1?
  def speed(self):
    a = math.pow(0.1, len(self._children))
    b = sum([x.speed() for x in self._children])
    return a * b / len(self._children)
  
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
        if child.negate:
          heapq.heappush(self._children, _ExplicitNegatedNode(child))
        else:
          heapq.heappush(self._children, child)
    self._hasnegation = sum([c.negate for c in self._children])

  def step(self):
    if not self._hasnegation:
      newVal = self.currentVal
      while newVal == self.currentVal:
        child = heapq.heappop(self._children)
        child.step()
        heapq.heappush(self._children, child)
        newVal = self._children[0].currentVal
      self.currentVal = newVal
    else:
      raise NotImplementedError('TODO')

  def children(self):
    return self._children

  # TODO: make this more accurate.
  def speed(self):
    S = [x.speed() for x in self._children]
    return sum(S) / len(self._children)
  
  def name(self):
    A = [x.name() for x in self.children()]
    A.sort()
    return '(' + '*'.join(A) + ')'