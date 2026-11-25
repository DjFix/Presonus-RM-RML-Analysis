#include "core/portable/gui/coreview.h"
#include "presonus/PageComponent.hpp"
#include "presonus/surface/GroupsPageComponent.hpp"
#include <array>
#include <cstdlib>
#include <iostream>

namespace {
class Dependencies final : public presonus::surface::GroupsPageDependencies {
public:
  void refreshList() override { std::abort(); }
  void doselect() override { std::abort(); }
  void observeGroup(Core::Portable::Component *) override { std::abort(); }
};

class Bindings final : public presonus::page::Bindings {
public:
  void *castOwner(void *, int) const override { return nullptr; }
  const void *currentPage(void *) const override { return nullptr; }
  void stopTextInput(void *, bool) const override { std::abort(); }
  bool isEditingText(void *) const override { std::abort(); }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  presonus::surface::GroupsPageState state;
  std::array<Core::Portable::Component *, 17> entries{};
  state.firstGroups = {entries.data(), static_cast<int>(entries.size())};
  state.listOffset = std::stoi(argv[2]);
  Dependencies dependencies;
  Bindings bindings;
  Presonus::PageComponent hidden(nullptr, bindings);
  Presonus::Surface::GroupsPageComponent value(state, dependencies);
  value.bindPage(hidden);
  const int delta = std::stoi(argv[1]);
  auto axis = std::stoi(argv[3]) ? Core::Portable::WheelEvent::kVertical
                                 : Core::Portable::WheelEvent::kHorizontal;
  const Core::Portable::WheelEvent event(delta, axis);
  value.onWheelInput(event);
  std::cout << state.listOffset << ' ' << (event.delta == delta) << ' '
            << (event.axis == axis) << '\n';
}
