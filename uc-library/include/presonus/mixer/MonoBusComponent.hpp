#pragma once

#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/mixer/SendOutputComponent.hpp"
#include <array>

namespace presonus::mono_bus_port {
// Borrowed application and CCL providers for the independent source port.
// All referenced state must outlive the binding.
struct Bindings {
  Presonus::Mixer::SendOutputComponent &sendOutput;
  presonus::send_output_port::SendState &ownSendState;
  Core::Vector<Core::Portable::Component *> &sendChannels;
  std::array<Core::Vector<presonus::send_output_port::SendState *> *, 3>
      affectedSendGroups{};
  const char *sourceName = "";
  Core::Portable::Parameter *rangeAlias = nullptr;
  int index = 0;
  bool updateChannelNames = false;
};
} // namespace presonus::mono_bus_port

namespace Presonus::Mixer {
// Partial real type relationship from native RTTI. Original intermediate
// application bases are represented by explicitly bound portable providers.
class MonoBusComponent : public ChannelComponent {
public:
  DECLARE_CORE_CLASS(0x1765ec, MonoBusComponent, ChannelComponent)
  using ChannelComponent::ChannelComponent;
  void bindMonoBus(presonus::mono_bus_port::Bindings &bindings) {
    bindings_ = &bindings;
  }
  void paramChanged(Core::Portable::Parameter *parameter, int message) override;

private:
  presonus::mono_bus_port::Bindings *bindings_ = nullptr;
};
} // namespace Presonus::Mixer
