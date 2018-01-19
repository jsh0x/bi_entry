import heapq, itertools

REMOVED = '<removed item>'


class PriorityQueue:
	def __init__(self):
		self.data = []
		self.entry_finder = {}
		self.counter = itertools.count()

	def add_item(self, item, priority: int=0):
		"""Add a new item or update the priority of an existing item"""
		if item in self.entry_finder:
			self.remove_item(item)
		count = next(self.counter)
		entry = [priority, count, item]
		self.entry_finder[item] = entry
		heapq.heappush(self.data, entry)

	def remove_item(self, item):
		"""Mark an existing item as REMOVED. Raise KeyError if not found."""
		entry = self.entry_finder.pop(item)
		entry[-1] = REMOVED

	def pop_item(self):
		"""Remove amd return the item with the lowest priority value. Raise KeyError if empty."""
		while self.data:
			priority, count, item = heapq.heappop(self.data)
			if item is not REMOVED:
				del self.entry_finder[item]
				return item
		raise KeyError('pop from an empty priority queue')


class Sorter:
	def __init__(self):
		self.scrap_pq = PriorityQueue()
		self.transact_pq = PriorityQueue()
		self.reason_pq = PriorityQueue()

	# def populate_scrap(self):
	# 	self.scrap_pq


	@staticmethod
	def sorting_algorithm():
		"""Variable to be taken into account:
			Entry date
			Unit type
			Times skipped
			Time of day
			Total qty
			"""

