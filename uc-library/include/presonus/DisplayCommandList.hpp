#pragma once
#include "core/public/gui/corecolor.h"
#include "core/public/gui/corerect.h"
#include <array>
#include <cstdint>
#include <memory>

namespace Core::Portable {
class Bitmap;
}

namespace Presonus {
class DisplayCommandList {
public:
  using Command = std::array<std::uint8_t, 20>;
  struct BitmapEntry {
    std::uint32_t key = 0;
    std::uint16_t id = 0;

    bool operator==(const BitmapEntry &other) const { return key == other.key; }
    bool operator>(const BitmapEntry &other) const { return key > other.key; }
  };
  struct State {
    std::array<Command, 50> commands{};
    std::int32_t count = 0;
    std::uint32_t auxiliaryCursor = 0;
    std::array<BitmapEntry, 32> bitmapEntries{};
    std::size_t bitmapCount = 0;
    std::uint16_t nextBitmapId = 0;
  };
  DisplayCommandList();
  explicit DisplayCommandList(State &state) : state_(state) {}
  DisplayCommandList(const DisplayCommandList &) = default;
  void drawLine(int, int, int, int, const Core::Color &);
  void fillRect(const Core::TRect<int> &, const Core::Color &);
  void setClip(const Core::TRect<int> &);
  void drawVerticalLine(int, int, int, const Core::Color &);
  void drawHorizontalLine(int, int, int, const Core::Color &);
  // Portable command encoding retains 32-bit address keys and tokens.
  void drawBitmap(int, int, const Core::Portable::Bitmap &, int, int, int, int);
  void flush();

private:
  // Copies retain the same state binding as external-state lists.
  std::shared_ptr<State> ownedState_;
  State &state_;
  Command *append(std::uint8_t);
};
} // namespace Presonus
