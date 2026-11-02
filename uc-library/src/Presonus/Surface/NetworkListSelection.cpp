#include "presonus/surface/NetworkSetupComponent.hpp"
namespace Presonus::Surface {
bool NetworkSetupComponent::ListModel::isItemSelected(int index) const {
  if (!selectedItem_)
    return index == 0;
  auto *item = items.at(index);
  return item && item->getUserData() == selectedItem_;
}
} // namespace Presonus::Surface
