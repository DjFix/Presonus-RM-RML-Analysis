#include "presonus/surface/RadioToggleButton.hpp"
namespace Presonus::Surface {
// Real CCL Button BitmapReferences release icon/image, then Control detaches
// its parameter observer. Compiler-generated D0 performs real deallocation.
RadioToggleButton::~RadioToggleButton() = default;
void RadioToggleButton::push() {
  down = false;
  if (!parameter)
    return;
  parameter->beginEdit();
  const float current = parameter->getValue();
  const float radio = static_cast<float>(value);
  parameter->setValue(current == radio ? static_cast<float>(offValue_) : radio,
                      true);
  parameter->endEdit();
}
} // namespace Presonus::Surface
