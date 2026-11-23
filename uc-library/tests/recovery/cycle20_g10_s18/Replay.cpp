#include "presonus/MappableMixer.hpp"
#include "presonus/SLChannel.hpp"
#include "presonus/color/MixerColorConverter.hpp"

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string_view>

namespace {
using namespace Core::Portable;

class Channel final : public Presonus::SLChannelBase {
public:
  using Presonus::SLChannelBase::SLChannelBase;
  ColorParam *color = nullptr;
  Parameter *getColorParameter() const override { return color; }
};

class Edits final : public ParamObserverBase {
public:
  void paramChanged(Parameter *, int message) override {
    if (message == Parameter::kEdit)
      ++count;
  }
  int count = 0;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 8)
    return 2;
  const std::string_view mode(argv[1]);
  const bool hasMixer = std::atoi(argv[2]) != 0,
             hasNumber = std::atoi(argv[3]) != 0;
  const bool hasConverter = std::atoi(argv[4]) != 0,
             hasColor = std::atoi(argv[5]) != 0;
  const auto originalColor =
      static_cast<Core::uint32>(std::strtoul(argv[6], nullptr, 10));
  const auto originalNumber = std::strtof(argv[7], nullptr);
  MixerColorConverter converter;
  if (mode == "provider") {
    if constexpr (18 == 17) {
      const auto color =
          hasColor ? Core::Color::fromInt(originalColor) : Core::Color{};
      std::cout << converter.getColorIndexForRGB(color) << '\n';
    } else {
      const auto color =
          converter.getRGBFromColorIndex(static_cast<int>(originalNumber));
      std::cout << static_cast<Core::uint32>(color) << '\n';
    }
    return 0;
  }
  Presonus::MappableMixer mixer;
  mixer.setColorConverter(hasConverter ? &converter : nullptr);
  Edits numberEdits, colorEdits;
  ParamInfo numberInfo{};
  numberInfo.type = ParamInfo::kFloat;
  numberInfo.minValue = -256.f;
  numberInfo.maxValue = 256.f;
  ParamInfo colorInfo{};
  colorInfo.type = ParamInfo::kColor;
  NumericParam index(numberInfo);
  ColorParam rgb(colorInfo);
  index.setValue(originalNumber);
  rgb.setColor(originalColor, false);
  index.setController(&numberEdits);
  rgb.setController(&colorEdits);
  Channel channel("offline");
  if (hasMixer)
    channel.bindSourcePortColorMixer(&mixer);
  if (hasNumber) {
    if constexpr (18 == 17)
      channel.bindWritableColorIndexParameter(index);
    else
      channel.bindColorIndexParameter(&index);
  }
  if (hasColor)
    channel.color = &rgb;
  if constexpr (18 == 17)
    channel.updateColorIndex();
  else
    channel.updateColorFromIndex();
  index.setController(nullptr);
  rgb.setController(nullptr);
  std::cout << std::setprecision(9) << index.getValue() << ' ' << rgb.getColor()
            << ' ' << numberEdits.count << ' ' << colorEdits.count << '\n';
}
