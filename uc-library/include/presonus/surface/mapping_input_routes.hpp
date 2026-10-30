#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/surface/sl_mixer_encoder.hpp"
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
  void paramChanged(Core::Portable::Parameter *, int) override = 0;
  void onIdle() override = 0;
  int getModifiers() const override = 0;
  int getRadioValue(int, int) const override;
  int getBankScrollingOffset() const override = 0;
  Core::Portable::Parameter *getParamByTag(int) const override = 0;
  Core::Portable::Parameter *getMainScreenParamByTag(int) const override = 0;
  bool isDisplayEncoderLocked() const override = 0;
  bool areFadersLockedToMainMix() const override = 0;
  void onSelectedChannelChanged() override = 0;
  void selectedChannelUpdated() override = 0;
  void setRadioGroup(int, int, int, bool) override;
  void onDeviceDisconnected() override = 0;

protected:
  explicit MappingComponent(presonus::surface::MappingRouteInit)
      : Core::Portable::Component("portable mapping input routes") {}
  ~MappingComponent() override = default;

private:
  MixerAssignmentHandler *normalFootswitchHandler_ = nullptr;
  MixerAssignmentHandler *alternateFootswitchHandler_ = nullptr;
  MixerAssignmentHandler *encoderHandler_ = nullptr;
  friend struct presonus::surface::MappingInputAccess;
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
