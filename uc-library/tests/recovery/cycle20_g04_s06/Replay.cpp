#include "presonus/mixer/ChannelComponent.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <tuple>

using Presonus::Mixer::ChannelComponent;
using presonus::mixer::ChannelEnvironment;
using presonus::mixer::ChannelState;

namespace {
float asFloat(std::uint32_t bits) {
  float value;
  static_assert(sizeof(value) == sizeof(bits));
  std::memcpy(&value, &bits, sizeof(value));
  return value;
}

std::uint32_t asBits(float value) {
  std::uint32_t bits;
  std::memcpy(&bits, &value, sizeof(bits));
  return bits;
}

struct InheritedChannel : ChannelComponent {
  using ChannelComponent::ChannelComponent;
};

struct OverrideChannel : ChannelComponent {
  using ChannelComponent::ChannelComponent;
  unsigned calls = 0;
  std::array<std::uint32_t, 2> arguments{};

  void setGEQFaderScaler(float scale, float offset) override {
    ++calls;
    arguments = {asBits(scale), asBits(offset)};
  }
};

[[gnu::noinline]] void callVirtually(ChannelComponent &channel, float scale,
                                     float offset) {
  channel.setGEQFaderScaler(scale, offset);
}

auto snapshot(ChannelComponent &channel) {
  const auto &state = channel.portableState();
  return std::make_tuple(&state, state.environment, state.pan, state.gain,
                         state.lastLocate, state.active, state.coefficients,
                         state.soloCoefficients, state.updates,
                         state.environment->panLaw, state.pan->getValue());
}
} // namespace

int main() {
  const Core::Portable::ParamInfo info = PARAM_FLOAT(
      33, "Pan", -1.f, 1.f, 0.25f, PARAM_DELTA, nullptr, nullptr, 0.f, 0);
  Core::Portable::NumericParam pan(info);
  ChannelEnvironment environment{};
  environment.panLaw = -0.75f;
  ChannelState channelState{};
  channelState.environment = &environment;
  channelState.pan = &pan;
  channelState.active = true;
  channelState.gain = 0.5f;
  channelState.lastLocate = -0.25f;
  channelState.coefficients = {0.25f, 0.5f, 0.75f};
  channelState.soloCoefficients = {-1.f, 1.f};
  channelState.updates = {1, 2, 3, 4, 5, 6, 7, 8};

  const ChannelComponent::SourcePortConstruction construct;
  ChannelComponent base(construct, channelState);
  InheritedChannel inherited(construct, channelState);
  OverrideChannel overriding(construct, channelState);

  unsigned route = 0;
  std::uint32_t scaleBits = 0, offsetBits = 0;
  while (std::cin >> route >> scaleBits >> offsetBits) {
    if (route > 3)
      return 1;
    const float scale = asFloat(scaleBits);
    const float offset = asFloat(offsetBits);
    const auto before = snapshot(base);
    if (route == 0)
      base.ChannelComponent::setGEQFaderScaler(scale, offset);
    else if (route == 1)
      callVirtually(base, scale, offset);
    else
      callVirtually(inherited, scale, offset);
    const bool unchanged = snapshot(base) == before;

    overriding.calls = 0;
    callVirtually(overriding, scale, offset);
    std::cout << unchanged << ' ' << (snapshot(base) == before) << ' '
              << overriding.calls << ' ' << overriding.arguments[0] << ' '
              << overriding.arguments[1] << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
