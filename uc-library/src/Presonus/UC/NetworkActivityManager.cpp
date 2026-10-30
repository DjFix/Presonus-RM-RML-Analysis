#include "presonus/uc/network_activity_manager.hpp"
#include <algorithm>
#include <type_traits>
namespace Presonus::UC {
static_assert(
    std::is_empty_v<Core::Portable::StaticSingleton<NetworkActivityManager>>);
static_assert(std::is_trivially_destructible_v<
              Core::Portable::StaticSingleton<NetworkActivityManager>>);
NetworkActivityManager::NetworkActivityManager(
    presonus::uc::NetworkActivityPortTag,
    const presonus::uc::NetworkActivityProjection &initial,
    int listenerCapacity)
    : activity_(initial), listeners_(listenerCapacity) {}
// Actual Vector member teardown precedes actual Lock teardown. The genuine
// upstream empty StaticSingleton base adds no runtime cleanup or owned state.
NetworkActivityManager::~NetworkActivityManager() = default;
const presonus::uc::NetworkActivityProjection &
NetworkActivityManager::getActivityInfo() const {
  return activity_;
}
void NetworkActivityManager::resetActivity() {
  std::fill(activity_.bytes.begin() + 8, activity_.bytes.end(), 0);
}
void NetworkActivityManager::addListener(ILowLevelNetworkListener *listener) {
  Core::Threads::ScopedLock guard(lock_);
  const auto count = listeners_.count();
  if (count >= listeners_.getCapacity() && !listeners_.resize(count + 1))
    return;
  listeners_.add(listener);
}
void NetworkActivityManager::removeListener(
    ILowLevelNetworkListener *listener) {
  Core::Threads::ScopedLock guard(lock_);
  listeners_.remove(listener);
}
} // namespace Presonus::UC
