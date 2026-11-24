#include "core/portable/coreparaminfo.h"
#include "presonus/panel/FrontPanelComponent.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>

namespace {
class WatchingDependencies final
    : public presonus::frontpanel_port::Dependencies {
public:
  mutable int calls = 0;

  void perform(presonus::frontpanel_port::Action, int, int) override {
    ++calls;
  }
  bool timerLongEnough() const override {
    ++calls;
    return false;
  }
  bool fadersLocked() const override {
    ++calls;
    return false;
  }
  const char *activePageName() const override {
    ++calls;
    return nullptr;
  }
  void paste(void *, const void *, const char *) override { ++calls; }
};

template <class T> auto bytesOf(const T &object) {
  std::array<unsigned char, sizeof(T)> image;
  std::memcpy(image.data(), &object, image.size());
  return image;
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const int offset = std::atoi(argv[1]);
  const int selected = std::atoi(argv[2]);
  const Core::Portable::ParamInfo range[] = {
      PARAM_INT(1, "geq-band-test", 0, 30, 0, "", nullptr, 0, 0)};
  Core::Portable::Component settings;
  settings.addParameters(range, 1);
  auto *selection = Core::Portable::core_cast<Core::Portable::NumericParam>(
      settings.getParameterByTag(1));
  if (!selection)
    return 3;
  selection->setValue(selected, false);
  if (selection->getValue() != selected)
    return 4;
  presonus::frontpanel_port::State state(settings);
  state.constructorWord164 = offset;
  WatchingDependencies dependencies;
  Presonus::Panel::FrontPanelComponent panel(state, dependencies);
  auto before = bytesOf(panel);
  auto stateBefore = bytesOf(state);
  auto settingsBefore = bytesOf(settings);
  auto parameterBefore = bytesOf(*selection);
  auto method = &Presonus::Panel::FrontPanelComponent::checkGeqViewRange;
  const bool result = (panel.*method)();
  std::cout << result << ' ' << (before == bytesOf(panel)) << ' '
            << (stateBefore == bytesOf(state)) << ' '
            << (settingsBefore == bytesOf(settings) &&
                settings.getParameterByTag(1) == selection &&
                parameterBefore == bytesOf(*selection) &&
                selection->getValue() == selected)
            << ' ' << dependencies.calls << '\n';
}
