#include "presonus/BackgroundPainter.hpp"
namespace Presonus {
void BackgroundPainter::paint(const Core::TRect<int> &,
                              const Core::Portable::DrawEvent &event,
                              const Core::Portable::Style &style) {
  event.graphics.fillRect(event.updateRect, style.getBackColor());
}
} // namespace Presonus
