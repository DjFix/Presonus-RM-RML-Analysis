#include "presonus/DisplayCommandList.hpp"
#include "core/public/corevector.h"
#include <algorithm>
#include <cstdlib>
namespace {
using BitmapEntry = Presonus::DisplayCommandList::BitmapEntry;
struct BitmapSearch : Core::ConstVector<BitmapEntry> {
  using Core::ConstVector<BitmapEntry>::compare;
};
void half(Presonus::DisplayCommandList::Command &c, unsigned pos,
          std::uint32_t value) {
  c[pos] = static_cast<std::uint8_t>(value);
  c[pos + 1] = static_cast<std::uint8_t>(value >> 8);
}
void rgba(Presonus::DisplayCommandList::Command &c, const Core::Color &v) {
  c[12] = v.red;
  c[13] = v.green;
  c[14] = v.blue;
  c[15] = v.alpha;
}
void rect(Presonus::DisplayCommandList::Command &c, const Core::TRect<int> &r) {
  half(c, 4, static_cast<std::uint32_t>(r.left));
  half(c, 6, static_cast<std::uint32_t>(r.top));
  half(c, 8,
       static_cast<std::uint32_t>(r.right) -
           static_cast<std::uint32_t>(r.left));
  half(c, 10,
       static_cast<std::uint32_t>(r.bottom) -
           static_cast<std::uint32_t>(r.top));
}
} // namespace
namespace Presonus {
DisplayCommandList::DisplayCommandList()
    : ownedState_(std::make_shared<State>()), state_(*ownedState_) {
  state_.nextBitmapId = 100;
}
DisplayCommandList::Command *DisplayCommandList::append(std::uint8_t opcode) {
  if (state_.count > 49)
    return nullptr;
  // Negative counts address before the original buffer and are outside this
  // source-port domain.
  if (state_.count < 0)
    return nullptr;
  Command *c = &state_.commands[static_cast<unsigned>(state_.count++)];
  (*c)[0] = opcode;
  return c;
}
void DisplayCommandList::setClip(const Core::TRect<int> &r) {
  if (auto *c = append(0))
    rect(*c, r);
}
void DisplayCommandList::fillRect(const Core::TRect<int> &r,
                                  const Core::Color &v) {
  if (auto *c = append(1)) {
    rect(*c, r);
    rgba(*c, v);
  }
}
void DisplayCommandList::drawHorizontalLine(int x, int y, int n,
                                            const Core::Color &v) {
  if (auto *c = append(2)) {
    half(*c, 4, x);
    half(*c, 6, y);
    half(*c, 8, n);
    rgba(*c, v);
  }
}
void DisplayCommandList::drawVerticalLine(int x, int y, int n,
                                          const Core::Color &v) {
  if (auto *c = append(3)) {
    half(*c, 4, x);
    half(*c, 6, y);
    half(*c, 8, n);
    rgba(*c, v);
  }
}
void DisplayCommandList::drawLine(int x, int y, int x2, int y2,
                                  const Core::Color &v) {
  if (auto *c = append(4)) {
    half(*c, 4, x);
    half(*c, 6, y);
    half(*c, 8, x2);
    half(*c, 10, y2);
    rgba(*c, v);
  }
}
void DisplayCommandList::drawBitmap(int x, int y,
                                    const Core::Portable::Bitmap &bitmap,
                                    int srcX, int srcY, int width, int height) {
  // The original uses a 32-bit identity and emits an opaque 32-bit
  // address-plus-offset token. Keep those command bytes without dereferencing
  // the token or claiming the pinned Bitmap has the original field layout.
  const auto key =
      static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(&bitmap));
  BitmapEntry entry{key, 0};
  auto *entries = state_.bitmapEntries.data();
  auto *end = entries + state_.bitmapCount;
  // Call libc through its exported entry point even when the table is empty.
  auto *volatile search = &::bsearch;
  const auto *found = static_cast<const BitmapEntry *>(
      search(&entry, entries, state_.bitmapCount, sizeof(BitmapEntry),
             BitmapSearch::compare));
  if (found) {
    entry.id = found->id;
  } else {
    entry.id = state_.nextBitmapId++;
    if (state_.bitmapCount < state_.bitmapEntries.size()) {
      auto *position = std::upper_bound(
          entries, end, key, [](std::uint32_t k, const BitmapEntry &existing) {
            return k < existing.key;
          });
      std::move_backward(position, end, end + 1);
      *position = entry;
      ++state_.bitmapCount;
    }
    if (auto *command = append(6)) {
      half(*command, 4, entry.id);
      const auto token = key + 12U;
      half(*command, 8, token);
      half(*command, 10, token >> 16);
    }
  }
  if (auto *command = append(7)) {
    half(*command, 4, x);
    half(*command, 6, y);
    half(*command, 8, entry.id);
    half(*command, 10, srcX);
    half(*command, 12, srcY);
    half(*command, 14, width);
    half(*command, 16, height);
  }
}
void DisplayCommandList::flush() {
  state_.auxiliaryCursor = 0;
  state_.count = 0;
}
} // namespace Presonus
