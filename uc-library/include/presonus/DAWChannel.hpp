#pragma once

#include "presonus/uc/ClientComponent.hpp"

namespace Presonus {

// Shared portable implementation of the recovered channel lifecycle and cast.
// The original ARM object layout and remaining DAW channel behavior are outside
// this interface.
class DAWChannel : public UC::ClientComponent {
public:
  DAWChannel();
  ~DAWChannel() override;

  void *castTo(int typeId) override;
  static void operator delete(void *allocation) noexcept;

protected:
  Core::Portable::Parameter *cachedParameters_[3]{};
};

} // namespace Presonus
