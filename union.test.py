import unittest

from union import AtLeastINode, ListINode, EmptyINode, AndINode, OrINode, _ExplicitNegatedNode

_ExplicitNegatedNode.allnode = lambda x: ListINode([
	'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i'
])

class TestAtLeastINode(unittest.TestCase):
	# AtLeastINode should return an EmptyINode if it has no
	# children.
	def test_no_children(self):
		node = AtLeastINode(1)
		self.assertEqual(type(node), EmptyINode)

	# Empty children should always yield empty results.
	def test_empty_children(self):
		for k in [1, 2, 3]:
			child1 = ListINode([])
			child2 = ListINode([])
			child3 = ListINode([])
			node = AtLeastINode(k, child1, child2, child3)
			self.assertEqual(len(node.retrieve(10)), 0)

	# AtLeastINode should crash if initialized with invalid k
	def test_fails_on_invalid_k(self):
		child1 = ListINode([])
		child2 = ListINode([])
		with self.assertRaises(TypeError) as ctx:
			node = AtLeastINode('0', child1, child2)
		with self.assertRaises(ValueError) as ctx:
			node = AtLeastINode(0, child1, child2)
		with self.assertRaises(ValueError) as ctx:
			node = AtLeastINode(3, child1, child2)

	# Below are some tests to ensure AtLeastINode(1, ...)
	# behaves like an 'OR' gate (or a "Union").
	def test_or_gate1(self):
		child1 = ListINode(['a', 'b', 'c'])
		child2 = ListINode([])
		node = AtLeastINode(1, child1, child2)
		self.assertEqual(node.retrieve(10), ['a', 'b', 'c'])

	def test_or_gate2(self):
		child1 = ListINode(['a', 'b', 'c'])
		child2 = ListINode(['a', 'd'])
		node = AtLeastINode(1, child1, child2)
		self.assertEqual(
			node.retrieve(10), ['a', 'b', 'c', 'd'])

	def test_or_gate3(self):
		child1 = ListINode(['a'])
		child2 = ListINode(['b'])
		child3 = ListINode(['c'])
		node = AtLeastINode(1, child1, child2, child3)
		self.assertEqual(node.retrieve(10), ['a', 'b', 'c'])

	# Below are some tests to ensure AtLeastINode(n, ...)
	# behaves like an 'AND' gate (or a "Intersection").
	def test_and_gate1(self):
		child1 = ListINode(['a', 'b', 'c'])
		child2 = ListINode([])
		node = AtLeastINode(2, child1, child2)
		self.assertEqual(node.retrieve(10), [])

	def test_and_gate2(self):
		child1 = ListINode(['a', 'b', 'c', 'e'])
		child2 = ListINode(['a', 'd', 'e'])
		node = AtLeastINode(2, child1, child2)
		self.assertEqual(node.retrieve(10), ['a', 'e'])

	def test_and_gate3(self):
		child1 = ListINode(['a', 'b', 'c', 'e'])
		child2 = ListINode(['a', 'd', 'e'])
		child3 = ListINode(['a', 'b', 'e'])
		node = AtLeastINode(3, child1, child2, child3)
		self.assertEqual(node.retrieve(10), ['a', 'e'])

class TestAndINode(unittest.TestCase):
	def test_no_children(self):
		node = AndINode()
		self.assertEqual(len(node.retrieve(10)), 0)

	# Empty children should always yield empty results.
	def test_empty_children(self):
		child1 = ListINode([])
		child2 = ListINode([])
		child3 = ListINode([])
		node = AndINode(child1, child2, child3)
		self.assertEqual(len(node.retrieve(10)), 0)

	def test1(self):
		child1 = ListINode(['a', 'b', 'c'])
		child2 = ListINode([])
		node = AndINode(child1, child2)
		self.assertEqual(node.retrieve(10), [])

	def test2(self):
		child1 = ListINode(['a', 'b', 'c', 'e'])
		child2 = ListINode(['a', 'd', 'e'])
		node = AndINode(child1, child2)
		self.assertEqual(node.retrieve(10), ['a', 'e'])

	def test3(self):
		child1 = ListINode(['a', 'b', 'c', 'e'])
		child2 = ListINode(['a', 'd', 'e'])
		child3 = ListINode(['a', 'b', 'e'])
		node = AndINode(child1, child2, child3)
		self.assertEqual(node.retrieve(10), ['a', 'e'])

	def test4(self):
		child1 = ListINode(['a', 'b', 'c', 'd', 'e'])
		child2 = ListINode(['a', 'd'], negate=1)
		node = AndINode(child1, child2)
		r = node.retrieve(10)
		self.assertEqual(r, ['b', 'c', 'e'])

	def test5(self):
		child1 = ListINode(['a', 'b', 'c', 'd', 'e', 'f'])
		child2 = ListINode(['a', 'd'], negate=1)
		node = AndINode(child1, child2)
		r = node.retrieve(10)
		self.assertEqual(r, ['b', 'c', 'e', 'f'])

	def test6(self):
		child1 = ListINode(['a', 'b', 'c'])
		child2 = ListINode([], negate=1)
		node = AndINode(child1, child2)
		r = node.retrieve(10)
		self.assertEqual(r, ['a', 'b', 'c'])

class TestOrINode(unittest.TestCase):
	# AtLeastINode should return an EmptyINode if it has no
	# children.
	def test_no_children(self):
		node = OrINode()
		self.assertEqual(type(node), EmptyINode)

	# Empty children should always yield empty results.
	def test_empty_children(self):
		child1 = ListINode([])
		child2 = ListINode([])
		child3 = ListINode([])
		node = OrINode(child1, child2, child3)
		self.assertEqual(len(node.retrieve(10)), 0)

	# Below are some tests to ensure AtLeastINode(1, ...)
	# behaves like an 'OR' gate (or a "Union").
	def test1(self):
		child1 = ListINode(['a', 'b', 'c'])
		child2 = ListINode([])
		node = OrINode(child1, child2)
		self.assertEqual(node.retrieve(10), ['a', 'b', 'c'])

	def test2(self):
		child1 = ListINode(['a', 'b', 'c'])
		child2 = ListINode(['a', 'd'])
		node = OrINode(child1, child2)
		self.assertEqual(
			node.retrieve(10), ['a', 'b', 'c', 'd'])

	def test3(self):
		child1 = ListINode(['a'])
		child2 = ListINode(['b'])
		child3 = ListINode(['c'])
		node = OrINode(child1, child2, child3)
		self.assertEqual(node.retrieve(10), ['a', 'b', 'c'])

	def test4(self):
		child1 = ListINode(['a', 'b', 'c'])
		child2 = ListINode(['a', 'd', 'f', 'i'], negate=True)
		node = OrINode(child1, child2)
		self.assertEqual(
			node.retrieve(10), ['a', 'b', 'c', 'e', 'g', 'h'])

class TestExplicitNegatedNode(unittest.TestCase):
	def test1(self):
		node = _ExplicitNegatedNode(ListINode([
			'a', 'c', 'e', 'g', 'i'
		]))
		self.assertEqual(
			node.retrieve(10), ['b', 'd', 'f', 'h'])

if __name__ == '__main__':
	unittest.main()
