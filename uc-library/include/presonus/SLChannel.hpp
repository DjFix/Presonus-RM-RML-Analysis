#pragma once

#include "core/public/gui/corecolor.h"
#include "presonus/GRMeterMaid.hpp"
#include "presonus/delay_timer.hpp"
#include "presonus/uc/ClientComponent.hpp"

namespace Presonus {
class MixerClientComponentBase;
class MappableMixer;
enum ChannelType : int;
// Source-port inheritance and type ID: intentional CCL5 typed-object
// adaptation, not a claim about original ARM layout, private declarations or
// RTTI identity.
class SLChannelBase : public UC::ClientComponent {
public:
  DECLARE_CORE_CLASS(0x534c4342, SLChannelBase, UC::ClientComponent)
  using UC::ClientComponent::ClientComponent;
  SLChannelBase();
  virtual ~SLChannelBase();
  class ParamLinker : public Core::Portable::ParamObserverBase {
  public:
    ParamLinker(MixerClientComponentBase &, SLChannelBase &, SLChannelBase &);
    virtual ~ParamLinker();
    bool isLinked() const;
    void paramChanged(Core::Portable::Parameter *, int) override;
    SLChannelBase &neighbour() const { return neighbour_; }

  private:
    MixerClientComponentBase &mixer_;
    SLChannelBase &source_;
    SLChannelBase &neighbour_;
    Core::Vector<Core::Portable::Parameter *> observed_;
    Core::Portable::Parameter *link_ = nullptr;
  };
  virtual void init(MixerClientComponentBase &, SLChannelBase &);
  virtual void idleMeters();
  void updateMeter(int, float);
  void onIdle() override;
  void paramChanged(Core::Portable::Parameter *, int) override;
  void updateLinkedSelection(bool notifyMixer);
  bool isLinked() const;
  SLChannelBase *getLinkNeighbour() const;
  void getDefaultName(Core::CStringBuffer<128> &) const;
  // The real mixer and observers remain separate source providers. Both
  // borrowed observer pointers must outlive this channel; root means the
  // actual end of the mixer's initialized master chain.
  void bindSourcePortMixerObservers(MappableMixer &local, MappableMixer &root,
                                    MappableMixer *immediateMaster = nullptr) {
    observerMixer_ = &local;
    rootObserverMixer_ = &root;
    masterObserverMixer_ = immediateMaster;
    colorMixer_ = &local;
  }
  MeterMaid &sourcePortLevelMeter() { return levelMeter_; }
  GRMeterMaid &sourcePortGainReductionMeter(unsigned i) {
    return gainReduction_[i];
  }
  DelayTimer &sourcePortIdleTimer() { return idleTimer_; }

  virtual Core::Portable::Parameter *getSelectionParameter() const;
  // These nullable Parameter returns are intentional source-port declarations.
  // Original ARM bodies return zero without instance access. Their ordinary
  // return declarations/pointee qualifiers and original vtable layout remain
  // unresolved; matching method names do not establish ARM ABI compatibility.
  virtual Core::Portable::Parameter *getLinkParameter() const;
  virtual Core::Portable::Parameter *getColorParameter() const;
  virtual Core::Portable::Parameter *getLinkMasterParameter() const;
  virtual Core::Portable::Parameter *getLinkedSelectionParameter() const;
  // Independent borrowed input used by the portable color-index query.
  void bindColorIndexParameter(const Core::Portable::NumericParam *parameter) {
    colorIndexParameter_ = parameter;
    writableColorIndexParameter_ = nullptr;
  }
  // Separate source-port bindings preserve read-only index callers. Providers
  // are borrowed and must outlive this channel.
  void
  bindWritableColorIndexParameter(Core::Portable::NumericParam &parameter) {
    colorIndexParameter_ = &parameter;
    writableColorIndexParameter_ = &parameter;
  }
  void bindSourcePortColorMixer(const MappableMixer *mixer) {
    colorMixer_ = mixer;
  }
  void updateColorIndex();
  void updateColorFromIndex();
  int getColorIndex() const;
  Core::Color getColor() const;
  int getNumber() const;
  // Independent borrowed source binding. The mixer must outlive this channel.
  void bindSourcePortMixer(const MixerClientComponentBase *mixer) {
    sourcePortMixer_ = mixer;
  }
  ChannelType getChannelType() const;
  // The base leaves the supplied vector unchanged. The exact original return
  // declaration and vtable layout remain unresolved.
  virtual void
  getSlowLinkParams(Core::Vector<Core::Portable::Parameter *> &) const;

protected:
  void releaseSourcePortLinker();
  void setSourcePortDefaultName(const char *name) { defaultName_ = name; }
  MappableMixer *sourcePortObserverMixer() const { return observerMixer_; }
  MappableMixer *sourcePortMasterObserverMixer() const {
    return masterObserverMixer_;
  }
  MappableMixer *sourcePortRootObserverMixer() const {
    return rootObserverMixer_;
  }
  MixerClientComponentBase *sourcePortMutableMixer() const { return mixer_; }

private:
  MeterMaid levelMeter_;
  GRMeterMaid gainReduction_[4];
  Core::CString128 defaultName_{"Ch"};
  MixerClientComponentBase *mixer_ = nullptr;
  MappableMixer *observerMixer_ = nullptr;
  MappableMixer *rootObserverMixer_ = nullptr;
  MappableMixer *masterObserverMixer_ = nullptr;
  ParamLinker *linker_ = nullptr;
  DelayTimer idleTimer_{0.025f};
  const Core::Portable::NumericParam *colorIndexParameter_ = nullptr;
  const MixerClientComponentBase *sourcePortMixer_ = nullptr;
  Core::Portable::NumericParam *writableColorIndexParameter_ = nullptr;
  const MappableMixer *colorMixer_ = nullptr;
};

class SLChannel : public SLChannelBase {
public:
  SLChannel();
  ~SLChannel() override;
  void init(MixerClientComponentBase &, SLChannelBase &) override;
  void paramChanged(Core::Portable::Parameter *, int) override;
  Core::Portable::Parameter *getLinkParameter() const override;
  Core::Portable::Parameter *getLinkMasterParameter() const override;
  void
  getSlowLinkParams(Core::Vector<Core::Portable::Parameter *> &) const override;
  // Independent source-only setup; the initialized parameter is borrowed and
  // must outlive this channel. No original constructor/lifecycle credit.
  SLChannel(const char *name, Core::Portable::Parameter *selection)
      : SLChannelBase(name), selection_(selection) {}
  Core::Portable::Parameter *getSelectionParameter() const override;
  Core::Portable::Parameter *getColorParameter() const override;
  Core::Portable::Parameter *getLinkedSelectionParameter() const override;
  // Borrowed parameters must outlive use by this channel.
  void bindColorParameter(Core::Portable::Parameter *parameter) {
    color_ = parameter;
  }
  void bindLinkedSelectionParameter(Core::Portable::Parameter *parameter) {
    linkedSelection_ = parameter;
  }

private:
  Core::Portable::Parameter *selection_ = nullptr;
  Core::Portable::Parameter *color_ = nullptr;
  Core::Portable::Parameter *linkedSelection_ = nullptr;
};
} // namespace Presonus
