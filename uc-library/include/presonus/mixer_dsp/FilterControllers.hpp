#pragma once
#include <cstdint>
#include <memory>

namespace Core {
struct IPropertyHandler;
}
namespace Presonus::Mixer {
class AudioComponent;
}

namespace presonus::dsp {
class FilterControllerProvider;

// These providers are allocated independently of the shared filter facades.
// The returned AudioComponent owns the controller and the handler release.
std::unique_ptr<Presonus::Mixer::AudioComponent>
makeHiPassAudioComponent(const char *, Core::IPropertyHandler *, int, int);
std::unique_ptr<Presonus::Mixer::AudioComponent>
makeLoPassAudioComponent(const char *, Core::IPropertyHandler *, int, int);
} // namespace presonus::dsp

namespace Presonus::Dsp {
class EQController;
// Independent portable state; not an original process object or ARM layout.
// Original accesses: process+4 value, +0x139 dirty, +0x13a active;
// controller+0x1c pending and +0x28 process pointer.
struct FilterControllerState {
  std::uint32_t valueBits = 0;
  std::uint8_t dirty = 0, active = 0, pending = 0;
};

// Portable filter facade with an owned EQ provider for integer construction.
// Native uses EQController inheritance. The two portable setter contracts
// differ in return type, so the owned provider has an explicit bridge.
class HiPassController {
public:
  explicit HiPassController(FilterControllerState &state) : state_(state) {}
  explicit HiPassController(int controllerId);
  virtual ~HiPassController();
  float getValue(int index) const;
  // Original setter return declaration unresolved.
  void setValue(int index, float value);
  EQController *portableEQController() const;

private:
  // Copies of the existing borrowed construction retain state aliasing.
  std::shared_ptr<presonus::dsp::FilterControllerProvider> provider_;
  FilterControllerState &state_;
};

// Portable filter facade with an owned EQ provider for integer construction.
// Native uses EQController inheritance. The two portable setter contracts
// differ in return type, so the owned provider has an explicit bridge.
class LoPassController {
public:
  explicit LoPassController(FilterControllerState &state) : state_(state) {}
  explicit LoPassController(int controllerId);
  virtual ~LoPassController();
  float getValue(int index) const;
  // Original setter return declaration unresolved.
  void setValue(int index, float value);
  EQController *portableEQController() const;

private:
  // Copies of the existing borrowed construction retain state aliasing.
  std::shared_ptr<presonus::dsp::FilterControllerProvider> provider_;
  FilterControllerState &state_;
};
} // namespace Presonus::Dsp
