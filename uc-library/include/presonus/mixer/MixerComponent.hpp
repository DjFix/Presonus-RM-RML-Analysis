#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/corestorage.h"
#include "core/public/corevector.h"
#include "presonus/LinkableComponent.hpp"
#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/mixer/MixerComponentBaseDelegate.hpp"
#include "presonus/panel/PresetComponent.hpp"

namespace Presonus::Mixer {
class MixerComponent;
class GEQComponent;
class NetworkSetupComponent;
} // namespace Presonus::Mixer
namespace presonus::uc {
class ClientTypedOrigins;
}
namespace presonus::mixer_component_port {
struct MixerState {
  Core::Vector<Presonus::Mixer::ChannelComponent *> channels;
  Core::Vector<Presonus::LinkableComponent *> equalizers;
  bool muteEnabled{}, muteActive{}, cascadeSelected{}, cascadeDirty{};
  // Explicit identity bridge from partial real GEQ provider to its canonical
  // Linkable source port. equalizers remains the sole ordered collection.
  struct GEQLinkIdentity {
    Presonus::Mixer::GEQComponent *equalizer{};
    Presonus::LinkableComponent *linkable{};
  };
  Core::Vector<GEQLinkIdentity> geqLinkIdentities;
  // Actual CCL-owned snapshot for native receiver+0x498. Application state
  // outlives this borrowed Mixer facade; no original object-layout claim.
  Core::Portable::Attributes panicMutes{
      Core::Portable::AttributeAllocator::getDefault()};
  // Real typed source-port result of the original optional RTTI lookup.
  Presonus::Mixer::NetworkSetupComponent *stageboxNetwork{};
  presonus::uc::ClientTypedOrigins *stageboxOrigins{};
  struct ChannelLinkIdentity {
    Presonus::Mixer::ChannelComponent *channel{};
    Presonus::LinkableComponent *linkable{};
    Presonus::linkable_port::State *state{};
    int kind{};
  };
  Core::Vector<ChannelLinkIdentity> channelLinks;
  Presonus::Mixer::ChannelComponent *selectedChannel{};
  bool selectionGuard{};
  // Explicit application observer boundary, not a reconstructed original class.
  struct SelectionObserver {
    virtual ~SelectionObserver() = default;
    virtual void selectionChanged() = 0;
  };
  // Compatibility-only selection callbacks from the older partial port.
  // A bound actual Delegate collection below is authoritative for both calls.
  Core::Vector<SelectionObserver *> selectionObservers;
  const Core::Vector<Presonus::Mixer::MixerComponentBase::Delegate *>
      *delegates{};
  // Borrow actual owning-base collections; offsets describe evidence, not
  // original container field names or a second mirrored channel collection.
  const Core::Vector<Presonus::Mixer::ChannelComponent *> *linkKind0To3{};
  const Core::Vector<Presonus::Mixer::ChannelComponent *> *linkKind4{};
  const Core::Vector<Presonus::Mixer::ChannelComponent *> *linkKind6{};
  Presonus::Mixer::PermissionsComponent *linkPermissions{};
  // Borrow the three distinct authoritative collections observed by this
  // listener callback. Names describe required parameter tags, not native
  // field declarations or a recovered owning class layout.
  struct AVBListenerViews {
    const Core::Vector<Presonus::Mixer::ChannelComponent *>
        *parameter304Channels{};
    const Core::Vector<Presonus::Mixer::ChannelComponent *>
        *digitalInputCandidates{};
    const Core::Vector<Presonus::Mixer::ChannelComponent *>
        *parameter340Channels{};
  } avbListeners;
};
// App-specific dependencies only. Core storage, attributes and parameters use
// the actual pinned CCL provider. No default or fixture provider is production.
class MixerServices {
public:
  virtual ~MixerServices() = default;
  virtual void serverParamChanged(Presonus::Mixer::MixerComponent &,
                                  Core::Portable::Parameter *, int) = 0;
  virtual Core::Portable::Component &
  parameterComponent(Presonus::Mixer::ChannelComponent &) const = 0;
  virtual Presonus::LinkableComponent *
  linkIdentity(Presonus::Mixer::ChannelComponent *) const = 0;
  virtual const Core::Portable::IStorageFilter *storageFilter(int, bool) = 0;
  virtual void load(const Core::Portable::InputStorage &) = 0;
  virtual void save(Core::Portable::OutputStorage &) = 0;
  virtual bool
  muteExcluded(const Presonus::Mixer::ChannelComponent &) const = 0;
  virtual Core::Portable::Parameter &
  muteSource(Presonus::Mixer::ChannelComponent &) = 0;
  virtual Core::Portable::Parameter &
  muteDestination(Presonus::Mixer::ChannelComponent &) = 0;
  virtual Core::Portable::Parameter &
  selection(Presonus::Mixer::ChannelComponent &) = 0;
  virtual const char *
  presetType(const Presonus::Panel::PresetComponent &) const = 0;
  virtual void command(const char *, const char *, int) = 0;
};
} // namespace presonus::mixer_component_port
namespace Presonus::Mixer {
// Sole source-port definition. Original return declarations, inheritance,
// ownership and object layout remain unresolved; this is not ARM32 ABI.
class MixerComponent {
public:
  MixerComponent(presonus::mixer_component_port::MixerState &state,
                 presonus::mixer_component_port::MixerServices &services)
      : state_(state), services_(services) {}
  virtual ~MixerComponent() = default;
  void paramChanged(Core::Portable::Parameter *, int);
  void release();
  ChannelComponent *
  findChannelOwningParameter(const Core::Portable::Parameter &) const;
  virtual void restoreMutes(Core::Portable::Attributes &,
                            const MixerComponentBase::Filter &);
  void doMute(ChannelComponent *);
  void doLink(GEQComponent *, bool);
  void doLink(ChannelComponent *, bool);
  void panicMuteAll(bool);
  void sendStageboxSceneMsg(const char *, const char *, int);
  void doSelect(ChannelComponent *);
  void onAVBListenerChange();
  void presetStored(const Presonus::Panel::PresetComponent &, int);
  void onCascadeChannelSelect(int, int);
  Presonus::LinkableComponent *getGeqLinkPartner(Presonus::LinkableComponent *);
  ChannelComponent *getLinkPartner(Presonus::LinkableComponent *,
                                   const Core::Vector<ChannelComponent *> &);
  virtual void rememberMutes(Core::Portable::Attributes &,
                             const MixerComponentBase::Filter &);

private:
  presonus::mixer_component_port::MixerState &state_;
  presonus::mixer_component_port::MixerServices &services_;
};
} // namespace Presonus::Mixer
