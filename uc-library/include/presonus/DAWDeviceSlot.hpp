#pragma once

#include "presonus/uc/ClientComponent.hpp"

namespace Presonus {

class DAWDeviceFolder;

// Portable implementation of behavior validated against the original ARM code.
// Object size, member offsets and vtable layout are specific to this CCL
// build. The original ARM ABI and hardware behavior are unverified.
class DAWDeviceSlot : public UC::ClientComponent {
public:
  static constexpr int kTypeID = 0x64774453;

  DAWDeviceSlot();
  ~DAWDeviceSlot() override;
  void *castTo(int typeId) override;
  void init();
  DAWDeviceFolder *getFolder() const;

private:
  Core::Portable::Parameter *editParameter = nullptr;
};

} // namespace Presonus
