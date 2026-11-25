#include "presonus/DAWChannel.hpp"

#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>
#include <string_view>
#include <typeinfo>

using Presonus::DAWChannel;
using namespace Core::Portable;

extern "C" {
void dawC1(DAWChannel *) asm("_ZN8Presonus10DAWChannelC1Ev");
void dawC2(DAWChannel *) asm("_ZN8Presonus10DAWChannelC2Ev");
void dawD0(DAWChannel *) asm("_ZN8Presonus10DAWChannelD0Ev");
void dawD1(DAWChannel *) asm("_ZN8Presonus10DAWChannelD1Ev");
void __real__ZdlPv(void *);
void __real__ZdlPvm(void *, std::size_t);
}

namespace {

void *trackedAllocation;
unsigned eventCount;
const char *events[3];

void require(bool valid) {
  if (!valid)
    std::abort();
}

void record(const char *event) {
  require(eventCount < 3);
  events[eventCount++] = event;
}

struct InspectChannel : DAWChannel {
  static auto caches() { return &InspectChannel::cachedParameters_; }
};

struct OwnedChild : Component {
  ~OwnedChild() override { record("child"); }
};

struct ParameterObserver : ParamObserverBase {
  void paramChanged(Parameter *parameter, int event) override {
    require(event == Parameter::kDestroyed);
    record("parameter");
    parameter->removeObserver(this);
  }
};

void construction(std::string_view variant, unsigned char prefill) {
  alignas(DAWChannel) unsigned char storage[sizeof(DAWChannel)];
  std::memset(storage, prefill, sizeof storage);
  auto *channel = reinterpret_cast<DAWChannel *>(storage);
  (variant == "C1" ? dawC1 : dawC2)(channel);
  channel = std::launder(channel);
  const Component *component = channel;
  require(std::strcmp(component->getName(), "") == 0);
  require(typeid(*component) == typeid(DAWChannel));
  require(component->getParent() == nullptr &&
          component->countChildren() == 0 && component->countParameters() == 0);
  for (const auto *value : channel->*InspectChannel::caches())
    require(value == nullptr);
  dawD1(channel);
  std::puts("constructed empty null-caches");
}

void destruction(std::string_view variant) {
  void *allocation = ::operator new(sizeof(DAWChannel));
  auto *channel = ::new (allocation) DAWChannel;
  ParameterObserver observer;
  ParamInfo info{};
  info.type = ParamInfo::kToggle;
  std::strcpy(info.name, "fixture-parameter");
  channel->addChild(new OwnedChild);
  channel->addParameters(&info, 1);
  require(channel->getChild(0)->getParent() == channel);
  auto *parameter = channel->getParameterAt(0);
  require(parameter != nullptr);
  parameter->addObserver(&observer);
  eventCount = 0;
  trackedAllocation = allocation;
  (variant == "D0" ? dawD0 : dawD1)(channel);
  require(eventCount == (variant == "D0" ? 3u : 2u));
  require(std::string_view(events[0]) == "child" &&
          std::string_view(events[1]) == "parameter");
  const char *outcome = "retained";
  if (variant == "D0") {
    require(std::string_view(events[2]) == "unsized-delete");
    outcome = events[2];
  } else {
    trackedAllocation = nullptr;
    ::operator delete(allocation);
  }
  std::printf("%s %s %s\n", events[0], events[1], outcome);
}

} // namespace

extern "C" void __wrap__ZdlPv(void *allocation) {
  if (trackedAllocation && allocation == trackedAllocation) {
    record("unsized-delete");
    trackedAllocation = nullptr;
  }
  __real__ZdlPv(allocation);
}

extern "C" void __wrap__ZdlPvm(void *allocation, std::size_t size) {
  require(!trackedAllocation || allocation != trackedAllocation);
  __real__ZdlPvm(allocation, size);
}

int main(int argc, char **argv) {
  require(argc == 3);
  const std::string_view variant = argv[1];
  const int value = static_cast<int>(std::strtol(argv[2], nullptr, 10));
  if (variant == "C1" || variant == "C2") {
    construction(variant, static_cast<unsigned char>(value));
  } else if (variant == "D0" || variant == "D1") {
    destruction(variant);
  } else {
    require(variant == "cast");
    DAWChannel channel;
    void *result = channel.castTo(value);
    require(!result || result == static_cast<void *>(&channel));
    std::puts(result ? "receiver" : "null");
  }
}
