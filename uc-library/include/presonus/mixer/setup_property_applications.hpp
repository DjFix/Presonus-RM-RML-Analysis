#pragma once
#include "presonus/mixer/AudioSetup.hpp"
#include "presonus/noaa/setup_property.hpp"
#include "presonus/uc/firmware_update_listener.hpp"
#include "presonus/uc/network_client_factory.hpp"
#include "presonus/uc/server_registrar.hpp"
#include <array>
#include <cstdint>
#include <memory>
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
namespace Presonus::Dsp {
class OMAPTargetHandler;
}
namespace Presonus::NOAA {
class TCardUCNetHandler;
}
namespace Presonus::Panel {
class PanelRegistrar;
}
namespace Presonus::Mixer {
// Partial original app interface/hierarchy. Functional callbacks remain pure,
// not empty success stubs. Unrelated original virtual members are not restored;
// no complete vtable/ARM layout/startup/lifecycle equivalence is claimed.
class MixerApplication : public UC::IFirmwareUpdateListener,
                         public UC::INetworkClientFactory {
public:
  virtual ~MixerApplication() noexcept(false);
  MixerApplication(const MixerApplication &) = delete;
  MixerApplication &operator=(const MixerApplication &) = delete;
  // The source-port bool declaration remains provisional.
  bool isNetworkClientReady() const override;
  UC::ClientRootComponent *
  createClientComponent(const UC::NetworkItem &) override = 0;
  void releaseClientComponent(UC::ClientRootComponent *) override = 0;
  virtual NOAA::NOAASetupProperty getNOAASetupProperty() const = 0;

protected:
  MixerApplication();
  MixerApplication(presonus::mixer::SetupContextTag,
                   const presonus::mixer::SetupContext &context);
  const presonus::mixer::SetupContext &portableSetupContext() const;

  // Independent source-port state. The original declarations of the
  // remaining initialized fields and their host layout are unresolved.
  struct PortableLifecycleDefaults {
    std::array<std::uint8_t, 2> initialBytes{};
    std::array<std::uint32_t, 2> initialWords{};
    std::array<std::uint32_t, 2> setupWords{};
    std::array<std::uint32_t, 6> targetWords{0, 0, UINT32_MAX, 0, 0, 0};
  };
  const PortableLifecycleDefaults &portableLifecycleDefaults() const;
  Dsp::OMAPTargetHandler &portableOMAPTarget();
  void adoptPortableCard(std::unique_ptr<NOAA::TCardUCNetHandler> card);
  static MixerApplication *portableCurrentApplication() noexcept;
  bool consumePortableQuitRequest() noexcept;

private:
  struct LocalState;
  const presonus::mixer::SetupContext *context_ = nullptr;
  std::unique_ptr<LocalState> local_;
};
class RackMixerApplication : public MixerApplication {
public:
  // Borrowed panel registrar. It must outlive calls to onProgress.
  void bindProgressRegistrar(Panel::PanelRegistrar &registrar) {
    progressRegistrar_ = &registrar;
  }
  // Portable declaration of the existing listener override. Progress is in
  // [0, 1] and requires a previously bound live registrar.
  void onProgress(const char *, float progress) override;

protected:
  using MixerApplication::MixerApplication;

private:
  Panel::PanelRegistrar *progressRegistrar_ = nullptr;
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
  presonus::mixer::AudioSetupRecord getAudioEngineSetupProperty() const;
  void getNetworkSetup(unsigned short &, UC::ServerInfo &) const;
};
class WolverineApplication : public RackMixerApplication {
public:
  WolverineApplication(presonus::mixer::SetupContextTag tag,
                       const presonus::mixer::SetupContext &context)
      : RackMixerApplication(tag, context) {}
  NOAA::NOAASetupProperty getNOAASetupProperty() const override;
  presonus::mixer::AudioSetupRecord getAudioEngineSetupProperty() const;
  void getNetworkSetup(unsigned short &, UC::ServerInfo &) const;
};
class BeastApplication : public StudioliveMixerApplication {
public:
  BeastApplication(presonus::mixer::SetupContextTag tag,
                   const presonus::mixer::SetupContext &context)
      : StudioliveMixerApplication(tag, context) {}
  NOAA::NOAASetupProperty getNOAASetupProperty() const override;
  presonus::mixer::AudioSetupRecord getAudioEngineSetupProperty() const;
  void getNetworkSetup(unsigned short &, UC::ServerInfo &) const;
};
class StormApplication : public StudioliveMixerApplication {
public:
  StormApplication(presonus::mixer::SetupContextTag tag,
                   const presonus::mixer::SetupContext &context)
      : StudioliveMixerApplication(tag, context) {}
  NOAA::NOAASetupProperty getNOAASetupProperty() const override;
  presonus::mixer::AudioSetupRecord getAudioEngineSetupProperty() const;
  void getNetworkSetup(unsigned short &, UC::ServerInfo &) const;
};
class RogueApplication : public StudioliveMixerApplication {
public:
  RogueApplication(presonus::mixer::SetupContextTag tag,
                   const presonus::mixer::SetupContext &context)
      : StudioliveMixerApplication(tag, context) {}
  NOAA::NOAASetupProperty getNOAASetupProperty() const override;
  presonus::mixer::AudioSetupRecord getAudioEngineSetupProperty() const;
  void getNetworkSetup(unsigned short &, UC::ServerInfo &) const;
};
} // namespace Presonus::Mixer
