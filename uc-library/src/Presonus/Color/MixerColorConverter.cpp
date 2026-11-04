#include "presonus/color/MixerColorConverter.hpp"
#include "core/public/corestringbuffer.h"
#include "presonus/ColorMapping.hpp"
#include "presonus/DisplayCommandList.hpp"
#include "presonus/SpectrumPainter.hpp"
#include <array>
#include <cstring>
namespace {
// Original converter index table, distinct from ColorMapping enumeration order.
constexpr std::array<const char *, 17> names{
    "default",    "red",         "orange",    "lightorange", "pinkish",
    "deeppurple", "purple",      "pink",      "white",       "coral",
    "green",      "yellow",      "turquoise", "blue",        "lightblue",
    "powderblue", "blueishwhite"};
} // namespace
Presonus::IColorConverter::~IColorConverter() = default;
MixerColorConverter::~MixerColorConverter() = default;
int MixerColorConverter::getColorIndexForRGB(const Core::Color &color) const {
  // Explicit source-based adaptation of the original thin MappingTable wrapper;
  // use the actual provider, not the independent legacy int callback API.
  Core::CStringBuffer<64> name(Presonus::ColorMapping::mapColor(color));
  for (int i = 0; i < static_cast<int>(names.size()); ++i)
    if (std::strcmp(name, names[i]) == 0)
      return i;
  return 0;
}
Core::Color MixerColorConverter::getRGBFromColorIndex(int index) const {
  if (static_cast<unsigned>(index) >= names.size())
    return Presonus::ColorMapping::mapColor("default");
  Core::CStringBuffer<64> name(names[index]);
  return Presonus::ColorMapping::mapColor(name);
}
