#include "presonus/uc/network_manager_services.hpp"

namespace Presonus::UC {
int NetworkManager::setPortNumber(unsigned short first, unsigned short second,
                                  int flags) {
  if (state_.startedCount != 0)
    return 1002;
  const bool primary = (static_cast<unsigned>(flags) & 1U) != 0;
  if (primary && (first == 0 || second == 0))
    return 101;
  state_.primaryPortFlag = primary;
  state_.secondaryPortFlag =
      primary && ((static_cast<unsigned>(flags) & 2U) != 0);
  state_.firstPort = first;
  state_.secondPort = second;
  return 0;
}

int NetworkManager::setNetworkPriority(int priority) {
  std::uint32_t adapterInterval = 1000;
  if (priority == 0 || priority == 1) {
    state_.threadPriority = priority == 0 ? 1 : 3;
    state_.processInterval = 5;
    adapterInterval = 333;
  } else if (priority == 2) {
    state_.threadPriority = 4;
    state_.processInterval = 1;
  }
  if (state_.processThread)
    state_.processThread->setPriority(state_.threadPriority);
  state_.adapterInterval = adapterInterval;
  return 0;
}

int NetworkManager::isSendingFromExternalConnection(int identifier) {
  return state_.dispatcher.isExternalHandler(identifier);
}
} // namespace Presonus::UC
