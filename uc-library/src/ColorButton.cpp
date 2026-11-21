#include "presonus/ColorButton.hpp"

void ColorButton::paramChanged(Core::Portable::Parameter *parameter,
                               int message) {
  Control::paramChanged(parameter, message);
  if (message == Core::Portable::Parameter::kChanged &&
      parameter == colorParameter_) {
    View::invalidate();
  }
}
