#include "presonus/panel/SystemAboutPage.hpp"
namespace Presonus::Panel {
void SystemAboutPage::store() {
  if (!storeParameter)
    return;
  storeParameter->setValue(1.f, true);
  storeParameter->resetValue(false);
}
} // namespace Presonus::Panel
