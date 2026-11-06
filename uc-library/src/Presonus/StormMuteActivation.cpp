#include "presonus/StormMuteGroupComponent.hpp"
#include <cstdint>
namespace Presonus {
void StormMuteGroupComponent::activate(unsigned int index) const {
  MuteGroupBase *selected = state.activationError;
  if (index <= INT32_MAX &&
      index < static_cast<unsigned int>(state.groups.count())) {
    auto *entry = state.groups[static_cast<int>(index)];
    selected = entry ? &entry->implementation : nullptr;
  }
  if (!selected)
    return;
  selected->activate();
  selected->updateStatus();
}
} // namespace Presonus
