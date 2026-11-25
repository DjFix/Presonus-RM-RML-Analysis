#include "presonus/dsp/SLReverbController.hpp"

#include <algorithm>
#include <iostream>
#include <new>
#include <type_traits>

namespace {
using Presonus::Dsp::Controller;
using presonus::dsp::ReverbPortState;
using Presonus::Dsp::SLReverbController;

struct Reverb final : SLReverbController {
  using SLReverbController::SLReverbController;
  float setValue(int tag, float value) override {
    setReverbValue(tag, value);
    return getValue(tag);
  }
};

static_assert(!std::is_abstract_v<SLReverbController>);

struct Target final : Core::IPropertyHandler {
  void setProperty(const Core::Property &) override {}
  void getProperty(Core::Property &) override {}
  void release() override { ++releases; }
  int releases = 0;
};

const void *receiverAddress;
const void *stateAddress;
const void *biquadAddress;
Target *watchedTarget;
unsigned receiverFrees, stateFrees, biquadFrees;
bool targetReleasedBeforeReceiver;

void observeFree(const void *address) {
  if (!address)
    return;
  if (address == receiverAddress) {
    ++receiverFrees;
    targetReleasedBeforeReceiver = watchedTarget->releases != 0;
  } else if (address == stateAddress) {
    ++stateFrees;
  } else if (address == biquadAddress) {
    ++biquadFrees;
  }
}

#ifdef SLREVERB_DELETING
[[gnu::noipa]] void destroyThroughController(Controller *value) {
  delete value;
}
#endif
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);

extern "C" void __wrap__ZdlPv(void *address) {
  observeFree(address);
  __real__ZdlPv(address);
}

extern "C" void __wrap__ZdlPvm(void *address, std::size_t size) {
  observeFree(address);
  __real__ZdlPvm(address, size);
}

namespace {
bool exercise(bool borrowed, bool hasTarget, bool ownsTarget) {
#ifndef SLREVERB_DELETING
  alignas(Reverb) unsigned char storage[sizeof(Reverb)];
#endif
  ReverbPortState external;
  external.memory.fill(std::byte{0x51});
  Target independent;
#ifdef SLREVERB_DELETING
  auto *object = borrowed ? new Reverb(external) : new Reverb(37);
#else
  auto *object =
      borrowed ? new (storage) Reverb(external) : new (storage) Reverb(37);
#endif
  auto &state = object->reverbSourceState();
  state.valueCount = [] { return 57; };
  if (object->getNumParameters() != 57 || object->setValue(3, 0.5f) != 0.5f ||
      (&state == &external) != borrowed ||
      (object->reverbBiquad() == nullptr) != borrowed)
    return false;
  if (hasTarget)
    object->setTarget(&independent);
  if (ownsTarget)
    object->makeTargetOwner();

  const auto snapshot = external.memory;
  receiverAddress = object;
  stateAddress = &state;
  biquadAddress = object->reverbBiquad();
  watchedTarget = &independent;
  receiverFrees = stateFrees = biquadFrees = 0;
  targetReleasedBeforeReceiver = false;
#ifdef SLREVERB_DELETING
  destroyThroughController(object);
  constexpr unsigned expectedReceiverFrees = 1;
#else
  object->Reverb::~Reverb();
  constexpr unsigned expectedReceiverFrees = 0;
#endif
  receiverAddress = stateAddress = biquadAddress = nullptr;
  watchedTarget = nullptr;
  const bool externallyUnchanged =
      external.memory == snapshot && (!borrowed || external.valueCount() == 57);
  const bool expectedTargetRelease = ownsTarget && hasTarget;
  std::cout << independent.releases << ' ' << receiverFrees << ' '
            << externallyUnchanged << '\n';
  return externallyUnchanged && receiverFrees == expectedReceiverFrees &&
         stateFrees == !borrowed && biquadFrees == !borrowed &&
         static_cast<bool>(independent.releases) == expectedTargetRelease &&
         targetReleasedBeforeReceiver ==
             (expectedTargetRelease && expectedReceiverFrees != 0);
}
} // namespace

int main() {
  bool borrowed, target, owner;
  while (std::cin >> borrowed >> target >> owner)
    if (!exercise(borrowed, target, owner))
      return 1;
  return std::cin.eof() ? 0 : 2;
}
