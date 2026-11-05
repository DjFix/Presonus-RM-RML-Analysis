#pragma once
#include "core/public/corestringbuffer.h"

namespace Presonus::UC {
// Partial portable source model. No original layout or return declaration is
// established. The untyped borrowed pointer is an intentional source-port
// choice.
class NetworkItem {
public:
  explicit NetworkItem(void *borrowedComponent)
      : component_(borrowedComponent) {}
  void *getComponent() const;
  // Independent source-port identity, not the native field at byte offset
  // 0x18e or an original accessor declaration. Inputs are copied and bounded
  // to 63 characters plus a terminator. The borrowed component is unchanged.
  void setPortableIdentity(const char *text) { portableIdentity_ = text; }
  const Core::CStringBuffer<64> &portableIdentity() const {
    return portableIdentity_;
  }

private:
  void *component_;
  Core::CStringBuffer<64> portableIdentity_;
};
} // namespace Presonus::UC
