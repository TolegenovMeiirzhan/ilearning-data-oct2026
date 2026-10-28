
from array import array


class XorLinkedList:
    __slots__ = ('size', 'capacity', 'buffer', 'first', 'last')
    NOT_FOUND = 0xFFFFFFFF
    ELEMENT_SIZE = 2
    INITIAL_CAPACITY = 8
    MAX_CAPACITY = 65536

    def __init__(self):
        self.size = 0
        self.capacity = self.INITIAL_CAPACITY
        self.buffer = memoryview(array('I', [0]) * (self.capacity * 2))
        if self.buffer.itemsize != 4:
            raise RuntimeError('This implementation needs 32-bit unsigned int.')
        self.first = self.last = self.NOT_FOUND

    def __len__(self):
        return self.size

    @property
    def empty(self):
        return self.size == 0

    def ensure_capacity(self):
        if self.size >= self.MAX_CAPACITY:
            raise RuntimeError('Maximum list capacity reached.')
        if self.size == self.capacity:
            capacity = min(self.capacity * 2, self.MAX_CAPACITY)
            new = array('I', self.buffer)
            new.extend(array('I', [0]) * ((capacity - self.capacity) * 2))
            self.buffer = memoryview(new)
            self.capacity = capacity

    def check_address(self, address):
        if type(address) is not int or (address != self.NOT_FOUND and
                (address < 0 or address % 2 or address >= self.size * 2)):
            raise IndexError('Invalid node address.')

    def allocate(self, value, previous, following):





        if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
            raise ValueError('Value must be an unsigned 32-bit integer.')
        if self.size >= self.capacity:
            self.ensure_capacity()
        address = self.size * 2
        self.buffer[address] = value
        self.buffer[address + 1] = previous ^ following
        self.size += 1
        return address

    def insert_between(self, value, previous, following):





        if previous == self.NOT_FOUND:
            following = self.first
        elif following == self.NOT_FOUND:
            previous = self.last
                                                                                
        if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
            raise ValueError('Value must be an unsigned 32-bit integer.')
        if self.size >= self.capacity:
            self.ensure_capacity()
        address = self.size * 2
        buffer = self.buffer
        buffer[address] = value
        buffer[address + 1] = previous ^ following
        self.size += 1
        if previous == self.NOT_FOUND:
            self.first = address
        else:
            buffer[previous + 1] ^= following ^ address
        if following == self.NOT_FOUND:
            self.last = address
        else:
            buffer[following + 1] ^= previous ^ address
        return address

    def append(self, value):
        return self.insert_between(value, self.last, self.NOT_FOUND)

    def prepend(self, value):
        return self.insert_between(value, self.NOT_FOUND, self.first)

    def __getitem__(self, address):
        self.check_address(address)
        if address == self.NOT_FOUND:
            raise IndexError('No node at NOT_FOUND.')
        return self.buffer[address]

    def _addresses(self):
        previous, current = self.NOT_FOUND, self.first
        while current != self.NOT_FOUND:
            yield current
            previous, current = current, previous ^ self.buffer[current + 1]

    def __iter__(self):
        for address in self._addresses():
            yield self.buffer[address]

    def address(self, value):
        return next((a for a in self._addresses() if self.buffer[a] == value), self.NOT_FOUND)

    def reverse(self):
        self.first, self.last = self.last, self.first
        return self
