#pragma once
#include "core/portable/corecomponent.h"
#include "core/public/corevector.h"
#include <cstdint>
namespace Presonus::Mixer {
class ChannelComponent;
class GEQComponent;
} // namespace Presonus::Mixer
namespace presonus::gequi_port {
// Independent app dependency boundary. No original layout, inheritance or
// ownership is asserted. Core operations use actual CCL objects.
// Explicit independent source-port selection input, not original object layout.
struct ChannelSelection {
  const Core::ConstVector<Presonus::Mixer::ChannelComponent *> &main;
  const Core::ConstVector<Presonus::Mixer::ChannelComponent *> &aux;
  int geqCount;
};
struct Dependencies {
  virtual ~Dependencies() = default;
  virtual int geqCount() const = 0;
  virtual Presonus::Mixer::GEQComponent *geqAt(int index) const = 0;
  virtual Core::Portable::Component &
  parameters(Presonus::Mixer::GEQComponent *) = 0;
  virtual Core::Portable::Component &
  parameters(Presonus::Mixer::ChannelComponent *) = 0;
  virtual int channelKind(Presonus::Mixer::ChannelComponent *) const = 0;
  virtual std::uint32_t
  channelIndex(Presonus::Mixer::ChannelComponent *) const = 0;
  virtual Core::Portable::Parameter &
  channelLink(Presonus::Mixer::ChannelComponent *) = 0;
  virtual Presonus::Mixer::ChannelComponent *assignedChannel(int geq) = 0;
  virtual bool linked(Presonus::Mixer::GEQComponent *) const = 0;
  virtual bool linkSlave(Presonus::Mixer::GEQComponent *) const = 0;
  virtual bool linked(Presonus::Mixer::ChannelComponent *) const = 0;
  virtual void flatten(Presonus::Mixer::GEQComponent *) = 0;
  virtual Presonus::Mixer::GEQComponent *
  geqController(Core::Portable::IParamObserver *) = 0;
  virtual Presonus::Mixer::ChannelComponent *
  channelController(Core::Portable::IParamObserver *) = 0;
  virtual bool channelUpdateLink(Presonus::Mixer::ChannelComponent *) const = 0;
  virtual void updateGeqNameList() = 0;
};
} // namespace presonus::gequi_port
namespace Presonus::Panel {
// Portable source port, not ARM32 ABI layout. Unencoded returns are chosen port
// declarations and remain pending original declaration evidence.
class GeqUIComponent : public Core::Portable::Component {
public:
  class Delegate;
  // Borrowed delegate; no interface or original return declaration established.
  void setDelegate(Delegate *);
  Delegate *portableDelegate() const { return delegate_; }
  explicit GeqUIComponent(presonus::gequi_port::Dependencies &dependencies)
      : dependencies(dependencies) {}
  void updateStereoLink(Mixer::ChannelComponent *, bool);
  Mixer::ChannelComponent *getChannelAssignedToCurrentGeq();
  // Independent binding: caller retains vectors and pointed-to channel
  // lifetime.
  void
  configureChannelSelection(const presonus::gequi_port::ChannelSelection &s) {
    channelSelection = &s;
  }
  bool isChildParameter(const Core::Portable::Parameter &) const;
  bool isChannelLinked(unsigned int);
  void flattenCurrentGeq();
  void addRemoveWatchers(int, bool);
  void selectBand(int);
  void updateBandSelect();
  Mixer::GEQComponent *getGeqForChannel(Mixer::ChannelComponent *);
  void observedParamChanged(Core::Portable::Parameter *, int);
  void updateStereoField();
  void paramChanged(Core::Portable::Parameter *p, int message) override {
    observedParamChanged(p, message);
  }
  // Independent source-port configuration, not recovered methods.
  void configureSelection(int geq, int band) {
    currentGeq = geq;
    currentBand = band;
  }
  int selectedBand() const { return currentBand; }

private:
  Delegate *delegate_ = nullptr;
  Mixer::GEQComponent *geqAt(int index) const;
  presonus::gequi_port::Dependencies &dependencies;
  const presonus::gequi_port::ChannelSelection *channelSelection = nullptr;
  int currentGeq = -1;
  int currentBand = 0;
};
} // namespace Presonus::Panel
