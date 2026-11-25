#pragma once

#include "presonus/uc/ClientComponent.hpp"

namespace Core::Portable {
class Attributes;
}

namespace Presonus::UC {

struct BinaryEvent;
struct DebugEvent;
struct MeterEvent;
struct TimeCodeEvent;

// Portable primary-component subset. Transport and secondary interfaces are
// outside this class's recovered contract.
class ClientRootComponent : public ClientComponent {
public:
  static constexpr int kTypeID = 0x436c5274;
  static constexpr int __typeid() { return kTypeID; }
  using ClientComponent::ClientComponent;

  void *castTo(int typeId) override;
  ClientRootComponent *getRoot();
  Core::abs_time getSystemTime() const;

  void receiveEvent(const BinaryEvent &);
  void receiveEvent(const DebugEvent &);
  void receiveEvent(const TimeCodeEvent &);
  void updateLevels(const MeterEvent &);
  void subscriptionReply(const MessageAttributes *);
  bool collectAll(Core::Portable::Attributes &, ClientComponent &) const;
};

} // namespace Presonus::UC
