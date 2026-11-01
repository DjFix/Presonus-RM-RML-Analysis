#pragma once
#include "core/public/corevector.h"
#include <cstring>

namespace presonus::mapping {
class ItemOperations;
struct Entry;
} // namespace presonus::mapping

namespace Presonus {
// Intentional portable source contract. Members/constructor and return types
// below do not establish the firmware declaration, layout, or ARM32 ABI.
class MappingTable {
public:
  class Item; // Opaque original identity; no inferred original fields.
  MappingTable(const presonus::mapping::Entry *sortedEntries, int count,
               presonus::mapping::ItemOperations &operations);
  Item *findItem(const char *name) const;
  void setControlFullOff(const char *name);
  void setControlInverseMode(const char *name, bool state);
  void setControlEnabled(const char *name, bool state);
  void setControlImmediate(const char *name, bool state);

private:
  const presonus::mapping::Entry *entries_;
  int count_;
  presonus::mapping::ItemOperations &operations_;
};
} // namespace Presonus

namespace presonus::mapping {
// Independent source-port record, not the original MappingTable::Item layout.
// Caller owns records, NUL-terminated names and opaque items for table
// lifetime. Input names must be nonnull, unique, lexically sorted and at most
// 31 bytes.
struct Entry {
  const char *name;
  Presonus::MappingTable::Item *item;
  bool operator==(const Entry &other) const {
    return std::strcmp(name, other.name) == 0;
  }
  bool operator>(const Entry &other) const {
    return std::strcmp(name, other.name) > 0;
  }
};
// Required application dependency boundary, deliberately no default/no-op
// provider. Original Item and panel behavior remain unresolved dependencies.
class ItemOperations {
public:
  virtual ~ItemOperations() = default;
  virtual void fullOff(Presonus::MappingTable::Item &) = 0;
  virtual void inverseMode(Presonus::MappingTable::Item &, bool) = 0;
  virtual void enabled(Presonus::MappingTable::Item &, bool) = 0;
  virtual void immediate(Presonus::MappingTable::Item &, bool) = 0;
};
} // namespace presonus::mapping
