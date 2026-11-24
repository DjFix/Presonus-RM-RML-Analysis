#include "presonus/panel/SystemAboutPage.hpp"
#include <utility>

namespace Presonus::Panel {
SystemAboutPage::SystemAboutPage(Page::Elements elements,
                                 Core::Portable::NumericParam *parameter)
    : Page(std::move(elements)), storeParameter(parameter) {}

SystemAboutPage::~SystemAboutPage() = default;

void SystemAboutPage::store() {
  if (!storeParameter)
    return;
  storeParameter->setValue(1.f, true);
  storeParameter->resetValue(false);
}
} // namespace Presonus::Panel
