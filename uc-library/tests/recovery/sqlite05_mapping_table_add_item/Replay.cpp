#include "presonus/MappingTable.hpp"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <new>
#include <type_traits>
#include <utility>
#include <vector>

using Core::Portable::AliasParam;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Presonus::MappingTable;

namespace {
void require(bool condition) {
  if (!condition)
    std::abort();
}

struct Operations : presonus::mapping::ItemOperations {
  void fullOff(MappingTable::Item &) override { std::abort(); }
  void inverseMode(MappingTable::Item &, bool) override { std::abort(); }
  void enabled(MappingTable::Item &, bool) override { std::abort(); }
  void immediate(MappingTable::Item &, bool) override { std::abort(); }
};

struct Trace : Core::Portable::ParamObserverBase {
  struct Allocation {
    void *address;
    bool destroyed, freed;
  };
  std::array<Allocation, 1025> aliases{};
  int total = 0;
  bool trace = false, fail = false, trackConstruction = false;
  void *expectedAlias = nullptr;

  Allocation *find(void *address) {
    for (int i = total - 1; i >= 0; --i)
      if (aliases[i].address == address && !aliases[i].freed)
        return &aliases[i];
    return nullptr;
  }

  void paramChanged(Parameter *parameter, int message) override {
    if (message != Parameter::kDestroyed)
      return;
    auto *entry = find(parameter);
    require(entry && !entry->destroyed);
    entry->destroyed = true;
    std::cout << "destroy " << (entry - aliases.data()) << '\n';
    parameter->removeObserver(this);
  }

  void deleting(void *address) {
    if (auto *entry = find(address)) {
      require(entry->destroyed);
      entry->freed = true;
      std::cout << "free " << (entry - aliases.data()) << '\n';
    }
  }
} state;

void checkAlias(AliasParam *alias) {
  require(alias && alias->getType() == ParamInfo::kAlias &&
          alias->getTag() == 0 &&
          std::strcmp(alias->getName(), "hwparam") == 0 &&
          alias->getOriginal() == nullptr);
}
} // namespace

extern "C" void *realNew(std::size_t) asm("__real__Znwm");
extern "C" void *wrappedNew(std::size_t size) asm("__wrap__Znwm");
extern "C" void *wrappedNew(std::size_t size) {
  if (state.trackConstruction && size == sizeof(AliasParam) &&
      !state.expectedAlias) {
    if (state.trace)
      std::cout << "allocate\n";
    if (state.fail)
      throw std::bad_alloc{};
    return state.expectedAlias = realNew(size);
  }
  return realNew(size);
}

extern "C" void realDelete(void *) asm("__real__ZdlPv");
extern "C" void wrappedDelete(void *address) asm("__wrap__ZdlPv");
extern "C" void wrappedDelete(void *address) {
  state.deleting(address);
  realDelete(address);
}
extern "C" void realSizedDelete(void *, std::size_t) asm("__real__ZdlPvm");
extern "C" void wrappedSizedDelete(void *address,
                                   std::size_t size) asm("__wrap__ZdlPvm");
extern "C" void wrappedSizedDelete(void *address, std::size_t size) {
  state.deleting(address);
  realSizedDelete(address, size);
}

extern "C" int realStrcmp(const char *, const char *) asm("__real_strcmp");

extern "C" void realAlias(AliasParam *, const ParamInfo &, bool) asm(
    "__real__ZN4Core8Portable10AliasParamC1ERKNS0_9ParamInfoEb");
extern "C" void wrapAlias(AliasParam *, const ParamInfo &, bool) asm(
    "__wrap__ZN4Core8Portable10AliasParamC1ERKNS0_9ParamInfoEb");
extern "C" void wrapAlias(AliasParam *alias, const ParamInfo &info,
                          bool ownsInfo) {
  if (state.trackConstruction) {
    require(alias == state.expectedAlias && !ownsInfo && state.total < 1025);
    require(info.type == ParamInfo::kAlias && info.tag == 0 &&
            realStrcmp(info.name, "hwparam") == 0 && info.minValue == 0 &&
            info.maxValue == 0 && info.midValue == 0 &&
            info.defaultValue == 0 && info.deltaValue == 0 && info.flags == 0 &&
            !info.unitName && !info.curveName && !info.stringList &&
            !info.title && !info.shortTitle);
    state.aliases[state.total++] = {alias, false, false};
    if (state.trace)
      std::cout << "alias\n";
  }
  realAlias(alias, info, ownsInfo);
  if (state.trackConstruction)
    alias->addObserver(&state);
}

extern "C" void realItem(MappingTable::Item *, const char *, AliasParam *) asm(
    "__real__"
    "ZN8Presonus12MappingTable4ItemC1EPKcPN4Core8Portable10AliasParamE");
extern "C" void wrapItem(MappingTable::Item *, const char *, AliasParam *) asm(
    "__wrap__"
    "ZN8Presonus12MappingTable4ItemC1EPKcPN4Core8Portable10AliasParamE");
extern "C" void wrapItem(MappingTable::Item *item, const char *name,
                         AliasParam *alias) {
  if (state.trace) {
    require(alias == state.expectedAlias);
    std::cout << "item " << std::quoted(name ? name : "") << '\n';
  }
  realItem(item, name, alias);
}

extern "C" int wrapStrcmp(const char *, const char *) asm("__wrap_strcmp");
extern "C" int wrapStrcmp(const char *lhs, const char *rhs) {
  // Only record roster comparisons. Constructor field validation uses the
  // real strcmp directly, outside the observable ordering trace.
  if (state.trace)
    std::cout << "compare " << std::quoted(lhs) << ' ' << std::quoted(rhs)
              << '\n';
  return realStrcmp(lhs, rhs);
}

namespace {
void add(MappingTable &table, const char *name) {
  state.trackConstruction = true;
  try {
    table.addItem(name);
  } catch (const std::bad_alloc &) {
    require(state.fail && !state.expectedAlias);
    std::cout << "allocation_failed\n";
  }
  state.trackConstruction = false;
  state.expectedAlias = nullptr;
}

void rosterTest(int argc, char **argv, Operations &operations) {
  using Item = MappingTable::Item;
  std::vector<const Item *> initial;
  MappingTable owned(MappingTable::OwnedItems{}, operations);
  for (int i = 3; i < argc; ++i)
    add(owned, argv[i]);
  for (int i = 0; i < argc - 3; ++i) {
    const auto *item = owned.sourcePortItemAt(i);
    require(item);
    initial.push_back(item);
  }
  require(!owned.sourcePortItemAt(-1));
  require(owned.sourcePortItemAt(argc - 3) == nullptr);

  // A copy views the same roster and standard move keeps that roster alive.
  MappingTable moved = owned;
  MappingTable aliasView(std::move(moved));
  state.fail = std::string_view(argv[1]) == "fail";
  state.trace = true;
  add(owned, std::string_view(argv[1]) == "null" ? nullptr : argv[2]);
  state.trace = false;

  for (int i = 0; auto *item = owned.sourcePortItemAt(i); ++i) {
    require(aliasView.sourcePortItemAt(i) == item);
    require(item->control == nullptr && item->defaultColor.isEmpty());
    checkAlias(item->alias);
    const auto *found = owned.findItem(item->name);
    require(found && realStrcmp(found->name, item->name) == 0);
    require(aliasView.findItem(item->name) == found);
    auto original = std::find(initial.begin(), initial.end(), item);
    std::cout << "row " << (original - initial.begin()) << ' '
              << std::quoted(item->name.str()) << '\n';
  }
  require(!owned.findItem("unique_unsupported_lookup"));
}

void borrowedTest(Operations &operations) {
  static constexpr ParamInfo info{};
  AliasParam alias(info, false);
  MappingTable::Item item("borrowed", &alias);
  const presonus::mapping::Entry entry{item.name, &item};
  {
    MappingTable table(&entry, 1, operations);
    MappingTable copy = table;
    MappingTable moved(std::move(copy));
    require(moved.findItem("borrowed") == &item &&
            moved.sourcePortItemAt(0) == nullptr);
    moved.addItem("ignored");
    require(moved.findItem("ignored") == nullptr);
  }
  require(item.alias == &alias);
  std::cout << "borrowed_lookup_and_lifetime\n";
}

static_assert(std::is_copy_constructible_v<MappingTable>);
static_assert(std::is_move_constructible_v<MappingTable>);
static_assert(!std::is_copy_assignable_v<MappingTable>);
} // namespace

int main(int argc, char **argv) {
  Operations operations;
  if (argc == 2 && std::string_view(argv[1]) == "borrowed") {
    borrowedTest(operations);
    return 0;
  }
  if (argc < 3)
    return 2;
  rosterTest(argc, argv, operations);
  for (int i = 0; i < state.total; ++i)
    require(state.aliases[i].destroyed && state.aliases[i].freed);
}
