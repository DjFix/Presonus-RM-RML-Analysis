#pragma once
#include "core/public/gui/corecolor.h"
#include "core/public/gui/corerect.h"
#include <array>
#include <cstdint>

namespace Presonus {
class ColorMapping {
public:
  // Logical source model of native 28-byte table records; original declarations
  // pending.
  struct Item {
    const char *name;
    std::uint32_t enumeration;
    Core::Color color;
    float hue, saturation, lightness, alpha;
  };
  static float getDiff(const Item &, const Item &);
  static const char *mapColor(Core::Color);
  static Core::Color mapColor(const char *); // Source-port return spelling.
  static std::uint32_t mapColorToEnum(Core::Color);
};
} // namespace Presonus
