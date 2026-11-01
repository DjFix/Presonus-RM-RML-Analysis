#include "presonus/surface/GroupsPageComponent.hpp"
#include <iostream>
#include <string>
#include <vector>
using presonus::surface::GroupsPageState;
struct Dependencies : presonus::surface::GroupsPageDependencies {
  GroupsPageState &s;
  std::vector<int> trace;
  explicit Dependencies(GroupsPageState &s) : s(s) {}
  void refreshList() override {
    trace.push_back(1);
    trace.push_back(s.listOffset);
  }
  void doselect() override {
    trace.push_back(2);
    trace.push_back(s.selection);
  }
  void observeGroup(Core::Portable::Component *p) override {
    trace.push_back(3);
    trace.push_back(static_cast<int>(reinterpret_cast<std::uintptr_t>(p)));
    trace.push_back(
        static_cast<int>(reinterpret_cast<std::uintptr_t>(s.observedGroup)));
  }
};
struct Parameter : Core::Portable::NumericParam {
  int id;
  Dependencies &d;
  Parameter(const Core::Portable::ParamInfo &info, int id, Dependencies &d)
      : NumericParam(info), id(id), d(d) {}
  void setValue(Core::Portable::ParamValue value, bool edit) override {
    d.trace.push_back(4);
    d.trace.push_back(id);
    d.trace.push_back(static_cast<int>(value));
    d.trace.push_back(edit);
    NumericParam::setValue(value, edit);
  }
};
int main() {
  int op, a, b, old, arg, selection, observed, n;
  while (std::cin >> op >> a >> b >> old >> arg >> selection >> observed >> n) {
    GroupsPageState s;
    std::vector<Core::Portable::Component *> first(64), second(64);
    for (int i = 0; i < 64; ++i) {
      first[i] =
          reinterpret_cast<Core::Portable::Component *>(0x400000u + 4 * i);
      second[i] =
          reinterpret_cast<Core::Portable::Component *>(0x410000u + 4 * i);
    }
    s.firstGroups =
        Core::ConstVector<Core::Portable::Component *>(first.data(), a);
    s.secondGroups =
        Core::ConstVector<Core::Portable::Component *>(second.data(), b);
    s.listOffset = old;
    s.selection = selection;
    s.observedGroup = reinterpret_cast<Core::Portable::Component *>(
        static_cast<std::uintptr_t>(static_cast<std::uint32_t>(observed)));
    Dependencies d(s);
    Core::Portable::ParamInfo info{};
    std::vector<Parameter *> owned;
    std::vector<Core::Portable::Parameter *> params;
    for (int i = 0; i < n; ++i) {
      auto *p = new Parameter(info, 0x500000 + 0x100 * i, d);
      owned.push_back(p);
      params.push_back(p);
    }
    s.selectionParameters =
        Core::ConstVector<Core::Portable::Parameter *>(params.data(), n);
    Presonus::Surface::GroupsPageComponent c(s, d);
    int result = 0;
    switch (op) {
    case 1:
      c.addListOffset(arg);
      break;
    case 2:
      result = c.getMaxListOffset();
      break;
    case 3:
      c.setListOffset(arg);
      break;
    case 4:
      c.deSelect();
      break;
    case 5:
      c.updateSelection();
      break;
    default:
      return 2;
    }
    std::cout << result << ' ' << s.listOffset << ' ' << s.selection << ' '
              << reinterpret_cast<std::uintptr_t>(s.observedGroup) << ' '
              << d.trace.size();
    for (int v : d.trace)
      std::cout << ' ' << v;
    std::cout << '\n';
    for (auto *p : owned)
      delete p;
  }
}
