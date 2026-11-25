#pragma once

#include "presonus/uc/ClientComponent.hpp"

namespace Presonus::UC {

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
};

} // namespace Presonus::UC
