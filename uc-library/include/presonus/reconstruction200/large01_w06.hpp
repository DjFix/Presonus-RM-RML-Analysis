#pragma once
#include "core/public/gui/corecolor.h"
#include "core/public/gui/corerect.h"
#include <array>
#include <cstdint>

namespace Presonus {
// Source-port borrowed state. No original object layout or lifecycle is
// claimed.
class SpectrumPainter {
public:
  explicit SpectrumPainter(const Core::TRect<int> &last) : last_(last) {}
  Core::TRect<int> getLastDrawnRect() const;

private:
  const Core::TRect<int> &last_;
};
class DisplayCommandList {
public:
  using Command = std::array<std::uint8_t, 20>;
  struct State {
    std::array<Command, 50> commands{};
    std::int32_t count = 0;
    std::uint32_t auxiliaryCursor = 0;
  };
  explicit DisplayCommandList(State &state) : state_(state) {}
  void drawLine(int, int, int, int, const Core::Color &);
  void fillRect(const Core::TRect<int> &, const Core::Color &);
  void setClip(const Core::TRect<int> &);
  void drawVerticalLine(int, int, int, const Core::Color &);
  void drawHorizontalLine(int, int, int, const Core::Color &);
  void flush();

private:
  State &state_;
  Command *append(std::uint8_t);
};
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
