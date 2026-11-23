#pragma once

#include "presonus/panel/Element.hpp"
#include "presonus/surface_panel/IDisplay.hpp"

namespace Presonus::Panel {
// Portable teardown model. The inherited constructor supplies host setup.
class FillElement : public Element {
public:
  using Element::Element;
  FillElement(int x, int y, int width, int height, int value);
  ~FillElement() override;
  // Class-local render. The portable Element interface has a nonvirtual render.
  void render(IDisplay &display, bool force);
  const Rectangle &fillRectangle() const { return rectangle_; }
  int sourcePortFillValue() const { return value_; }

private:
  Rectangle rectangle_{};
  int value_ = 0;
};
} // namespace Presonus::Panel
