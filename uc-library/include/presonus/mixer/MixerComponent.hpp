#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/corestorage.h"
#include "core/public/corevector.h"
#include "presonus/LinkableComponent.hpp"
#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/PresetComponent.hpp"

namespace Presonus::Mixer {
class MixerComponent;
} // namespace Presonus::Mixer
namespace presonus::mixer_component_port {
struct MixerState {
  Core::Vector<Presonus::Mixer::ChannelComponent *> channels;
  Core::Vector<Presonus::LinkableComponent *> equalizers;
  bool muteEnabled{}, muteActive{}, cascadeSelected{}, cascadeDirty{};
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
  void restoreMutes(Core::Portable::Attributes &,
                    const MixerComponentBase::Filter &);
  void doMute(ChannelComponent *);
  void presetStored(const Presonus::Panel::PresetComponent &, int);
  void onCascadeChannelSelect(int, int);
  Presonus::LinkableComponent *getGeqLinkPartner(Presonus::LinkableComponent *);
  ChannelComponent *getLinkPartner(Presonus::LinkableComponent *,
                                   const Core::Vector<ChannelComponent *> &);
  void rememberMutes(Core::Portable::Attributes &,
                     const MixerComponentBase::Filter &);

private:
  presonus::mixer_component_port::MixerState &state_;
  presonus::mixer_component_port::MixerServices &services_;
};
} // namespace Presonus::Mixer
