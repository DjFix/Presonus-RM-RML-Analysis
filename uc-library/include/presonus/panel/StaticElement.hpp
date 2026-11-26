#pragma once

#include "presonus/panel/OffscreenElement.hpp"
#include <string>

namespace Presonus::Panel {
// Portable teardown model. The inherited constructor supplies host setup.
class StaticElement : public OffscreenElement {
public:
  using OffscreenElement::OffscreenElement;
  explicit StaticElement(const ElementInfo &info);
  void render(IDisplay &display, bool force) override;
  StaticElement(int x, int y, const char *text);
  ~StaticElement() override;
  void setNeedsToDraw(bool value);
  const std::string &text() const { return text_; }

private:
  std::string text_;
};
} // namespace Presonus::Panel
