#include "presonus/panel/key_input_provider.hpp"
DEFINE_SINGLETON(Presonus::Panel::KeyInputProvider)
namespace Presonus::Panel {
bool KeyInputProvider::altKeyPressed() const {
  return delegate_ ? delegate_->altKeyPressed() : false;
}
} // namespace Presonus::Panel
