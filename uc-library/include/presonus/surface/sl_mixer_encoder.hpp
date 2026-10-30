#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/delay_timer.hpp"
#include "presonus/panel/key_input_provider.hpp"
namespace presonus::surface {
struct SLMixerEncoderAccess;
}
namespace Presonus {
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
};
class GeqPageComponent {
public:
  class IObserver {
  public:
    virtual void onGeqScrollOffsetChanged() = 0;

  protected:
    ~IObserver() = default;
  };
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
  void setDigitalParams(Core::Portable::Parameter *,
                        Core::Portable::Parameter *);
  void onEncoderChanged(int) override;
  // Original overrides deliberately unsupported until their actual bodies
  // are recovered. This partial source port is abstract, original was concrete.
  const char *getName() const override = 0;
  void updateConnections() override = 0;
  void onModifiersChanged() override = 0;
  void onIdle() override = 0;
  void initialize(Core::Portable::Component *) override = 0;
  void setController(IMappingController *) override = 0;
  void updatePanEncoderConnection() override = 0;
  void onMappingParamChanged(Core::Portable::Parameter *) override = 0;
  bool handleMappingRadioGroup(Core::Portable::Parameter *) override = 0;
  void handleFootswitch(FootswitchMode, bool) override;
  bool getParamFocusInfo(FocusInfo &, Core::Portable::Parameter *) override = 0;
  void paramChanged(Core::Portable::Parameter *, int) override = 0;

protected:
  SLMixerHandler()
      : encoderTimer_(1.f) {} // Independent fixture/source ctor only.
  ~SLMixerHandler() override = default;

private:
  DelayTimer encoderTimer_;
  int savedMeterMode_ = 0;
  Core::Portable::Parameter *digitalFirst_ = nullptr;
  Core::Portable::Parameter *digitalSecond_ = nullptr;
  Core::Portable::Parameter *footswitchTarget_ = nullptr;
  Core::Vector<Core::Portable::Parameter *> footswitchParameters_;
  friend struct presonus::surface::SLMixerEncoderAccess;
};
} // namespace Surface
} // namespace Presonus
namespace presonus::surface {
struct SLMixerEncoderAccess {
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
