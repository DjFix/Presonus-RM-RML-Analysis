#pragma once

#include "presonus/panel/Element.hpp"

namespace Presonus::Panel {
// Partial portable lifetime model. The host virtual table follows the host ABI.
class OffscreenElement : public Element {
public:
  OffscreenElement(int x, int y);
  ~OffscreenElement() override;
  static void operator delete(void *receiver) noexcept;
};
} // namespace Presonus::Panel
