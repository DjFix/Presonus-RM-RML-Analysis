#pragma once

#include "core/public/coretypes.h"
#include "presonus/uc/ServerComponent.hpp"

namespace Presonus::UC {

struct BinaryEvent;
struct MusicInputEvent;
struct TimeCodeEvent;

// Portable primary-component subset. Native secondary bases and lifecycle are
// outside this interface.
class ServerRootComponent : public ServerComponent {
public:
  using ServerComponent::ServerComponent;
  DECLARE_CORE_CLASS_(0x53765274, ServerRootComponent)
  void *castTo(int typeId) override;
  ServerRootComponent *getRoot();
  Core::abs_time getSystemTime() const;
  void receiveEvent(const BinaryEvent &);
  void receiveEvent(const MusicInputEvent &);
  void receiveEvent(const TimeCodeEvent &);
  void clientsChanged();
  void networkActivity();
};

} // namespace Presonus::UC
