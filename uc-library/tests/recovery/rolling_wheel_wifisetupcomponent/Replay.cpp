#include "core/portable/gui/coreview.h"
#include "presonus/surface/WifiSetupComponent.hpp"
#include <array>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace {
using namespace Core::Portable;

struct RecordingParam : NumericParam {
  explicit RecordingParam(const ParamInfo &info) : NumericParam(info, false) {}
  void fromString(const char *text, bool edit) override {
    std::cout << "T " << getTag() << ' ' << edit << ' ' << (*text ? text : "-")
              << '\n';
  }
  void setValue(float value, bool edit) override {
    std::cout << "V " << getTag() << ' ' << value << ' ' << edit << '\n';
  }
  void enable(bool enabled) override {
    std::cout << "E " << getTag() << ' ' << enabled << '\n';
  }
};

struct Dependencies : presonus::surface::WifiSetupDependencies {
  void pageOnShow(bool) override { std::abort(); }
  void startPasswordInput(Parameter *, const char *, const void *) override {
    std::abort();
  }
  void ensureManager() const override { std::abort(); }
  void updateList(ListParam *, ListParam *, ListParam *, bool) const override {
    std::abort();
  }
  bool findNetwork(const char *) const override { std::abort(); }
  bool networkHasFlag(const char *) const override { std::abort(); }
  const char *managerStatus(const Presonus::WIFIManager &) const override {
    std::abort();
  }
  const char *managerSSID(const Presonus::WIFIManager &) const override {
    std::abort();
  }
  const char *managerIP(const Presonus::WIFIManager &) const override {
    std::abort();
  }
  const char *networkSignal() const override { std::abort(); }
  void scan(bool) override { std::abort(); }
};

struct PageBindings : presonus::page::Bindings {
  bool visible;
  const void *page = nullptr;
  void *castOwner(void *owner, int) const override { return owner; }
  const void *currentPage(void *) const override {
    return visible ? page : nullptr;
  }
  void stopTextInput(void *, bool) const override {}
  bool isEditingText(void *) const override { return false; }
};
class Fixture : public Presonus::Surface::WifiSetupComponent {
public:
  using WifiSetupComponent::WifiSetupComponent;
  void add(Parameter *p) { paramList.add(p); }
};
} // namespace

int main() {
  int offset, delta, count, visible, axis;
  while (std::cin >> offset >> delta >> count >> visible >> axis) {
    presonus::surface::WifiSetupState state{offset, 3};
    presonus::surface::WifiScanPhase scan{};
    Dependencies deps;
    PageBindings binding;
    binding.visible = visible;
    Presonus::PageComponent page(&binding, binding);
    binding.page = &page;
    Presonus::DelayTimer timer(1.f);
    std::array<ParamInfo, 11> info{};
    std::vector<std::string> strings;
    for (int i = 0; i < count; ++i)
      strings.push_back("net" + std::to_string(i));
    std::vector<const char *> names;
    for (const auto &text : strings)
      names.push_back(text.c_str());
    Fixture fixture(state, scan, deps, page, timer);
    info[0].type = ParamInfo::kList;
    info[0].maxValue = count - 1;
    auto *list = new ListParam(info[0]);
    list->setSharedStrings(names.data(), count);
    fixture.add(list);
    for (int i = 1; i <= 10; ++i) {
      info[i].tag = 99 + i;
      info[i].type = ParamInfo::kFloat;
      fixture.add(new RecordingParam(info[i]));
    }
    const WheelEvent event(delta, axis ? WheelEvent::kVertical
                                       : WheelEvent::kHorizontal);
    fixture.onWheelInput(event);
    std::cout << "S " << state.listOffset << ' ' << state.selected << ' '
              << event.delta << ' ' << event.axis << '\n';
  }
}
