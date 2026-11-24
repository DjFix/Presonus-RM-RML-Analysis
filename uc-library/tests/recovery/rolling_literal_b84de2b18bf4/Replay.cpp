#include "presonus/panel/GambitPanelRegistrar.hpp"

#include <array>
#include <cstdio>
#include <cstring>
#include <type_traits>

using Registrar = Presonus::Panel::GambitPanelRegistrar;
static_assert(std::is_same_v<decltype(&Registrar::getPanelPortName),
                             const char *(Registrar::*)()>);

int main() {
  Registrar second;
  const char *saved;
  {
    Registrar first;
    const auto state = [](Registrar &receiver) {
      std::array<int, 18> output{};
      for (int i = -1; i <= 16; ++i)
        output[i + 1] = receiver.getParamInfoListSizeFromGroup(i);
      return output;
    };
    const auto beforeFirst = state(first);
    const auto beforeSecond = state(second);
    saved = first.getPanelPortName();
    if (!saved || saved != first.getPanelPortName() ||
        saved != second.getPanelPortName() || beforeFirst != state(first) ||
        beforeSecond != state(second))
      return 1;
  }
  if (saved != second.getPanelPortName())
    return 1;
  std::puts(saved);
}
