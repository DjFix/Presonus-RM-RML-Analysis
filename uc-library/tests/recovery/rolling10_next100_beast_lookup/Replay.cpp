#include "core/portable/coreparams.h"
#include "presonus/panel/BeastPanelRegistrar.hpp"
#include "presonus/panel/PanelParameterTables.hpp"
#include "presonus/panel/WolverinePanelRegistrar.hpp"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <string>
using Core::Portable::ParamInfo;
static std::uint32_t bits(float f) {
  std::uint32_t u;
  std::memcpy(&u, &f, 4);
  return u;
}
static void str(const char *s) {
  if (!s) {
    std::cout << "-";
    return;
  }
  std::cout << 'x';
  for (; *s; ++s)
    std::cout << std::hex << std::setw(2) << std::setfill('0')
              << unsigned(static_cast<unsigned char>(*s));
  std::cout << std::dec;
}
static void record(const ParamInfo &r) {
  std::cout << r.type << ' ' << r.tag << ' ';
  for (unsigned char c : r.name)
    std::cout << std::hex << std::setw(2) << std::setfill('0') << unsigned(c);
  std::cout << std::dec;
  for (float f :
       {r.minValue, r.maxValue, r.midValue, r.defaultValue, r.deltaValue})
    std::cout << ' ' << bits(f);
  std::cout << ' ' << r.flags;
  for (const char *s : {r.unitName, r.curveName, r.title, r.shortTitle}) {
    std::cout << ' ';
    str(s);
  }
  assert(r.stringList == nullptr);
  std::cout << '\n';
}
int main(int argc, char **argv) {
  if (argc == 3 && std::string(argv[1]) == "counts") {
    Presonus::Panel::WolverinePanelRegistrar w;
    Presonus::Panel::BeastPanelRegistrar b;
    int g;
    while (std::cin >> g)
      std::cout << (std::string(argv[2]) == "wolverine"
                        ? w.getParamInfoListSizeFromGroup(g)
                        : b.getParamInfoListSizeFromGroup(g))
                << '\n';
    return 0;
  }
  if (argc == 4 && std::string(argv[1]) == "tags") {
    Presonus::Panel::BeastPanelRegistrar b;
    struct {
      int before;
      int count;
      int after;
    } c{123, std::stoi(argv[3]), 456};
    const auto *p = b.getTags(std::stoi(argv[2]), c.count);
    assert(c.before == 123 && c.after == 456);
    std::cout << (p ? 1 : 0) << ' ' << c.count;
    if (p)
      for (int i = 0; i < c.count; ++i)
        std::cout << ' ' << static_cast<std::uint32_t>(p[i]);
    std::cout << '\n';
    return 0;
  }
  assert(argc == 5);
  std::string kind = argv[1];
  int group = std::stoi(argv[2]);
  unsigned address = std::stoul(argv[3]);
  int count = std::stoi(argv[4]);
  Presonus::Panel::WolverinePanelRegistrar w;
  Presonus::Panel::BeastPanelRegistrar b;
  const ParamInfo *info = kind == "wolverine"
                              ? w.getParamInfoListFromGroup(group)
                              : b.getParamInfoListFromGroup(group);
  int actualCount = kind == "wolverine"
                        ? w.getParamInfoListSizeFromGroup(group)
                        : b.getParamInfoListSizeFromGroup(group);
  assert(actualCount == count);
  assert(info == presonus::panel::panelParameterTable(address));
  assert((info != nullptr) == (address != 0));
  if (!info) {
    assert(count == 0);
    return 0;
  }
  // Metadata addresses and bytes must survive repeated owning consumer
  // destruction.
  for (int pass = 0; pass < 2; ++pass) {
    Core::Portable::ParamList list;
    list.add(info, count, false);
    assert(list.count() == count);
    for (int i = 0; i < count; ++i) {
      const ParamInfo &r = info[i];
      auto *p = list.at(i);
      assert(p && p->isNumeric() && !p->isOwnInfo());
      assert(p->getType() == r.type && p->getTag() == r.tag &&
             std::strcmp(p->getName(), r.name) == 0);
      // With ownsInfo=false Parameter retains the exact static name storage.
      assert(p->getName() == r.name);
      assert(bits(p->getMin()) == bits(r.minValue) &&
             bits(p->getMax()) == bits(r.maxValue));
      assert(bits(p->getDefault()) == bits(r.defaultValue) &&
             bits(p->getValue()) == bits(r.defaultValue));
      assert(p->isPublic() == !(r.flags & ParamInfo::kPrivate));
      assert(p->isStorable() == bool(r.flags & ParamInfo::kStorable));
      assert(p->isLinkable() == bool(r.flags & ParamInfo::kLinkable));
      assert(p->isMutable() == bool(r.flags & ParamInfo::kMutable));
      assert(p->isReadOnly() == bool(r.flags & ParamInfo::kReadOnly));
      assert(p->isUserFlag1() == bool(r.flags & ParamInfo::kUserFlag1));
      assert(p->isUserFlag2() == bool(r.flags & ParamInfo::kUserFlag2));
      p->setValue(r.minValue, false);
      assert(bits(p->getValue()) == bits(r.makeValid(r.minValue)));
      p->setValue(r.maxValue, false);
      assert(bits(p->getValue()) == bits(r.makeValid(r.maxValue)));
      p->resetValue(false);
      assert(bits(p->getValue()) == bits(r.defaultValue));
    }
  }
  for (int i = 0; i < count; ++i)
    record(info[i]);
}
