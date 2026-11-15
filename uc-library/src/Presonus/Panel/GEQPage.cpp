#include "presonus/panel/GEQPage.hpp"
#include "presonus/panel/GeqUIComponent.hpp"
namespace Presonus::Panel {
void GEQPage::recall() {
  if (component_)
    component_->flattenCurrentGeq();
}
} // namespace Presonus::Panel
