#include "presonus/mixer/InputComponent.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <stdexcept>

// Opaque test token, as used by the existing ranked mixer replay.
class Presonus::Dsp::MultiParamProperty {};

namespace {
using Receiver = Presonus::Mixer::InputComponent;
using Token = Presonus::Dsp::MultiParamProperty;
using namespace presonus::input_port;

struct Boundary final : Providers {
  Property &resolveProperty(const void *) override {
    ++calls;
    return property;
  }
  Core::Portable::Parameter *auxPrePost(Core::Portable::Component &) override {
    ++calls;
    return nullptr;
  }
  void channelSectionChanged(int) override { ++calls; }
  void channelUpdates() override { ++calls; }
  void meterLevel(int, float) override { ++calls; }
  void update(int, Property &) override { ++calls; }
  void submit(const Property &) override { ++calls; }
  Property property;
  unsigned calls = 0;
};

void virtualCall(Receiver &receiver, Token &property) {
  receiver.fxLevelUpdate(property);
}

struct DispatchProbe final : Receiver {
  using Receiver::Receiver;
  void fxLevelUpdate(Token &) override { ++calls; }
  unsigned calls = 0;
};

template <typename T> auto objectBytes(const T &object) {
  std::array<unsigned char, sizeof(T)> bytes;
  std::memcpy(bytes.data(), &object, bytes.size());
  return bytes;
}

bool runCase(bool viaTable, unsigned seed) {
  State state;
  state.channelIndex = seed + 5;
  state.levels.fill((seed + 1) / 4.f);
  state.changed.fill(seed & 1);
  state.cachedLevels.fill(-0.25f);
  state.cachedIntegers.fill(-2);
  state.auxiliaryCachedLevels = {0.125f, 0.25f};
  Boundary providers;
  providers.property.id = 0x12345678;
  providers.property.channel = seed;
  providers.property.append(45, 0x87654321);
  Token token{};
  DispatchProbe probe{state, providers};
  probe.Receiver::fxLevelUpdate(token);
  if (probe.calls != 0)
    throw std::runtime_error("qualified call selected override");
  virtualCall(probe, token);
  if (probe.calls != 1)
    throw std::runtime_error("virtual call bypassed override");

  Receiver input{state, providers};
  const auto inputBefore = objectBytes(input);
  const auto stateBefore = objectBytes(state);
  const auto tokenBefore = objectBytes(token);
  const auto propertyBefore = objectBytes(providers.property);
  const auto auxLevels = state.auxiliaryCachedLevels;
  if (viaTable)
    virtualCall(input, token);
  else
    input.Receiver::fxLevelUpdate(token);
  return objectBytes(input) == inputBefore &&
         objectBytes(state) == stateBefore &&
         objectBytes(token) == tokenBefore &&
         objectBytes(providers.property) == propertyBefore &&
         state.auxiliaryCachedLevels == auxLevels && providers.calls == 0;
}
} // namespace

int main() {
  unsigned route, seed;
  while (std::cin >> route >> seed) {
    if (route > 1 || seed > 3)
      return 2;
    std::cout << runCase(route != 0, seed) << '\n';
  }
  return std::cin.eof() ? 0 : 2;
}
