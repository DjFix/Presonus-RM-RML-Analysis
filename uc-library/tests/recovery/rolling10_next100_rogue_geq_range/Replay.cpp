#include "core/portable/coreparams.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#ifndef PROVIDER_ONLY
#include "presonus/panel/RogueFrontPanelComponent.hpp"
#endif
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
int main(int argc, char **argv) {
  bool provider = argc > 1 && std::string(argv[1]) == "--provider";
  std::uint32_t bits;
  int present, offset, count;
  while (std::cin >> bits >> present >> offset >> count) {
    float value;
    std::memcpy(&value, &bits, 4);
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.minValue = -2147483648.f;
    info.maxValue = 2147483520.f;
    Core::Portable::NumericParam selected(info);
    selected.setValue(value, false);
    Presonus::Mixer::MixerComponentBase mixer;
    for (int i = 0; i < count; ++i)
      mixer.inputChannels.add(nullptr);
    Core::Portable::Parameter &base = selected;
    if (provider) {
      float observed = present ? base.getValue() : 0.f;
      std::uint32_t observedBits;
      std::memcpy(&observedBits, &observed, 4);
      std::cout << observedBits << ' ' << mixer.inputChannels.count() << '\n';
    } else {
#ifndef PROVIDER_ONLY
      presonus::panel::RogueGeqViewportState state{
          present ? &selected : nullptr, mixer, offset};
      Presonus::Panel::RogueFrontPanelComponent panel(state);
      float before = selected.getValue();
      bool result = panel.checkGeqViewRange();
      if (selected.getValue() != before ||
          mixer.inputChannels.count() != count ||
          state.selected != (present ? &selected : nullptr) ||
          &state.mixer != &mixer)
        throw std::runtime_error("unexpected provider/state change");
      std::cout << int(result) << ' ' << state.offset << '\n';
#else
      throw std::runtime_error("provider only executable");
#endif
    }
  }
}
