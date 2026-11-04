#include "presonus/DisplayCommandList.hpp"
namespace {
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
void DisplayCommandList::flush() {
  state_.auxiliaryCursor = 0;
  state_.count = 0;
}
} // namespace Presonus
