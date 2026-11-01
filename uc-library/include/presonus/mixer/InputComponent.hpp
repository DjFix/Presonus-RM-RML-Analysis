#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/coreparams.h"
#include <array>
#include <cstdint>
#include <vector>

namespace Presonus::Dsp {
class MultiParamProperty;
class MultiParamIntProperty;
} // namespace Presonus::Dsp
namespace presonus::input_port {
// Independent portable data models. These are not recovered original layouts.
struct Entry {
  int tag;
  std::uint32_t value;
};
struct Property {
  std::uint32_t id = 0;
  int channel = 0;
  int count = 0;
  std::array<Entry, 60> entries{};
  void append(int tag, std::uint32_t value);
};
struct Subgroup {
  Core::Portable::Parameter *linked = nullptr;
  bool slave = false;
};
struct GlobalMuteCache {
  Core::Portable::Component *component = nullptr;
  Core::Portable::Parameter *parameter = nullptr;
};
struct State {
  Core::Portable::Component *parameters = nullptr;
  Core::Portable::Component *globalComponent = nullptr;
  GlobalMuteCache *globalCache = nullptr;
  std::array<Core::Portable::Parameter *, 10> parametersByRole{};
  std::vector<Core::Portable::Component *> auxiliaries;
  Core::Portable::Component *auxError = nullptr;
  std::vector<Subgroup *> subgroups;
  std::array<float, 7> levels{};
  int channelType = 0;
  int channelIndex = 0;
  std::array<int, 6> changed{};
  std::array<float, 13> cachedLevels{};
  std::array<int, 4> cachedIntegers{};
};
// Required app-specific boundaries. Their implementations are not recovered
// here. Core parameters and lookups are provided by real pinned CCL source.
struct Providers {
  virtual ~Providers() = default;
  virtual Property &resolveProperty(const void *opaqueOriginal) = 0;
  virtual Core::Portable::Parameter *
  auxPrePost(Core::Portable::Component &) = 0;
  virtual void channelSectionChanged(int section) = 0;
  virtual void channelUpdates() = 0;
  virtual void meterLevel(int channel, float level) = 0;
  virtual void update(int originalSlot, Property &) = 0;
  virtual void submit(const Property &) = 0;
};
} // namespace presonus::input_port
namespace Presonus::Mixer {
// Source-port facade retaining original encoded method identities. Original
// inheritance, fields, method return declarations and ARM layout remain
// unknown.
class InputComponent {
public:
  InputComponent(presonus::input_port::State &state,
                 presonus::input_port::Providers &providers)
      : state(state), providers(providers) {}
  void assignSubsUpdate(Dsp::MultiParamProperty &);
  bool isPostFaderAux(int);
  bool isSubgroupModeAux(int);
  void assignLRUpdate(Dsp::MultiParamProperty &);
  bool isGlobalAuxMute();
  void setSectionCoeffChanged(int);
  void soloUpdate(Dsp::MultiParamProperty &);
  void linkUpdate(Dsp::MultiParamIntProperty &);
  void doUpdates();
  bool auxAssigned(int);

private:
  presonus::input_port::State &state;
  presonus::input_port::Providers &providers;
  void solo(presonus::input_port::Property &);
};
} // namespace Presonus::Mixer
