import copy, math

class IterableNode:
    def __init__(self):
        pass
    def __iter__(self):
        raise Exception('not yet implemented')
    def children(self):
        return []
    def is_leaf(self):
        return len(self.children()) == 0
    def name(self):
        raise Exception('not yet implemented')
    # Expected time it takes to emit one entry.
    def speed(self):
        raise Exception('not yet implemented')
    def height(self):
        if self.is_leaf():
            return 0
        return max([x.height() for x in self.children()]) + 1

class EmptyINode:
    def __init__(self):
        pass
    def __iter__(self):
        return
    def name(self):
        return '0'
    def speed(self):
        return 0

kLineLength = 16
class FileIterator:
    def __init__(self, path):
        self.path = path
    def __iter__(self):
        with open(self.path, 'r') as f:
            while True:
                line = f.read(kLineLength).strip()
                if len(line) == 0:
                    return
                yield line
    def name(self):
        return self.path
    def is_leaf(self):
        return True
    def speed(self):
        return 0.5

class Union(IterableNode):
    @staticmethod
    def create(*iterables):
        assert len(iterables) > 0
        if len(iterables) == 1:
            return iterables[0]
        iterables = list(set(iterables))
        childNames = [strip_parentheses(x.name()) for x in iterables]
        childNames = list(childNames)
        # Remove children that are unnecessary.
        # For example: "AB + A = A"
        obselete = set()
        for i, child1 in enumerate(childNames):
            for j in range(i + 1, len(childNames)):
                child2 = childNames[j]
                if child1 in child2:
                    obselete.add(j)
                elif child2 in child1:
                    obselete.add(i)
        iterables = [iterables[i] for i in range(len(iterables)) if i not in obselete]
        return Union(*iterables)

    def __init__(self, *iterables):
        # Dedup inputs
        names = set([x.name() for x in iterables])
        self.iterables = []
        for it in iterables:
            n = it.name()
            if n in names:
                names.remove(n)
                self.iterables.append(it)
    
    def __iter__(self):
        iters = [iter(x) for x in self.iterables]
        vals = [next(it) for it in iters]
        while True:
            while None in vals:
                i = vals.index(None)
                vals = vals[:i] + vals[i+1:]
                iters = iters[:i] + iters[i+1:]
            if len(vals) == 0:
                return
            r = min(vals)
            yield r
            for i, val in enumerate(vals):
                if val == r:
                    try:
                        vals[i] = next(iters[i])
                    except StopIteration:
                        vals[i] = None
    
    def children(self):
        return self.iterables

    # There is a small penalty based on the number of lists.
    # This can safely be ignored when there are less than 100
    # lists though, so we ignore it here.
    def speed(self):
        return 0.99 * sum((x.speed() for x in self.iterables)) / len(self.iterables)
    
    def name(self):
        A = [x.name() for x in self.children()]
        A.sort()
        return '(' + '+'.join(A) + ')'

class Intersection(IterableNode):
    @staticmethod
    def create(*iterables):
        assert len(iterables) > 0
        if len(iterables) == 1:
            return iterables[0]
        iterables = list(set(iterables))
        childNames = [strip_parentheses(x.name()) for x in iterables]
        childNames = list(childNames)
        # Remove children that are unnecessary.
        # For example: "AB + A = A"
        obselete = set()
        for i, child1 in enumerate(childNames):
            for j in range(i + 1, len(childNames)):
                child2 = childNames[j]
                if child2 in child1:
                    obselete.add(j)
                elif child1 in child2:
                    obselete.add(i)
        iterables = [iterables[i] for i in range(len(iterables)) if i not in obselete]
        return Intersection(*iterables)

    def __init__(self, *iterables):
        # Dedup inputs
        names = set([x.name() for x in iterables])
        self.iterables = []
        for it in iterables:
            n = it.name()
            if n in names:
                names.remove(n)
                self.iterables.append(it)
    
    def __iter__(self):
        iters = [iter(x) for x in self.iterables]
        vals = [next(it) for it in iters]
        while True:
            while None in vals:
                i = vals.index(None)
                vals = vals[:i] + vals[i+1:]
                iters = iters[:i] + iters[i+1:]
            if len(vals) == 0:
                return
            r = max(vals)
            for i, val in enumerate(vals):
                while val < r:
                    try:
                        val = next(iters[i])
                    except StopIteration:
                        return
                vals[i] = val
            if sum(v == r for v in vals) == len(vals):
                yield r
                for i, val in enumerate(vals):
                    try:
                        vals[i] = next(iters[i])
                    except StopIteration:
                        return

    def children(self):
        return self.iterables

    def speed(self):
        return 0.5 * prod([x.speed() for x in self.iterables])
    
    def name(self):
        A = [x.name() for x in self.children()]
        A.sort()
        return '(' + '*'.join(A) + ')'

def prod(A):
    r = 1
    for a in A:
        r *= a
    return r

class Wrapper(IterableNode):
    def __init__(self, name, arr):
        self._name = name
        self.arr = arr
    def __iter__(self):
        return iter(self.arr)
    def name(self):
        return self._name
    def speed(self):
        return 0.5

# Creates a binary tree with multiplication nodes at the
# bottom and addition nodes at the top.
def _foil(tree):
    if tree.is_leaf():
        return tree
    assert isinstance(tree, Union) or isinstance(tree, Intersection)
    children = tree.children()
    if isinstance(tree, Intersection):
        is_union = [isinstance(c, Union) for c in children]
        if True in is_union:
            i = is_union.index(True)
            A = children[:i] + children[i+1:]
            B = []
            for c in children[i].children():
                for a in A:
                    B.append(_foil(Intersection(c, a)))
            return Union.create(*B)
    return tree

def strip_parentheses(x):
    if x[0] == '(' and x[-1] == ')':
        return x[1:-1]
    else:
        return x

def foil(tree):

    oldname = None
    newname = tree.name()
    while newname != oldname:
        tree = _foil(tree)
        oldname = newname
        newname = tree.name()

    # Make tree flatter (i.e. less binary)
    def flatten(node):
        if node.is_leaf():
            return node
        children = node.children()
        if isinstance(node, Intersection):
            C = []
            for child in children:
                if isinstance(child, Intersection):
                    C += [flatten(x) for x in child.iterables]
                else:
                    C.append(flatten(child))
            return Intersection.create(*C)
        if isinstance(node, Union):
            C = []
            for child in children:
                if isinstance(child, Union):
                    C += [flatten(x) for x in child.iterables]
                else:
                    C.append(flatten(child))
            return Union.create(*C)
        assert False
    oldname = None
    newname = tree.name()
    while newname != oldname:
        tree = flatten(tree)
        oldname = newname
        newname = tree.name()
    
    # The tree should now have a depth of 3, with one union
    # node parenting multiple intersection nodes, and the
    # intersection nodes having leaves as children.  If this
    # is not true.  The only alternative is that the expression
    # is even simpler, containing at most one non-leaf node.
    assert tree.height() < 3, f"A foiled tree's height should be less than 3, but this one's is {tree.height()}"

    if tree.height() < 2:
        return tree
    
    assert isinstance(tree, Union)
    for child in tree.children():
        assert isinstance(child, Intersection) or child.is_leaf()


    return tree

# Cache is a map from a name to the tree that most efficiently
# represents that expression.  For instance
# cache["(a+b)*(c+d)"] = "(a+b)*(c+d)"
# cache["(a*c)+(a*d)+(b*c)+(b*d)"] = "(a+b)*(c+d)"
def simplify(tree, cache=None):
    if not isinstance(tree, Union):
        return tree
    if cache is None:
        cache = {}
    elif tree.name() in cache:
        return cache[tree.name()]

    children = tree.children()

    child2leaves = {}
    for child in children:
        if child.is_leaf():
            child2leaves[child] = child
        else:
            child2leaves[child] = child.children()
        
    leaf2children = {}
    for child in child2leaves:
        for leaf in child2leaves[child]:
            if leaf not in leaf2children:
                leaf2children[leaf] = []
            leaf2children[leaf].append(child)

    # Every leaf that occurs in at least 2 children is a
    # candidate for being factored out.  We try every
    # possible factoring and evaluate it.

    best = tree
    bestSpeed = tree.speed()

    for leaf in leaf2children:
        childrenWithLeaf = leaf2children[leaf]
        if len(childrenWithLeaf) == 1:
            continue
        A, B = [], []
        for c in children:
            if c in childrenWithLeaf:
                if isinstance(c, Intersection):
                    C = copy.copy(c.children())
                    del C[C.index(leaf)]
                    A.append(Intersection.create(*C))
            else:
                B.append(c)
        if len(A) == 0:
            continue
        B.append(
            Intersection.create(leaf, Union.create(*A))
        )
        candidate = Union.create(*B)
        candidate = simplify(candidate, cache)
        s = candidate.speed()
        if s > bestSpeed:
            best = candidate
            bestSpeed = s
    
    cache[tree.name()] = best

    return best

if __name__ == '__main__':
    import numpy as np
    A = np.random.randint(0, 100, 30)
    B = np.random.randint(0, 100, 30)
    C = np.random.randint(0, 100, 30)
    D = np.random.randint(0, 100, 30)

    A.sort()
    B.sort()
    C.sort()
    D.sort()

    A = Wrapper('A', A)
    B = Wrapper('B', B)
    C = Wrapper('C', C)
    D = Wrapper('D', D)

    # a (a + c) = aa + ac
    # tree = Intersection.create(Union(A, B), Union(A, C))

    # (a + b) (a + c) = aa + ac + ab + bc
    # tree = Intersection.create(Union(A, B), Union(A, C))

    # (a + b) (a + c) = aa + ac + ab + bc
    # tree = Intersection.create(Union(A, B), Union(A, C, D))

    # (BC) + (ABCD)
    # tree = Union.create(
    #     Intersection(B, C),
    #     Intersection(A, B, C, D)
    # )

    # a * b * (c + d)
    # tree = Intersection.create(Union(A, B), Union(A, C))

    tree = Intersection.create(Intersection(A, B), Union(C, D))

    print(tree.speed(), strip_parentheses(tree.name()))
    tree = foil(tree)
    print(tree.speed(), strip_parentheses(tree.name()))
    tree = simplify(tree)
    print(tree.speed(), strip_parentheses(tree.name()))

    # print(tree1.name())
    # print(tree2.name())
