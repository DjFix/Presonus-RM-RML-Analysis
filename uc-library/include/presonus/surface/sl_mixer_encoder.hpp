#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/color/IColorConverter.hpp"
#include "presonus/delay_timer.hpp"
#include "presonus/panel/key_input_provider.hpp"
namespace presonus::surface {
struct SLMixerEncoderAccess;
struct PageObserverAccess;
struct SLMappingAccess;
struct SLMappingState;
} // namespace presonus::surface
namespace Presonus {
class PageComponent;
// Original twelve-pure-slot interface, no virtual destructor slots. Ordinary
// return spellings are source-port choices pending independent declarations.
class IMappingController {
public:
  virtual int getModifiers() const = 0;
  virtual int getRadioValue(int, int) const = 0;
  virtual int getBankScrollingOffset() const = 0;
  virtual Core::Portable::Parameter *getParamByTag(int) const = 0;
  virtual Core::Portable::Parameter *getMainScreenParamByTag(int) const = 0;
  virtual bool isDisplayEncoderLocked() const = 0;
  virtual bool areFadersLockedToMainMix() const = 0;
  virtual void encoderChanged(int) const = 0;
  virtual void onSelectedChannelChanged() = 0;
  virtual void selectedChannelUpdated() = 0;
  virtual void setRadioGroup(int, int, int, bool) = 0;
  virtual void onDeviceDisconnected() = 0;

protected:
  ~IMappingController() = default;
};
class AssignmentHandler : public Core::Portable::TypedObject {
public:
  void *castTo(int) override;
  virtual ~AssignmentHandler() = default; // Independent portable lifetime glue.
  virtual const char *getName() const = 0;
  virtual void updateConnections() = 0;
  virtual void onModifiersChanged();
  virtual void onIdle();
  virtual void initialize(Core::Portable::Component *);
  virtual void setController(IMappingController *);

protected:
  AssignmentHandler() = default; // No original constructor credit.
  Core::Portable::Component *component_ = nullptr;
  IMappingController *controller_ = nullptr;
};
class MixerAssignmentHandler : public AssignmentHandler {
public:
  enum FootswitchMode : int {};
  struct FocusInfo; // Original nested identity only; fields not recovered.
  void *castTo(int) override;
  ~MixerAssignmentHandler() override = default;
  virtual void updatePanEncoderConnection();
  virtual void onMappingParamChanged(Core::Portable::Parameter *) = 0;
  virtual bool handleMappingRadioGroup(Core::Portable::Parameter *);
  virtual void onEncoderChanged(int);
  virtual bool canActivate() const;
  virtual void handleFootswitch(FootswitchMode, bool);
  virtual bool getParamFocusInfo(FocusInfo &, Core::Portable::Parameter *) = 0;
};
class IMixerComponentObserver {
public:
  enum ObjectChangeMessage : int {};
  struct ReplaceArgs;
  // Original defaults remain unsupported in this partial source port. Pure
  // markers are explicit portability gaps, not recovered original purity.
  virtual void onSelectionChanged() = 0;
  virtual void onObjectChanged(ObjectChangeMessage) = 0;
  virtual void onComponentReplaced(const ReplaceArgs &) = 0;

protected:
  ~IMixerComponentObserver() = default;
};
namespace Surface {
// Deliberately partial original outer scopes, containing only evidenced nested
// interfaces. No outer state, base, lifecycle, implementation or layout claim.
class EQPageComponent {
public:
  class IObserver {
  public:
    virtual void onEqEncoderModeChanged() = 0;

  protected:
    ~IObserver() = default;
  };
  // Portable composition; original fields/layout and return remain unresolved.
  void addObserver(IObserver *);
  void removeObserver(IObserver *);
  int getEqEncoderMode() const;

private:
  Core::Portable::ParamList encoderParameters_;
  Core::Vector<IObserver *> observers_;
  friend struct presonus::surface::PageObserverAccess;
};
class GeqPageComponent {
public:
  int getMaxListOffset();
  class IObserver {
  public:
    virtual void onGeqScrollOffsetChanged() = 0;

  protected:
    ~IObserver() = default;
  };
  // Portable composition; original fields/layout and return remain unresolved.
  void addObserver(IObserver *);
  void removeObserver(IObserver *);

private:
  Core::Vector<IObserver *> observers_;
  int listOffset_ = 0;
  friend struct presonus::surface::PageObserverAccess;
};
class SLMixerHandler : public MixerAssignmentHandler,
                       public IMixerComponentObserver,
                       public EQPageComponent::IObserver,
                       public GeqPageComponent::IObserver,
                       public Core::Portable::ParamObserverBase,
                       public Panel::IKeyInputDelegate {
public:
  Core::Portable::Parameter *getMappingParameter(int) const;
  bool altKeyPressed() const override;
  int getMeterMode() const;
  bool isGeqMode() const;
  void setDigitalParams(Core::Portable::Parameter *,
                        Core::Portable::Parameter *);
  void onEncoderChanged(int) override;
  // Original overrides deliberately unsupported until their actual bodies
  // are recovered. This partial source port is abstract, original was concrete.
  const char *getName() const override;
  int getGeqScrollOffset() const;
  int getCurrentMix() const;
  int getEqEncoderMode() const;
  int getSelectedBank() const;
  Core::Portable::Component *getSelectedGeq() const;
  struct StripAssignData {
    int bankOffset = 0;
    Core::Vector<Core::Portable::Component *> lists;
    int mix = 33;
    bool inputs = false;
  };
  bool getStripAssignData(StripAssignData &) const;
  void updateSelectedMix(const StripAssignData &);
  void getChannelPanAndLinkParams(Core::Portable::Component &,
                                  Core::Portable::Parameter **,
                                  Core::Portable::Parameter **);
  bool showAutoGroups() const;
  bool showPeakHold() const;
  bool isValidGroup(Core::Portable::Component *) const;
  void updateConnections() override = 0;
  void onModifiersChanged() override;
  void onIdle() override;
  void initialize(Core::Portable::Component *) override = 0;
  void setController(IMappingController *) override = 0;
  void updatePanEncoderConnection() override = 0;
  void onMappingParamChanged(Core::Portable::Parameter *) override;
  bool handleMappingRadioGroup(Core::Portable::Parameter *) override;
  void handleFootswitch(FootswitchMode, bool) override;
  bool getParamFocusInfo(FocusInfo &, Core::Portable::Parameter *) override = 0;
  void paramChanged(Core::Portable::Parameter *, int) override = 0;

protected:
  SLMixerHandler()
      : encoderTimer_(1.f) {} // Independent fixture/source ctor only.
  // Independent setup for the initialized lifecycle source port. No original
  // constructor or layout credit. The default fixture constructor borrows
  // state.
  struct OwnedLifecycle {};
  SLMixerHandler(OwnedLifecycle, EQPageComponent *, GeqPageComponent *,
                 Presonus::IColorConverter *ownedConverter);
  SLMixerHandler(const SLMixerHandler &) = delete;
  SLMixerHandler &operator=(const SLMixerHandler &) = delete;
  ~SLMixerHandler() override;

private:
  // Declaration order makes C++ destroy the real providers in native order:
  // boolean vectors, component vector, timer, then owned parameters.
  Core::Portable::ParamList lifecycleParameters_;
  DelayTimer encoderTimer_;
  Core::Vector<Core::Portable::Component *> lifecycleComponents_;
  Core::Vector<bool> lifecycleFirstFlags_;
  Core::Vector<bool> lifecycleSecondFlags_;
  bool ownedLifecycle_ = false;
  Presonus::IColorConverter *ownedColorConverter_ = nullptr;
  GeqPageComponent *lifecycleGeqPage_ = nullptr;
  int savedMeterMode_ = 0;
  Core::Portable::Parameter *digitalFirst_ = nullptr;
  Core::Portable::Parameter *digitalSecond_ = nullptr;
  Core::Portable::Parameter *footswitchTarget_ = nullptr;
  Core::Vector<Core::Portable::Parameter *> footswitchParameters_;
  EQPageComponent *eqPage_ = nullptr;
  PageComponent *geqPage_ = nullptr; // Borrowed portable composition.
  // Separate portable scroll view, associated with the existing opaque page
  // identity.
  GeqPageComponent *geqScrollPage_ = nullptr;
  PageComponent *geqScrollIdentity_ = nullptr;
  presonus::surface::SLMappingState *mappingState_ = nullptr;
  friend struct presonus::surface::SLMappingAccess;
  friend struct presonus::surface::SLMixerEncoderAccess;
};
} // namespace Surface
} // namespace Presonus
namespace presonus::surface {
struct SLMixerEncoderAccess {
  static auto &lifecycleParameters(Presonus::Surface::SLMixerHandler &v) {
    return v.lifecycleParameters_;
  }
  static auto &lifecycleComponents(Presonus::Surface::SLMixerHandler &v) {
    return v.lifecycleComponents_;
  }
  static auto &lifecycleFirstFlags(Presonus::Surface::SLMixerHandler &v) {
    return v.lifecycleFirstFlags_;
  }
  static auto &lifecycleSecondFlags(Presonus::Surface::SLMixerHandler &v) {
    return v.lifecycleSecondFlags_;
  }
  static void bindGeqPage(Presonus::Surface::SLMixerHandler &v,
                          Presonus::PageComponent *identity,
                          Presonus::Surface::GeqPageComponent *scrollView) {
    v.geqPage_ = identity;
    v.geqScrollIdentity_ = identity;
    v.geqScrollPage_ = scrollView;
  }
  static auto &geqPage(Presonus::Surface::SLMixerHandler &v) {
    // Legacy mutable access invalidates the associated scroll view. Updating
    // both views must use bindGeqPage; no inheritance/layout is presumed.
    v.geqScrollIdentity_ = nullptr;
    v.geqScrollPage_ = nullptr;
    return v.geqPage_;
  }
  static Presonus::Surface::GeqPageComponent *
  scrollView(const Presonus::Surface::SLMixerHandler &v) {
    return v.geqPage_ == v.geqScrollIdentity_ ? v.geqScrollPage_ : nullptr;
  }
  static bool hasGeqPage(const Presonus::Surface::SLMixerHandler &v) {
    return v.geqPage_ != nullptr;
  }
  static auto &digitalFirst(Presonus::Surface::SLMixerHandler &v) {
    return v.digitalFirst_;
  }
  static auto &digitalSecond(Presonus::Surface::SLMixerHandler &v) {
    return v.digitalSecond_;
  }
  static auto &footswitchTarget(Presonus::Surface::SLMixerHandler &v) {
    return v.footswitchTarget_;
  }
  static auto &footswitchParameters(Presonus::Surface::SLMixerHandler &v) {
    return v.footswitchParameters_;
  }
  static void bind(Presonus::Surface::SLMixerHandler &v,
                   Presonus::IMappingController *p) {
    v.controller_ = p;
  }
  static auto &timer(Presonus::Surface::SLMixerHandler &v) {
    return v.encoderTimer_;
  }
  static auto &savedMeterMode(Presonus::Surface::SLMixerHandler &v) {
    return v.savedMeterMode_;
  }
};
} // namespace presonus::surface

namespace presonus::surface {
// Independent source-port setup/inspection API, not recovered ELF methods.
struct PageObserverAccess {
  static auto &encoderParameters(Presonus::Surface::EQPageComponent &v) {
    return v.encoderParameters_;
  }
  static int &listOffset(Presonus::Surface::GeqPageComponent &v) {
    return v.listOffset_;
  }
  static auto &observers(Presonus::Surface::EQPageComponent &v) {
    return v.observers_;
  }
  static auto &observers(Presonus::Surface::GeqPageComponent &v) {
    return v.observers_;
  }
};
} // namespace presonus::surface
