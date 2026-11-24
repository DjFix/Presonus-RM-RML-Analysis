#include "presonus/panel/WolverinePanelRegistrar.hpp"

#include <array>
#include <iostream>
#include <string_view>
#include <type_traits>
#include <utility>

using Presonus::Panel::WolverinePanelRegistrar;

static_assert(
    std::is_same_v<decltype(&WolverinePanelRegistrar::getPanelPortName),
                   const char *(WolverinePanelRegistrar::*)()>);

namespace {
constexpr std::array groups{-1, 0, 1, 2, 3, 15, 16};

auto observe(WolverinePanelRegistrar &receiver) {
  std::array<std::pair<int, const Core::Portable::ParamInfo *>, groups.size()>
      observations{};
  for (std::size_t i = 0; i < groups.size(); ++i) {
    observations[i] = {receiver.getParamInfoListSizeFromGroup(groups[i]),
                       receiver.getParamInfoListFromGroup(groups[i])};
  }
  return observations;
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 1;
  const std::string_view expected(argv[1]);
  const char *saved = nullptr;
  {
    WolverinePanelRegistrar first;
    WolverinePanelRegistrar second;
    const auto firstBefore = observe(first);
    const auto secondBefore = observe(second);
    saved = first.getPanelPortName();
    if (!saved || std::string_view(saved) != expected ||
        first.getPanelPortName() != saved ||
        second.getPanelPortName() != saved || observe(first) != firstBefore ||
        observe(second) != secondBefore)
      return 2;
  }
  WolverinePanelRegistrar newReceiver;
  if (newReceiver.getPanelPortName() != saved ||
      std::string_view(saved) != expected)
    return 3;
  std::cout << "4 calls across 3 receivers, stable literal after receiver "
               "destruction, 7 parameter-group observations per receiver "
               "preserved\n";
}
