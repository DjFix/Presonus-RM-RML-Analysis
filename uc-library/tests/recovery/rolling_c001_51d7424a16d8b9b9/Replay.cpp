#include "presonus/MappableMixer.hpp"
#include "presonus/color/IColorConverter.hpp"
#include "presonus/mixer_state/MixerState.hpp"
#include <array>
#include <iostream>

namespace {
class Converter final : public Presonus::IColorConverter {
public:
  int getColorIndexForRGB(const Core::Color &) const override { return 0; }
  Core::Color getRGBFromColorIndex(int) const override { return {}; }
};
} // namespace

int main() {
  Presonus::IPresetHandler first, second;
  Converter converter;
  std::array<Presonus::IPresetHandler *, 3> values{nullptr, &first, &second};
  std::array<Presonus::MappableMixer, 2> mixers;
  for (auto &mixer : mixers) {
    if (mixer.getPresetHandler())
      return 2;
    mixer.setColorConverter(&converter);
  }
  std::array<Presonus::IPresetHandler *, 2> stored{};
  int identity, instance;
  while (std::cin >> identity >> instance) {
    if (identity < 0 || identity > 2 || instance < 0 || instance > 1)
      return 2;
    auto &mixer = mixers[instance];
    const auto other = 1 - instance;
    mixer.setPresetHandler(values[identity]);
    stored[instance] = values[identity];
    const Presonus::MappableMixer &view = mixer;
    if (view.getColorConverter() != &converter ||
        mixers[other].getPresetHandler() != stored[other])
      return 3;
    const auto *result = view.getPresetHandler();
    int index = -1;
    for (int value = 0; value < 3; ++value)
      if (result == values[value])
        index = value;
    std::cout << index << '\n';
  }
  return std::cin.eof() ? 0 : 2;
}
