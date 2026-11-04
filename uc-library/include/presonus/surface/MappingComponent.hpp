#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/surface/sl_mixer_encoder.hpp"
namespace presonus::mapping {
// Independent source-port boundaries for app-specific providers. These are not
// original fields, types, virtual tables, or a replacement Core implementation.
struct Handler {
  virtual ~Handler() = default;
  virtual void selectedChanged() = 0;
  virtual void defaultMapping() = 0;
  virtual void displayAssignment() = 0;
  virtual void modifiersChanged() = 0;
  virtual void idle() = 0;
  virtual void mappingParamChanged(Core::Portable::Parameter *) = 0;
};
struct Bindings {
  virtual ~Bindings() = default;
  virtual void connect(const char *, Core::Portable::Parameter *, const char *,
                       bool) const = 0;
  virtual void color(const char *, const char *, bool) const = 0;
  virtual void disconnectMixerParams() const = 0;
  virtual void blink(const char *, const char *) const = 0;
  virtual Core::Portable::Component *
  mainScreen(Core::Portable::Component *) const = 0;
  virtual void updateDAW(bool) const = 0;
};
struct Access;
} // namespace presonus::mapping
namespace presonus::surface {
struct MappingRouteInit {};
struct MappingInputAccess;
} // namespace presonus::surface
namespace Presonus::Surface {
// Original RTTI: actual Core::Portable::Component + IMappingController.
// Deliberately partial abstract source port; original was concrete. No ARM
// field offsets/lifecycle claim; unrecovered overrides are unsupported.
class MappingComponent : public Core::Portable::Component,
                         public IMappingController {
public:
  void encoderChanged(int) const override;
  void handleFootswitch(bool);
  void setGeqMode(bool);
  void setPreampsMeterMode(bool);
  enum RadioOffBehaviour : int {};
  void verifyRadioGroup(Core::Portable::Parameter *, int, int,
                        RadioOffBehaviour);
  void verifyRadioParam(Core::Portable::Parameter *);
  void paramChanged(Core::Portable::Parameter *, int) override;
  void onIdle() override;
  int getModifiers() const override;
  int getRadioValue(int, int) const override;
  int getBankScrollingOffset() const override = 0;
  Core::Portable::Parameter *getParamByTag(int) const override;
  Core::Portable::Parameter *getMainScreenParamByTag(int) const override;
  // Independent initialized source-state binding. Borrowed actual CCL object,
  // not a callback or a claim of original ARM field layout.
  void bindMainScreenParameters(Core::Portable::Component *screen) {
    mainScreenParameters_ = screen;
  }
  bool isDisplayEncoderLocked() const override = 0;
  bool areFadersLockedToMainMix() const override;
  void onSelectedChannelChanged() override;
  void selectedChannelUpdated() override = 0;
  void setRadioGroup(int, int, int, bool) override;
  void onDeviceDisconnected() override;
  void connectControl(int, const char *, const char *);
  void connectControls();
  void setDefaultMapping();
  void updateDisplayEncoderAssignment();
  void onFootswitchModeChanged(int);

protected:
  explicit MappingComponent(presonus::surface::MappingRouteInit)
      : Core::Portable::Component("portable mapping input routes") {}
  ~MappingComponent() override = default;

private:
  Core::Portable::Component *mainScreenParameters_ = nullptr;
  MixerAssignmentHandler *normalFootswitchHandler_ = nullptr;
  MixerAssignmentHandler *alternateFootswitchHandler_ = nullptr;
  MixerAssignmentHandler *encoderHandler_ = nullptr;
  friend struct presonus::surface::MappingInputAccess;
  const presonus::mapping::Bindings *bindings_ = nullptr;
  presonus::mapping::Handler *selectedHandler_ = nullptr;
  presonus::mapping::Handler *displayHandler_ = nullptr;
  presonus::mapping::Handler *secondaryHandler_ = nullptr;
  presonus::mapping::Handler *dawHandler_ = nullptr;
  Presonus::DelayTimer holdTimer_{1.f};
  Presonus::DelayTimer blinkTimer_{1.f};
  bool blinkState_ = false;
  bool fadersLockedToMainMix_ = false;
  friend struct presonus::mapping::Access;
};
} // namespace Presonus::Surface
namespace presonus::surface {
struct MappingInputAccess {
  static void bind(Presonus::Surface::MappingComponent &v,
                   Presonus::MixerAssignmentHandler *normal,
                   Presonus::MixerAssignmentHandler *alternate,
                   Presonus::MixerAssignmentHandler *encoder) {
    v.normalFootswitchHandler_ = normal;
    v.alternateFootswitchHandler_ = alternate;
    v.encoderHandler_ = encoder;
  }
};
} // namespace presonus::surface

namespace presonus::mapping {
struct Access {
  static void bind(Presonus::Surface::MappingComponent &v, const Bindings &b,
                   Handler *selected, Handler *display, Handler *secondary,
                   Handler *daw) {
    v.bindings_ = &b;
    v.selectedHandler_ = selected;
    v.displayHandler_ = display;
    v.secondaryHandler_ = secondary;
    v.dawHandler_ = daw;
  }
  static bool &fadersLockedToMainMix(Presonus::Surface::MappingComponent &v) {
    return v.fadersLockedToMainMix_;
  }
  static Presonus::DelayTimer &hold(Presonus::Surface::MappingComponent &v) {
    return v.holdTimer_;
  }
  static Presonus::DelayTimer &blink(Presonus::Surface::MappingComponent &v) {
    return v.blinkTimer_;
  }
  static bool &blinkState(Presonus::Surface::MappingComponent &v) {
    return v.blinkState_;
  }
};
} // namespace presonus::mapping
