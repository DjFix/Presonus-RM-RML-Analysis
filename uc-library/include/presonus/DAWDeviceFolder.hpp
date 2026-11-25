#pragma once

#include "presonus/uc/ClientComponent.hpp"

namespace Presonus {

// Portable implementation of behavior validated against the original ARM code.
// Object size, member offsets and vtable layout are specific to this CCL
// build. The original ARM ABI and hardware behavior are unverified.
class DAWDeviceFolder : public UC::ClientComponent {
public:
  static constexpr int kTypeID = 0x64774446;

  DAWDeviceFolder();
  ~DAWDeviceFolder() override;
  void *castTo(int typeId) override;
  void init();
  int getUsedCount() const;

private:
  Core::Portable::Parameter *countParameter = nullptr;
};

} // namespace Presonus
