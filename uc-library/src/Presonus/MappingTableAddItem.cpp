#include "presonus/MappingTable.hpp"

#include <algorithm>
#include <array>
#include <memory>

namespace Presonus {
namespace {
constexpr int itemCapacity = 1024;

// Convert the field values of the native descriptor into the pinned CCL type.
constexpr auto aliasInfo = [] {
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kAlias;
  constexpr char name[] = "hwparam";
  for (std::size_t i = 0; i < sizeof(name); ++i)
    info.name[i] = name[i];
  return info;
}();
} // namespace

struct MappingTable::OwnedRoster {
  std::array<Item, itemCapacity> items;
  std::array<std::unique_ptr<Core::Portable::AliasParam>, itemCapacity> aliases;
  std::array<presonus::mapping::Entry, itemCapacity> entries{};
  int count = 0;

  ~OwnedRoster() {
    for (int i = 0; i < count; ++i) {
      const auto slot = entries[i].item - items.data();
      aliases[slot].reset();
    }
  }
};

MappingTable::MappingTable(OwnedItems, presonus::mapping::ItemOperations &ops)
    : MappingTable(nullptr, 0, ops) {
  ownedRoster_ = std::make_shared<OwnedRoster>();
}

Core::ConstVector<presonus::mapping::Entry> MappingTable::ownedEntries() const {
  return {ownedRoster_->entries.data(), ownedRoster_->count};
}

const MappingTable::Item *MappingTable::sourcePortItemAt(int index) const {
  if (!ownedRoster_ || index < 0 || index >= ownedRoster_->count)
    return nullptr;
  return ownedRoster_->entries[index].item;
}

void MappingTable::addItem(const char *name) {
  if (!ownedRoster_)
    return;

  // The original allocates and constructs the candidate before scanning the
  // roster. Retain that order, with automatic cleanup if insertion is refused.
  auto alias = std::make_unique<Core::Portable::AliasParam>(aliasInfo, false);
  Item item(name, alias.get());

  auto &roster = *ownedRoster_;
  const auto begin = roster.entries.begin();
  const auto end = begin + roster.count;
  const auto position = std::find_if(begin, end, [&](const auto &entry) {
    return std::strcmp(entry.name, item.name) > 0;
  });
  if (roster.count == itemCapacity)
    return;

  auto &stored = roster.items[roster.count];
  stored = item;
  roster.aliases[roster.count] = std::move(alias);
  std::move_backward(position, end, end + 1);
  *position = {stored.name, &stored};
  ++roster.count;
}
} // namespace Presonus
