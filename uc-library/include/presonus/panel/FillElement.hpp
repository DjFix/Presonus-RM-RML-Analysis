#pragma once

#include "presonus/panel/Element.hpp"
#include "presonus/surface_panel/IDisplay.hpp"

namespace Presonus::Panel {
// Portable teardown model. The inherited constructor supplies host setup.
class FillElement : public Element {
public:
  using Element::Element;
  explicit FillElement(const ElementInfo &info);
  FillElement(int x, int y, int width, int height, int value);
  ~FillElement() override;
  // Original fill dispatch on the host source-port Element interface.
  void render(IDisplay &display, bool force);
  const Rectangle &fillRectangle() const { return rectangle_; }
  int sourcePortFillValue() const { return value_; }

private:
  Rectangle rectangle_{};
  int value_ = 0;
};
} // namespace Presonus::Panel
