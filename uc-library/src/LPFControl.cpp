#include "presonus/LPFControl.hpp"

namespace {
constexpr int inset = 15;
}

LPFControl::~LPFControl() = default;

void LPFControl::draw(const Core::Portable::DrawEvent &event) {
  const auto *parameter = getParameter();
  if (!parameter)
    return;

  Core::Rect background;
  getClientRect(background);
  background.left += inset;
  background.right -= inset;
  background.top += inset;
  background.bottom -= inset;
  event.graphics.fillRect(background, getStyle().getBackColor());

  Core::Rect cutoff = background;
  cutoff.right = cutoff.left + static_cast<int>(parameter->getNormalized() *
                                                background.getWidth());
  if (cutoff.right > cutoff.left && cutoff.bottom > cutoff.top)
    event.graphics.fillRect(cutoff, getStyle().getTextColor());
  if (hasFocus())
    event.graphics.drawRect(background, Core::Portable::Colors::kWhite);
}
