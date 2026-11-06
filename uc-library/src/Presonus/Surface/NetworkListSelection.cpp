#include "presonus/surface/NetworkSetupComponent.hpp"
namespace Presonus::Surface {
bool NetworkSetupComponent::ListModel::isItemSelected(int index) const {
  if (!selectedItem_)
    return index == 0;
  auto *item = items.at(index);
  return item && item->getUserData() == selectedItem_;
}
void NetworkSetupComponent::ListModel::onWheelInput(
    const Core::Portable::WheelEvent &event) {
  const int count = views.count();
  for (int index = 0; index < count; ++index)
    views[index]->onWheelInput(event);
}
void NetworkSetupComponent::ListModel::selectListItem(
    int index, bool selected, Core::Portable::ListView *view, int trigger) {
  (void)trigger;
  if (!selected || index < 0 || index >= items.count())
    return;
  auto *item = items[index];
  if (!item)
    return;
  auto *identity = static_cast<UC::NetworkItem *>(item->getUserData());
  const int type = owner_->getTargetType();
  if (type == 0)
    owner_->selectMixer(identity, 3);
  else if (type == 1)
    owner_->selectDAW(identity, 3);
  view->invalidate();
}
} // namespace Presonus::Surface
