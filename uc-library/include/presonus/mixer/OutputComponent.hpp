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
};
} // namespace presonus::output_port
namespace Presonus::Mixer {
class OutputComponent {
public:
  explicit OutputComponent(presonus::output_port::Bindings &bindings)
      : bindings_(bindings) {}
  // Void is the explicit portable contract; original return remains unresolved.
  void soloUpdate(Presonus::Dsp::MultiParamProperty &);

private:
  presonus::output_port::Bindings &bindings_;
};
} // namespace Presonus::Mixer
