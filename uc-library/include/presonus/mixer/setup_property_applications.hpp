#pragma once
#include "presonus/noaa/setup_property.hpp"
#include "presonus/uc/firmware_update_listener.hpp"
#include "presonus/uc/network_client_factory.hpp"
namespace presonus::mixer {
struct SetupContextTag {};
inline constexpr SetupContextTag setupContextTag{};
// Required independent setup, already converted to meaningful native refs by
// the owner. The original app+0x1c/+0xb0 adjustment is NEVER applied to host
// data.
struct SetupContext {
  SetupContext(presonus::noaa::OpaqueSetupReference adjusted0c,
               presonus::noaa::OpaqueSetupReference native20)
      : alreadyAdjusted0c(adjusted0c), native20(native20) {}
  presonus::noaa::OpaqueSetupReference alreadyAdjusted0c;
  presonus::noaa::OpaqueSetupReference native20;
};
} // namespace presonus::mixer
namespace Presonus::Mixer {
// Partial original app interface/hierarchy. Functional callbacks remain pure,
// not empty success stubs. Unrelated original virtual members are not restored;
// no complete vtable/ARM layout/startup/lifecycle equivalence is claimed.
class MixerApplication : public UC::IFirmwareUpdateListener,
                         public UC::INetworkClientFactory {
public:
  // Independent C++cleanup of borrowed source-port context, NOT recovered
  // D1/D0.
  virtual ~MixerApplication() = default;
  bool isNetworkClientReady() const override = 0;
  UC::ClientRootComponent *
  createClientComponent(const UC::NetworkItem &) override = 0;
  void releaseClientComponent(UC::ClientRootComponent *) override = 0;
  virtual NOAA::NOAASetupProperty getNOAASetupProperty() const = 0;

protected:
  MixerApplication(presonus::mixer::SetupContextTag,
                   const presonus::mixer::SetupContext &context)
      : context_(context) {}
  const presonus::mixer::SetupContext &portableSetupContext() const {
    return context_;
  }

private:
  const presonus::mixer::SetupContext &context_;
};
class RackMixerApplication : public MixerApplication {
protected:
  using MixerApplication::MixerApplication;
};
class StudioliveMixerApplication : public MixerApplication {
protected:
  using MixerApplication::MixerApplication;
};
class GambitApplication : public RackMixerApplication {
public:
  GambitApplication(presonus::mixer::SetupContextTag tag,
                    const presonus::mixer::SetupContext &context)
      : RackMixerApplication(tag, context) {}
  NOAA::NOAASetupProperty getNOAASetupProperty() const override;
};
class WolverineApplication : public RackMixerApplication {
public:
  WolverineApplication(presonus::mixer::SetupContextTag tag,
                       const presonus::mixer::SetupContext &context)
      : RackMixerApplication(tag, context) {}
  NOAA::NOAASetupProperty getNOAASetupProperty() const override;
};
class BeastApplication : public StudioliveMixerApplication {
public:
  BeastApplication(presonus::mixer::SetupContextTag tag,
                   const presonus::mixer::SetupContext &context)
      : StudioliveMixerApplication(tag, context) {}
  NOAA::NOAASetupProperty getNOAASetupProperty() const override;
};
class StormApplication : public StudioliveMixerApplication {
public:
  StormApplication(presonus::mixer::SetupContextTag tag,
                   const presonus::mixer::SetupContext &context)
      : StudioliveMixerApplication(tag, context) {}
  NOAA::NOAASetupProperty getNOAASetupProperty() const override;
};
class RogueApplication : public StudioliveMixerApplication {
public:
  RogueApplication(presonus::mixer::SetupContextTag tag,
                   const presonus::mixer::SetupContext &context)
      : StudioliveMixerApplication(tag, context) {}
  NOAA::NOAASetupProperty getNOAASetupProperty() const override;
};
} // namespace Presonus::Mixer
