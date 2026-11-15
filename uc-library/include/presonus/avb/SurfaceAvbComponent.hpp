#pragma once
#include "core/portable/corecomponent.h"
#include <cstdint>
namespace presonus::avb {
struct SurfaceAvbIdleMaintenanceAccess;
}
namespace Presonus::AVB {
// Intentional source-port inheritance: the original body calls Component
// cleanup. Original complete layout, secondary vtables and ARM ABI remain
// unresolved.
class SurfaceAvbComponent : public Core::Portable::Component {
public:
  ~SurfaceAvbComponent() override;
  // Source-port void declaration; original ordinary return remains pending.
  void onIdle() override;

private:
  friend struct presonus::avb::SurfaceAvbIdleMaintenanceAccess;
  static std::int64_t lastMaintenance_;
};
} // namespace Presonus::AVB

namespace presonus::avb {
// Independent fixture/source-port access, not an original public interface.
struct SurfaceAvbIdleMaintenanceAccess {
  static std::int64_t get() {
    return Presonus::AVB::SurfaceAvbComponent::lastMaintenance_;
  }
  static void set(std::int64_t value) {
    Presonus::AVB::SurfaceAvbComponent::lastMaintenance_ = value;
  }
};
} // namespace presonus::avb
