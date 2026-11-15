#include "presonus/panel/BeastFrontPanelComponent.hpp"
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
int main(int argc, char **argv) {
  float values[] = {0, -2.5f, 0, 3.75f, 4.5f, 25.9f, 26, 27, 31.75f};
  if (argc == 2 && std::string(argv[1]) == "--observe-provider") {
    // This mode observes only actual CCL NumericParam; no reconstructed GEQ
    // method executes or supplies expected values to the native boundary.
    for (float input : values) {
      Core::Portable::ParamInfo pi{};
      Core::Portable::NumericParam parameter(pi);
      parameter.setValueFast(input);
      const float value = parameter.getValue();
      std::uint32_t bits;
      std::memcpy(&bits, &value, sizeof(bits));
      std::cout << bits << '\n';
    }
    return 0;
  }
  for (int i = 0; i < 9; ++i)
    for (int offset : {0, 4, 7, 40})
      for (int count : {0, 4, 32}) {
        Presonus::Mixer::MixerComponentBase m;
        for (int j = 0; j < count; ++j)
          m.inputChannels.add(nullptr);
        Core::Portable::ParamInfo pi{};
        Core::Portable::NumericParam p(pi);
        p.setValueFast(values[i]);
        Presonus::Panel::BeastFrontPanelComponent x(m, i == 0 ? nullptr : &p,
                                                    offset);
        std::cout << x.checkGeqViewRange() << ' ' << x.scrollOffset() << '\n';
      }
}
