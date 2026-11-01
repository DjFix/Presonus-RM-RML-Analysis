#include "presonus/MappingTable.hpp"
namespace Presonus {
MappingTable::MappingTable(const presonus::mapping::Entry *entries, int count,
                           presonus::mapping::ItemOperations &operations)
    : entries_(entries), count_(count), operations_(operations) {}
MappingTable::Item *MappingTable::findItem(const char *name) const {
  const Core::ConstVector<presonus::mapping::Entry> entries(entries_, count_);
  const presonus::mapping::Entry key{name, nullptr};
  const auto *entry = entries.search(key);
  return entry ? entry->item : nullptr;
}
void MappingTable::setControlFullOff(const char *name) {
  if (auto *item = findItem(name))
    operations_.fullOff(*item);
}
void MappingTable::setControlInverseMode(const char *name, bool state) {
  if (auto *item = findItem(name))
    operations_.inverseMode(*item, state);
}
void MappingTable::setControlEnabled(const char *name, bool state) {
  if (auto *item = findItem(name))
    operations_.enabled(*item, state);
}
void MappingTable::setControlImmediate(const char *name, bool state) {
  if (auto *item = findItem(name))
    operations_.immediate(*item, state);
}
} // namespace Presonus
