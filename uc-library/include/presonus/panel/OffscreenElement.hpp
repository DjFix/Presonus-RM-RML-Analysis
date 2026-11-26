#pragma once

#include "presonus/panel/Element.hpp"
#include <vector>

namespace Presonus::Panel {
// Partial portable lifetime model. The host virtual table follows the host ABI.
class OffscreenElement : public Element {
public:
  OffscreenElement(int x, int y);
  explicit OffscreenElement(const ElementInfo &info);
  ~OffscreenElement() override;
  void draw(IDisplay &display) override;
  static void operator delete(void *receiver) noexcept;

private:
  std::vector<char> cachedBits_;
};
} // namespace Presonus::Panel
