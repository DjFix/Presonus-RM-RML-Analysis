#pragma once

#include "core/portable/coreparams.h"
#include <cstdint>
#include <functional>
namespace Presonus {
class LinkableComponent;
}
namespace Presonus::UC {
class ClientSubscription;
}

namespace Core::Portable {
class FileName;
class Component;
} // namespace Core::Portable

namespace Presonus::Mixer {
class PermissionsComponent;
class MixerComponentBase;
class ChannelComponent;

// Borrowed projection of one existing mixer mixChannels entry. The embedding
// application supplies the actual link object and numeric channel identity;
// this does not assert ChannelComponent inheritance or original ARM fields.
struct PermissionsAuxView {
  const LinkableComponent *link = nullptr;
  std::uint32_t number = 0;
};

// Independent source-port boundary. These fields are not a recovered ARM
// layout. App-specific delegates must be supplied by the embedding application;
// Core parameters are provided by the pinned official CCL implementation.
struct PermissionsBindings {
  Core::Portable::Parameter *mix = nullptr;
  Core::Portable::Parameter *other = nullptr;
  const Core::CStringBuffer<64> *selectedName = nullptr;
  Core::Portable::Component *accessCodeParameters = nullptr;
  MixerComponentBase *mixer = nullptr;
  unsigned char restricted = 0;
  unsigned char dirty = 0;
  std::int64_t deadlineMilliseconds = 0;
  const UC::ClientSubscription *selectedSnapshot = nullptr;
  // Actual CCL list parameters, borrowed through synchronous notifications.
  // Must alias mix/other for list/load calls; mixList may be null only for
  // updateMixPermissionsStrings. Correspondences: native +0x88/+0x8c.
  // No native object layout is claimed.
  Core::Portable::ListParam *mixList = nullptr;
  Core::Portable::ListParam *otherList = nullptr;
  // Projects mixer->mixChannels; no second channel collection or link flag.
  // Every nonnull channel must project a nonnull link object. Both the
  // collection and projected objects must outlive each method call.
  std::function<PermissionsAuxView(const ChannelComponent *)> auxView;
  // Native byte +0x85 controls defaults after absent/failed archive load;
  // +0x98 suppresses feedback during the load. Source-port state only.
  unsigned char defaultPermissions = 0;
  unsigned char loading = 0;
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

  void updateOtherPermissionsStrings();
  void updateMixPermissionsStrings();
  void loadSelectedDevice();
  void loadAccessCode();
  void syncMixStrings();
  void onIdle();
  // Deterministic source-port clock boundary; original native units unresolved.
  void portableIdleAt(std::int64_t scheduleMilliseconds,
                      std::int64_t comparisonMilliseconds);
  void getFileName(Core::Portable::FileName &,
                   const Core::CStringBuffer<64> &) const;
  const UC::ClientSubscription *getSelectedDevice() const;
  void saveSelectedDevice() const;
  void getSelectedFileName(Core::Portable::FileName &fileName) const;
  void getMixString(Core::CStringBuffer<128> &string) const;
  void getOtherString(Core::CStringBuffer<128> &string) const;
  void auxLinkingChanged();
  void setFullPermissions(bool enabled);
  void resetPermissionsPW();
  // Provisional source-port returns; original return spellings remain pending.
  int getAppType(const UC::ClientSubscription &) const;
  int getSelectedDeviceApp() const;
  int getSelectedDeviceType() const;
  // Requires a nonnull subscription with NUL-terminated 64-byte values.
  Core::CStringBuffer<64>
  createClientInfo(const UC::ClientSubscription *) const;
  void saveAccessCode() const;
  void getAccessCodeFileName(Core::Portable::FileName &) const;

private:
  void compareDeadlineAt(std::int64_t);
  PermissionsBindings &bindings_;
};
} // namespace Presonus::Mixer
