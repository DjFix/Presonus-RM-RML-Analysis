#include "presonus/surface/NetworkSetupComponent.hpp"
namespace Presonus::Surface {
bool NetworkSetupComponent::isSlaveItem(const UC::NetworkItem *item) const {
  if (state_.dependencies.kind(*item) != 0)
    return false;
  for (int i = 0; i < state_.mixers.count(); ++i)
    if (state_.dependencies.associatedItem(*state_.mixers[i]) == item)
      return true;
  return false;
}
} // namespace Presonus::Surface
