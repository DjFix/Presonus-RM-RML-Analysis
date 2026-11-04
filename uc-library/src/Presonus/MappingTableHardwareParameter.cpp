#include "presonus/MappingTable.hpp"
namespace Presonus {
Core::Portable::Parameter *
MappingTable::getHardwareParameter(const char *name) const {
  auto *item = findItem(name);
  return item ? extended().parameter(*item) : nullptr;
}
} // namespace Presonus
