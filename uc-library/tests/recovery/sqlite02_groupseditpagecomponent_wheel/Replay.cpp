#include "core/portable/gui/coreview.h"
#include "presonus/surface/GroupsEditPageComponent.hpp"
#include <cstdlib>
#include <iostream>

namespace {
class Dependencies final : public presonus::surface::GroupsEditDependencies {
public:
  presonus::surface::GroupsEditSelection findGroupsPage() override {
    std::abort();
  }
  bool hasSlaveMixer() override { std::abort(); }
  Core::ConstVector<Core::Portable::Component *> components(const char *,
                                                            bool) override {
    std::abort();
  }
  Core::Portable::Parameter *findParameter(const char *) override {
    std::abort();
  }
  void startTextInput(Core::Portable::Parameter *, const char *,
                      Presonus::Surface::GroupsEditPageComponent &) override {
    std::abort();
  }
  void pageOnShow(bool) override { std::abort(); }
  Presonus::PageComponent &page() override { std::abort(); }
  void connect(const char *, Core::Portable::Parameter *) override {
    std::abort();
  }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  Dependencies dependencies;
  Presonus::Surface::GroupsEditPageComponent value(
      Presonus::Surface::GroupsEditPageComponent::SourcePortConstruction{},
      dependencies);
  auto &state = value.sourcePortState();
  if (!state.items.resize(26))
    return 3;
  for (int i = 0; i < 26; ++i)
    state.items.add({});
  state.listOffset = std::stoi(argv[2]);
  const int delta = std::stoi(argv[1]);
  auto axis = std::stoi(argv[3]) ? Core::Portable::WheelEvent::kVertical
                                 : Core::Portable::WheelEvent::kHorizontal;
  const Core::Portable::WheelEvent event(delta, axis);
  value.onWheelInput(event);
  std::cout << state.listOffset << ' ' << (event.delta == delta) << ' '
            << (event.axis == axis) << '\n';
}
