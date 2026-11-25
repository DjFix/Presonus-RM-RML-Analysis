#pragma once
#include "presonus/uc/server_description.hpp"
#include <cstdint>

namespace Presonus::UC {
// Partial portable source model. No original layout or return declaration is
// established. The untyped borrowed pointer is an intentional source-port
// choice.
class NetworkItem {
public:
  // Native values are observed as words. Original enumerator labels and
  // underlying signedness are unresolved.
  enum Type : std::uint32_t {};

  explicit NetworkItem(Type type);
  explicit NetworkItem(void *borrowedComponent)
      : component_(borrowedComponent) {}
  ~NetworkItem();
  void *getComponent() const;
  bool isAccessAcquired() const;
  // The portable signature exposes the proven output effect.
  void getTitle(Core::CStringBuffer<128> &title) const;

  Type portableType() const { return type_; }
  ServerDescription &portableDescription() { return description_; }
  const ServerDescription &portableDescription() const { return description_; }

  // Independent source-port input for an access observation.
  void setPortableAccessObservation(std::uint32_t observation) {
    accessObservation_ = observation;
  }
  // Independent source-port identity, not the native field at byte offset
  // 0x18e or an original accessor declaration. Inputs are copied and bounded
  // to 63 characters plus a terminator. The borrowed component is unchanged.
  void setPortableIdentity(const char *text) { portableIdentity_ = text; }
  const Core::CStringBuffer<64> &portableIdentity() const {
    return portableIdentity_;
  }

private:
  Type type_{};
  ServerDescription description_;
  void *component_ = nullptr;
  std::uint32_t accessObservation_ = 0;
  Core::CStringBuffer<64> portableIdentity_;
};
} // namespace Presonus::UC
