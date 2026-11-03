#pragma once
#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/mixer/InputComponent.hpp"
#include <array>
#include <functional>
namespace presonus::output_port {
// Independent binding model, following the existing opaque property adapter.
// No original OutputComponent layout or inheritance is asserted.
struct Bindings {
  presonus::mixer::ChannelState &channel;
  std::array<float, 2> cachedSolo{};
  std::function<presonus::input_port::Property &(
      Presonus::Dsp::MultiParamProperty &)>
      resolveProperty;
  // Independent state for native writes at 0x85, 0x17c and 0x190.
  // These do not assert original fields or offsets in this source port.
  bool updatePending{};
  int outputCoeffChanged{}, sectionOneCoeffChanged{};
  // Required application boundaries: the original always calls Channel first.
  // Existing users of soloUpdate do not require these additional bindings.
  std::function<void(Core::Portable::Parameter *, int)> channelParamChanged;
  std::function<void(int)> channelSectionCoeffChanged;
};
} // namespace presonus::output_port
namespace Presonus::Mixer {
class OutputComponent {
public:
  explicit OutputComponent(presonus::output_port::Bindings &bindings)
      : bindings_(bindings) {}
  // Void is the explicit portable contract; original return remains unresolved.
  void soloUpdate(Presonus::Dsp::MultiParamProperty &);
  void paramChanged(Core::Portable::Parameter *, int);
  void setSectionCoeffChanged(int);

private:
  presonus::output_port::Bindings &bindings_;
};
} // namespace Presonus::Mixer
