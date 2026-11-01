#pragma once

#include "core/portable/coreparams.h"

namespace Core::Portable {
class FileName;
}

namespace Presonus::Mixer {
class PermissionsComponent;

// Independent source-port boundary. These fields are not a recovered ARM
// layout. App-specific delegates must be supplied by the embedding application;
// Core parameters are provided by the pinned official CCL implementation.
struct PermissionsBindings {
  Core::Portable::Parameter *mix = nullptr;
  Core::Portable::Parameter *other = nullptr;
  const Core::CStringBuffer<64> *selectedName = nullptr;
  unsigned char restricted = 0;
  unsigned char dirty = 0;
  void *context = nullptr;
  void *ownerContext = nullptr;
  void (*getFileName)(void *, const PermissionsComponent &,
                      Core::Portable::FileName &,
                      const Core::CStringBuffer<64> &) = nullptr;
  void (*loadSelectedDevice)(void *, PermissionsComponent &) = nullptr;
  void (*devicePermissionsChanged)(void *, PermissionsComponent &) = nullptr;
};

// Portable source port with original encoded scopes/parameters. void return
// contracts are intentional source-port choices, not original declarations.
class PermissionsComponent {
public:
  explicit PermissionsComponent(PermissionsBindings &bindings)
      : bindings_(bindings) {}

  void getSelectedFileName(Core::Portable::FileName &fileName) const;
  void getMixString(Core::CStringBuffer<128> &string) const;
  void getOtherString(Core::CStringBuffer<128> &string) const;
  void auxLinkingChanged();
  void setFullPermissions(bool enabled);

private:
  PermissionsBindings &bindings_;
};
} // namespace Presonus::Mixer
