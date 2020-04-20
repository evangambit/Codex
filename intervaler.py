import copy

"""
[-inf, -5] [-6, -4] [-3] [-2] [...] [30] [31,32] [33,34] [35,36] [37,38] [39,42] [43,47] [48,56] [56,inf]
[-inf, -2] [-1] [0] [...] [16] [17] [18,19] [20,21] [22,23] [24,26] [27,30] [31,38] [39, inf]
[-inf, -1] [0] [1] [...] [5] [6] [7,8] [9,10] [11,12] [13,16] [17,23] [24, inf]
[-inf, 1] [2, 5] [6, 11] [11, inf]
"""
class Intervaler:
	def __init__(self, intervals):
		self.intervals = copy.copy(intervals)
		self.intervals.sort()
		self.lowclip = self.intervals[0][0]
		self.highclip = max(i[1] for i in self.intervals)

	def time2intervals(self, t):
		return [i for i in self.intervals if i[0] <= t and i[1] >= t]

	def interval2intervals(self, a, b):
		a = max(self.lowclip, a)
		b = min(self.highclip, b)

		candidates = [i for i in self.intervals if (i[0] >= a) and (i[1] <= b)]
		if len(candidates) == 0:
			# No candidates are contained by [a, b], so we find the
			# smallest interval that completely contains [a, b]
			candidates = [i for i in self.intervals if (i[0] <= a) and (i[1] >= b)]
			sizes = [i[1] - i[0] + 1 for i in candidates]
			return [candidates[sizes.index(min(sizes))]]
		sizes = [i[1] - i[0] + 1 for i in candidates]
		i = candidates[sizes.index(max(sizes))]
		r = [i]
		if i[1] < b:
			r += self.interval2intervals(i[1] + 1, b)
		if i[0] > a:
			r += self.interval2intervals(a, i[0] - 1)
		r.sort()
		return r

	@staticmethod
	def load(file):
		with open(file, 'r') as f:
			lines = f.readlines()
		lines = [l.strip() for l in lines if len(l.strip()) > 0]

		intervals = []
		for line in lines:
			assert line[0] == '['
			assert line[-1] == ']'
			cells = line[1:-1].split('] [')
			for i, cell in enumerate(cells):
				cell = cell.strip()
				if cell == '...':
					continue
				if ',' in cell:
					a, b = cell.split(',')
					a = int(a.strip())
					b = int(b.strip())
					intervals.append((a, b))
				else:
					a = int(cell.strip())
					intervals.append((a, a))
					if cells[i - 1].strip() == '...':
						for s in range(intervals[-2][0] + 1, intervals[-1][0]):
							intervals.append((s, s))
		return Intervaler(list(set(intervals)))


i = Intervaler.load('score_intervals.txt')

# Problem: divide-and-conquer doesn't let the algorithm overlap
# e.g. [-6, 99] doesn't find [6, 11]
i.interval2intervals(-6, 99)
# [(-6, -4), (-3, -3), (-2, -2), (-1, -1), (0, 0), (1, 1), (2, 5), (6, 6), (7, 8), (9, 10), (11, 57)]
# [-6, -4] [-3] [-2] [-1] [0] [1] [2, 5] [6, 11]




