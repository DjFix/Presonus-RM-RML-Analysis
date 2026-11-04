#pragma once
#include "core/public/gui/corecolor.h"
#include "core/public/gui/corerect.h"
#include <array>
#include <cstdint>

namespace Presonus {
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
} // namespace Presonus
