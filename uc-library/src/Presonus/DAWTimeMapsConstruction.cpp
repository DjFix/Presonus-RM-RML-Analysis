#include "core/public/corevector.h"
#include "presonus/DAWTimeInfo.hpp"
#include <cstring>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {
// Explicit wire encoding keeps the borrowed algorithms independent of host
// padding, endianness and the intentionally unresolved original item layout.
void put32(std::uint8_t *p, std::uint32_t value) {
  for (unsigned i = 0; i < 4; ++i)
    p[i] = value >> (8 * i);
}
void putDouble(std::uint8_t *p, double value) {
  static_assert(sizeof(double) == 8 && std::numeric_limits<double>::is_iec559);
  std::uint64_t bits;
  std::memcpy(&bits, &value, 8);
  for (unsigned i = 0; i < 8; ++i)
    p[i] = bits >> (8 * i);
}
template <class Item> struct Storage {
  Core::Vector<Item> items;
  std::vector<std::uint8_t> records;
  Storage(int capacity, int delta) : items(capacity, delta) {}
};
void encode(std::uint8_t *p,
            const Presonus::DAWTimeInfo::TimeSignatureMap::Item &v) {
  putDouble(p, v.ppq);
  put32(p + 8, v.numerator);
  put32(p + 12, v.denominator);
  put32(p + 16, v.bar);
  put32(p + 20, 0);
}
void encode(std::uint8_t *p, const Presonus::DAWTimeInfo::TempoMap::Item &v) {
  putDouble(p, v.ppq);
  putDouble(p + 8, v.secondsPerPpq);
  putDouble(p + 16, v.seconds);
}
template <class Owned, class Item>
std::shared_ptr<const Owned> makeStorage(const Item *items, int count) {
  if (count < 0 || (count && !items))
    throw std::invalid_argument("map items");
  if (count > std::numeric_limits<int>::max() - (Owned::delta - 1))
    throw std::length_error("map capacity");
  // Construct directly at the requested capacity through the pinned provider.
  // The default original constructors separately retain their initial capacity.
  auto storage = std::make_shared<Owned>(count);
  if (storage->items.getCapacity() < count)
    throw std::bad_alloc();
  storage->records.resize(static_cast<std::size_t>(count) * 24);
  for (int i = 0; i < count; ++i) {
    if (!storage->items.add(items[i]))
      throw std::bad_alloc();
    encode(storage->records.data() + static_cast<std::size_t>(i) * 24,
           storage->items.at(i));
  }
  return storage;
}
} // namespace
namespace Presonus {
struct DAWTimeInfo::TimeSignatureMap::OwnedStorage : Storage<Item> {
  static constexpr int delta = 16;
  explicit OwnedStorage(int capacity = delta) : Storage(capacity, delta) {}
};
struct DAWTimeInfo::TempoMap::OwnedStorage : Storage<Item> {
  static constexpr int delta = 64;
  explicit OwnedStorage(int capacity = delta) : Storage(capacity, delta) {}
};
DAWTimeInfo::TimeSignatureMap::TimeSignatureMap()
    : owned_(std::make_shared<OwnedStorage>()) {}
DAWTimeInfo::TempoMap::TempoMap() : owned_(std::make_shared<OwnedStorage>()) {}
void DAWTimeInfo::TimeSignatureMap::replaceOwnedItems(const Item *items,
                                                      int count) {
  auto next = makeStorage<OwnedStorage>(items, count);
  owned_ = std::move(next);
  records_ = owned_->records.data();
  count_ = count;
}
void DAWTimeInfo::TempoMap::replaceOwnedItems(const Item *items, int count) {
  auto next = makeStorage<OwnedStorage>(items, count);
  owned_ = std::move(next);
  records_ = owned_->records.data();
  count_ = count;
}
int DAWTimeInfo::TimeSignatureMap::ownedCapacity() const noexcept {
  return owned_ ? owned_->items.getCapacity() : 0;
}
int DAWTimeInfo::TempoMap::ownedCapacity() const noexcept {
  return owned_ ? owned_->items.getCapacity() : 0;
}
int DAWTimeInfo::TimeSignatureMap::allocationDelta() const noexcept {
  return 16;
}
int DAWTimeInfo::TempoMap::allocationDelta() const noexcept { return 64; }
} // namespace Presonus
