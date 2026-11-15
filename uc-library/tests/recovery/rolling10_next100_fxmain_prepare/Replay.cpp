#include "core/portable/coreparams.h"
#ifndef PROVIDER_ONLY
#include "presonus/panel/FXMainPage.hpp"
#endif
#include <bit>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
int main(int argc, char **argv) {
  const bool provider = argc > 1 && std::string(argv[1]) == "provider";
  std::uint32_t present, mode, bits, index, initial;
  const std::string names[] = {
      "",        "H",      "D",          "hd",   "HD",
      "HD-main", "nameHD", "nameHDtail", "HDHD", std::string(60, 'x') + "HD"};
  while (std::cin >> present >> mode >> bits >> index >> initial) {
    if (index >= 10 || initial > 255 || present > 1)
      return 2;
    Core::Portable::ParamInfo info{};
    info.defaultValue = std::bit_cast<float>(bits);
    Core::Portable::NumericParam parameter(info);
    if (provider) {
      const char *name = names[index].c_str();
      const char *match = std::strstr(name, "HD");
      std::cout << std::bit_cast<std::uint32_t>(parameter.getValue()) << ' '
                << (match ? match - name : -1) << '\n';
    }
#ifndef PROVIDER_ONLY
    else {
      presonus::panel::FXMainState state{present ? &parameter : nullptr, mode,
                                         names[index],
                                         static_cast<std::uint8_t>(initial)};
      Presonus::Panel::FXMainPage page(state);
      page.prepare();
      if (state.mode != mode || state.name != names[index] ||
          state.parameter != (present ? &parameter : nullptr) ||
          std::bit_cast<std::uint32_t>(parameter.getValue()) != bits)
        return 3;
      std::cout << static_cast<unsigned>(state.flag) << '\n';
    }
#endif
  }
}
