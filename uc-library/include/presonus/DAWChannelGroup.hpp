#pragma once

#include "presonus/uc/ClientComponent.hpp"

namespace Presonus {

// Partial portable lifetime and type-cast model. Native vtable slots and
// member offsets are not inferred from the host class layout.
class DAWChannelGroup : public UC::ClientComponent {
public:
  DAWChannelGroup();
  ~DAWChannelGroup() override;
  void *castTo(int typeId) override;
  // These operations require an initialized, borrowed parameter cache.
  int getUsedCount() const;
  void resetUsedCount();

  // The original deleting destructor calls unsized global delete.
  static void operator delete(void *receiver) noexcept;

protected:
  Core::Portable::Parameter *cachedParameter_;
};

} // namespace Presonus
