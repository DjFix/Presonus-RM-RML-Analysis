"""Bounded integer-only identity population, in ascending order."""


class IdentityBitmap:
    MAX_IDENTITY = 32_000_000

    def __init__(self):
        self.bits = bytearray()
        self.count = 0

    def add(self, value):
        if type(value) is not int or not 0 < value <= self.MAX_IDENTITY:
            raise ValueError(f'Unexpected compact integer identity: {value}')
        index, offset = divmod(value, 8)
        if index >= len(self.bits):
            self.bits.extend(b'\0' * (index + 1 - len(self.bits)))
        mask = 1 << offset
        if not self.bits[index] & mask:
            self.bits[index] |= mask
            self.count += 1

    def update(self, values):
        if isinstance(values, IdentityBitmap) and not self.bits:
            self.bits[:] = values.bits
            self.count = values.count
            return
        for value in values:
            self.add(value)

    def __len__(self):
        return self.count

    def __iter__(self):
        for index, current in enumerate(self.bits):
            while current:
                lowest = current & -current
                yield index * 8 + lowest.bit_length() - 1
                current ^= lowest
