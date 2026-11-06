#include "presonus/ColorMapping.hpp"
#include <algorithm>
namespace Presonus {
float ColorMapping::getDiff(const Item &a, const Item &b) {
  float lo = std::min(a.hue, b.hue), hi = std::max(a.hue, b.hue);
  float h = hi - lo;
  if (h > 180.f)
    h = hi - (lo + 360.f);
  float s = (a.saturation - b.saturation) * 60.f;
  float l = (a.lightness - b.lightness) * 100.f;
  return (h * h + s * s) + l * l;
}
} // namespace Presonus

namespace {
const std::array<Presonus::ColorMapping::Item, 17> &palette();
Presonus::ColorMapping::Item describe(Core::Color c) {
  Presonus::ColorMapping::Item item{0, 17, c, 0.f, 0.f, 0.f, 0.f};
  const float red = static_cast<float>(c.red) / 255.f;
  const float green = static_cast<float>(c.green) / 255.f;
  const float blue = static_cast<float>(c.blue) / 255.f;
  const float minimum = std::min(std::min(red, green), blue);
  const float maximum = std::max(std::max(red, green), blue);
  const float delta = maximum - minimum;
  const float sum = maximum + minimum;
  item.lightness = sum * .5f;
  item.alpha = static_cast<float>(c.alpha) / 255.f;
  if (delta != 0.f) {
    item.saturation = item.lightness < .5f
                          ? delta / sum
                          : delta / ((2.f - maximum) - minimum);
    if (red == maximum)
      item.hue = (green - blue) / delta;
    else if (green == maximum)
      item.hue = (blue - red) / delta + 2.f;
    else if (blue == maximum)
      item.hue = (red - green) / delta + 4.f;
    item.hue = item.hue * 60.f;
    if (item.hue < 0.f)
      item.hue = item.hue + 360.f;
  }
  return item;
}
std::size_t nearest(Core::Color color) {
  const auto item = describe(color);
  float best = 10000000.f;
  std::size_t result = 17;
  for (std::size_t i = 0; i < palette().size(); ++i) {
    const auto &candidate = palette()[i];
    const float difference = Presonus::ColorMapping::getDiff(item, candidate);
    if (difference < best) {
      best = difference;
      result = i;
    }
  }
  return result;
}
} // namespace
namespace Presonus {
const char *ColorMapping::mapColor(Core::Color color) {
  const auto i = nearest(color);
  return i < palette().size() ? palette()[i].name : nullptr;
}
std::uint32_t ColorMapping::mapColorToEnum(Core::Color color) {
  const auto i = nearest(color);
  return i < palette().size() ? palette()[i].enumeration : 17u;
}
} // namespace Presonus

namespace {
const std::array<Presonus::ColorMapping::Item, 17> &palette() {
  // Exact logical records from execution of the bound application initializer.
  static const std::array<Presonus::ColorMapping::Item, 17> entries{{
      {"red", 0, Core::Color(255, 0, 0, 255), 0x0.0p+0f, 0x1.0000000000000p+0f,
       0x1.0000000000000p-1f, 0x1.0000000000000p+0f},
      {"orange", 1, Core::Color(252, 167, 19, 255), 0x1.30e48a0000000p+5f,
       0x1.f3257c0000000p-1f, 0x1.1010100000000p-1f, 0x1.0000000000000p+0f},
      {"lightorange", 2, Core::Color(252, 201, 64, 255), 0x1.5dc98a0000000p+5f,
       0x1.f02a340000000p-1f, 0x1.3d3d3e0000000p-1f, 0x1.0000000000000p+0f},
      {"pink", 3, Core::Color(254, 213, 229, 255), 0x1.5095da0000000p+8f,
       0x1.e82fac0000000p-1f, 0x1.d4d4d40000000p-1f, 0x1.0000000000000p+0f},
      {"pinkish", 4, Core::Color(255, 226, 147, 255), 0x1.5f1c720000000p+5f,
       0x1.0000000000000p+0f, 0x1.9393940000000p-1f, 0x1.0000000000000p+0f},
      {"yellow", 5, Core::Color(255, 255, 0, 255), 0x1.e000000000000p+5f,
       0x1.0000000000000p+0f, 0x1.0000000000000p-1f, 0x1.0000000000000p+0f},
      {"coral", 6, Core::Color(83, 189, 77, 255), 0x1.d324920000000p+6f,
       0x1.d608660000000p-2f, 0x1.0b0b0c0000000p-1f, 0x1.0000000000000p+0f},
      {"blueishwhite", 7, Core::Color(179, 253, 253, 255),
       0x1.6800000000000p+7f, 0x1.e5be5c0000000p-1f, 0x1.b1b1b20000000p-1f,
       0x1.0000000000000p+0f},
      {"white", 8, Core::Color(240, 240, 240, 255), 0x0.0p+0f, 0x0.0p+0f,
       0x1.e1e1e20000000p-1f, 0x1.0000000000000p+0f},
      {"purple", 9, Core::Color(250, 104, 250, 255), 0x1.2c00000000000p+8f,
       0x1.df2df20000000p-1f, 0x1.6363640000000p-1f, 0x1.0000000000000p+0f},
      {"deeppurple", 10, Core::Color(153, 97, 246, 255), 0x1.068ce20000000p+8f,
       0x1.c8d0800000000p-1f, 0x1.5858580000000p-1f, 0x1.0000000000000p+0f},
      {"green", 11, Core::Color(0, 255, 0, 255), 0x1.e000000000000p+6f,
       0x1.0000000000000p+0f, 0x1.0000000000000p-1f, 0x1.0000000000000p+0f},
      {"powderblue", 12, Core::Color(128, 234, 234, 255), 0x1.6800000000000p+7f,
       0x1.6eb3e60000000p-1f, 0x1.6b6b6c0000000p-1f, 0x1.0000000000000p+0f},
      {"turquoise", 13, Core::Color(2, 237, 201, 255), 0x1.559df40000000p+7f,
       0x1.f76e540000000p-1f, 0x1.dfdfe00000000p-2f, 0x1.0000000000000p+0f},
      {"lightblue", 14, Core::Color(79, 211, 255, 255), 0x1.8600000000000p+7f,
       0x1.0000000000000p+0f, 0x1.4f4f500000000p-1f, 0x1.0000000000000p+0f},
      {"blue", 15, Core::Color(0, 0, 255, 255), 0x1.e000000000000p+7f,
       0x1.0000000000000p+0f, 0x1.0000000000000p-1f, 0x1.0000000000000p+0f},
      {"off", 16, Core::Color(0, 0, 0, 255), 0x0.0p+0f, 0x0.0p+0f, 0x0.0p+0f,
       0x1.0000000000000p+0f},
  }};
  return entries;
}
} // namespace
