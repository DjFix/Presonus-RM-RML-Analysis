#include "core/portable/corecomponent.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/panel/LCDManager.hpp"
#include "presonus/panel/PanelRegistrar.hpp"

#include <iostream>
#include <stdexcept>
#include <string>

namespace {
using Core::Portable::Component;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Presonus::Mixer::MixerComponentBase;
using Presonus::Panel::FrontPanelComponent;
using Presonus::Panel::ILCDDelegate;
using Presonus::Panel::LCDManager;
using Presonus::Panel::MixerLCD;
using Presonus::Panel::PanelRegistrar;

struct NoCommands final : presonus::panel::portable::Book {
  void command(unsigned) override {
    throw std::logic_error("unexpected book command");
  }
};

struct CaptureDelegate final : ILCDDelegate {
  explicit CaptureDelegate(const ILCDDelegate &target) : target(target) {}
  Core::Portable::Parameter *
  lookupElementParameter(const char *name) const override {
    ++calls;
    incoming = name;
    return target.lookupElementParameter(name);
  }
  const ILCDDelegate &target;
  mutable int calls = 0;
  mutable const char *incoming = nullptr;
};

constexpr ParamInfo panelFader =
    PARAM_INT_(6101, "fader", 0, 20, 7, "", "", 0, 0, "", nullptr);
constexpr ParamInfo mixerFader =
    PARAM_INT_(6201, "fader", 0, 20, 12, "", "", 0, 0, "", nullptr);
constexpr ParamInfo nestedFader =
    PARAM_INT_(6202, "fader", 0, 20, 15, "", "", 0, 0, "", nullptr);
} // namespace

int main() {
  MixerComponentBase mixer;
  Component mixerParameters("mixer");
  mixerParameters.addParameters(&mixerFader, 1);
  auto *other = new Component("other");
  auto *nested = new Component("panel");
  nested->addParameters(&nestedFader, 1);
  other->addChild(nested);
  mixerParameters.addChild(other);
  mixer.childLookupParameters = &mixerParameters;
  presonus::panel_binding::PanelRegistrarPortState registrarState;
  PanelRegistrar registrar(registrarState);
  FrontPanelComponent front(mixer, registrar);
  auto &panelParameters = front.portableState().component;
  panelParameters.addParameters(&panelFader, 1);

  NoCommands book;
  presonus::panel::portable::State state{book};
  MixerLCD lcd(state);
  lcd.bindLookupProviders(front, mixer);
  auto adapter = presonus::panel::portable::makeMixerLCDLookupDelegate(lcd);
  CaptureDelegate first(adapter);
  CaptureDelegate second(adapter);
  LCDManager manager(LCDManager::SourcePortConstruction{});
  const LCDManager &lookup = manager;
  if (lookup.lookupElementParameter("panel/fader"))
    return 1;

  unsigned binding;
  std::string query;
  while (std::cin >> binding >> query) {
    if (binding > 2)
      return 2;
    const auto firstBefore = first.calls;
    const auto secondBefore = second.calls;
    ILCDDelegate *delegates[] = {nullptr, &first, &second};
    manager.setDelegate(delegates[binding]);
    Parameter *result = lookup.lookupElementParameter(query.c_str());
    const int called = (first.calls != firstBefore)
                           ? 1
                           : ((second.calls != secondBefore) ? 2 : 0);
    if (first.calls - firstBefore + second.calls - secondBefore !=
            int(binding != 0) ||
        (called == 1 && first.incoming != query.c_str()) ||
        (called == 2 && second.incoming != query.c_str()))
      return 3;
    if (result && result != panelParameters.getParameterByTag(6101) &&
        result != mixerParameters.getParameterByTag(6201) &&
        result != nested->getParameterByTag(6202))
      return 4;
    std::cout << called << ' ' << (result ? result->getTag() : 0) << '\n';
  }
  manager.setDelegate(nullptr);
  return lookup.lookupElementParameter("panel/fader") ? 5 : 0;
}
