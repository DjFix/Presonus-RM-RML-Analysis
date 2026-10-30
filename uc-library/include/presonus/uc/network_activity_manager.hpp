#pragma once
#include "core/portable/coresingleton.h"
#include "core/public/corevector.h"
#include "core/system/corethread.h"
#include <array>
namespace presonus::uc {
// Independent opaque projection. Original getActivityInfo returns app+8;
// reset modifies app+16..143, preserving the first8 projected bytes.
struct NetworkActivityProjection {
  std::array<unsigned char, 136> bytes{};
};
struct NetworkActivityPortTag {};
struct NetworkActivityPortAccess;
} // namespace presonus::uc
namespace Presonus::UC {
class ILowLevelNetworkListener;
// Original RTTI identifies this base and exactly four pure slots. Return types
// below are explicit source-port choices, not original declaration recovery.
class INetworkActivityManager {
public:
  virtual const presonus::uc::NetworkActivityProjection &
  getActivityInfo() const = 0;
  virtual void resetActivity() = 0;
  virtual void addListener(ILowLevelNetworkListener *) = 0;
  virtual void removeListener(ILowLevelNetworkListener *) = 0;

protected:
  // Original interface vtable has no destructor slots; no interface deletion.
  ~INetworkActivityManager() = default;
};
class NetworkActivityManager
    : public INetworkActivityManager,
      public Core::Portable::StaticSingleton<NetworkActivityManager> {
public:
  // Existing explicit source-port constructor: initial state/capacity are
  // explicit source-port inputs; this does not implement singleton
  // construction/instance for that explicit overload.
  NetworkActivityManager(presonus::uc::NetworkActivityPortTag,
                         const presonus::uc::NetworkActivityProjection &initial,
                         int listenerCapacity = 0);
  ~NetworkActivityManager();
  NetworkActivityManager(const NetworkActivityManager &) = delete;
  NetworkActivityManager &operator=(const NetworkActivityManager &) = delete;
  const presonus::uc::NetworkActivityProjection &
  getActivityInfo() const override;
  void resetActivity() override;
  void addListener(ILowLevelNetworkListener *) override;
  void removeListener(ILowLevelNetworkListener *) override;

private:
  // App initialization witnessed in both original BasicConnection constructors.
  // No separately emitted original default-constructor symbol is claimed.
  NetworkActivityManager();
  friend class Core::Portable::StaticSingleton<NetworkActivityManager>;
  friend struct presonus::uc::NetworkActivityPortAccess;
  presonus::uc::NetworkActivityProjection activity_;
  Core::Threads::Lock lock_;
  Core::Vector<ILowLevelNetworkListener *> listeners_;
};
} // namespace Presonus::UC
namespace presonus::uc {
struct NetworkActivityPortAccess {
  static auto &listeners(Presonus::UC::NetworkActivityManager &manager) {
    return manager.listeners_;
  }
  static auto &activity(Presonus::UC::NetworkActivityManager &manager) {
    return manager.activity_;
  }
};
} // namespace presonus::uc
