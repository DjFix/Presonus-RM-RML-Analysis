#include "presonus/DAWTimeInfo.hpp"
#include <cstring>

namespace {
// Record fields are decoded from observed little-endian ARM bytes, without
// establishing original struct declarations or ownership.
double position(const std::uint8_t *record, unsigned offset) {
  std::uint64_t bits = 0;
  for (unsigned i = 0; i < 8; ++i)
    bits |= std::uint64_t(record[offset + i]) << (8 * i);
  double result;
  std::memcpy(&result, &bits, sizeof(result));
  return result;
}
const std::uint8_t *search(const std::uint8_t *records, int count, double value,
                           unsigned offset) {
  if (count == 1 || value < 0)
    return records;
  int low = 0, high = count, middle = 0;
  do {
    middle = low + (high - low) / 2;
    const int next = middle + 1;
    if (next < count && position(records + 24 * next, offset) <= value)
      low = next;
    else if (!(value < position(records + 24 * middle, offset)))
      return records + 24 * middle;
    else
      high = middle - 1;
  } while (low <= high);
  return records + 24 * middle;
}
// Observed immutable default payload, not a recovered original data
// declaration.
constexpr std::uint8_t defaultSignature[24] = {
    0, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
} // namespace
namespace Presonus {
const std::uint8_t *
DAWTimeInfo::TimeSignatureMap::findItem(double value) const {
  if (count_ <= 0)
    return defaultSignature;
  return search(records_, count_, value, 0);
}
const std::uint8_t *DAWTimeInfo::TempoMap::findItem(double value) const {
  if (count_ <= 0)
    return nullptr;
  return search(records_, count_, value, 16);
}
} // namespace Presonus

namespace Presonus {
const std::uint8_t *
DAWTimeInfo::TimeSignatureMap::findItemByBar(int value) const {
  if (count_ <= 0)
    return defaultSignature;
  if (count_ == 1 || value < 0)
    return records_;
  auto bar = [this](int i) {
    std::uint32_t bits = 0;
    for (unsigned j = 0; j < 4; ++j)
      bits |= std::uint32_t(records_[24 * i + 16 + j]) << (8 * j);
    std::int32_t result;
    std::memcpy(&result, &bits, 4);
    return result;
  };
  int low = 0, high = count_, middle = 0;
  do {
    middle = low + (high - low) / 2;
    int next = middle + 1;
    if (next < count_ && value >= bar(next))
      low = next;
    else if (value >= bar(middle))
      return records_ + 24 * middle;
    else
      high = middle - 1;
  } while (low <= high);
  return records_ + 24 * middle;
}
double DAWTimeInfo::TempoMap::secondsToPpq(double seconds) const {
  const auto *item = findItem(seconds);
  if (!item)
    return seconds + seconds;
  if (seconds < 0)
    return seconds / position(item, 8);
  return (seconds - position(item, 16)) / position(item, 8) + position(item, 0);
}
} // namespace Presonus
