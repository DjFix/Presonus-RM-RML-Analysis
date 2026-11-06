#include "presonus/dsp/ControllerInfo.hpp"
#include "presonus/dsp/ControllerProperties.hpp"
#include <array>
#include <bit>
#include <cassert>
#include <cstring>
#include <iostream>
#include <type_traits>
using namespace Presonus::Dsp;
static_assert(std::is_base_of_v<Core::IPropertyHandler, IController>);
static_assert(std::is_base_of_v<IController, Controller>);
static_assert(!std::has_virtual_destructor_v<IController>);
class Values final : public Controller {
public:
  explicit Values(const ParamDescriptorList *list, bool *destroyed = nullptr)
      : Controller(15, list), destroyed_(destroyed) {}
  ~Values() override {
    if (destroyed_)
      *destroyed_ = true;
  }
  float setValue(int tag, float value) override {
    assert(tag == 0);
    return value_ = value;
  }
  float getValue(int tag) const override {
    assert(tag == 0);
    return value_;
  }
  void doUpdates() override { ++updates; }
  unsigned updates = 0;

private:
  float value_ = 0;
  bool *destroyed_;
};
struct Sink final : Core::IPropertyHandler {
  unsigned sets = 0, releases = 0;
  void setProperty(const Core::Property &) override { ++sets; }
  void getProperty(Core::Property &) override { assert(false); }
  void release() override { ++releases; }
};
int main() {
  ParamDescriptorList list(presonus::dsp::DescriptorSourceTag{});
  auto *descriptor =
      list.addFloat(0, "Gain", "dB", "gain", 10, 20, 12, "", "", 15, 0);
  Core::LinearInterpolator provider(10, 20);
  Values controller(&list);
  IController *interface = &controller;
  Core::IPropertyHandler *propertyHandler = interface;
  assert(dynamic_cast<Controller *>(propertyHandler) == &controller);
  Sink sink;
  interface->setHandler(&sink);
  interface->setTarget(&sink);
  assert(controller.sourceState().handler == &sink);
  assert(interface->getNumParameters() == 1);
  ParamInfo info;
  interface->getParameterInfo(info, 0);
  assert(info.tag == 0 && std::strcmp(info.text0, "Gain") == 0);
  interface->setValue(0, 14);
  assert(interface->getValue(0) == 14);
  for (float v : {0.f, .25f, .5f, 1.f}) {
    assert(interface->normalizedValueToRange(0, v) ==
           provider.normalizedToRange(v));
    assert(
        interface->rangeToNormalizedValue(0, provider.normalizedToRange(v)) ==
        provider.rangeToNormalized(provider.normalizedToRange(v)));
    assert(interface->setNormalized(0, v) == provider.normalizedToRange(v));
    assert(interface->getNormalized(0) ==
           provider.rangeToNormalized(controller.getValue(0)));
  }
  char buffer[32]{};
  Presonus::StringResult result{buffer, 32};
  interface->printValue(result, 0, 12.5f);
  assert(std::strcmp(buffer, "12.50") == 0);
  float scanned = 0;
  assert(interface->scanValue(scanned, 0, "13.75") && scanned == 13.75f);
  SetupProperty setup;
  setup.rate = 48000;
  assert(interface->canSetup(setup));
  propertyHandler->setProperty(setup);
  assert(controller.sourceState().processRateBits ==
         std::bit_cast<unsigned>(48000.f));
  assert(interface->flushParameterChanges() == 1 && controller.updates == 1);
  ChannelProperty channel;
  channel.type = 1415672423;
  channel.channel = 37;
  channel.entries[0].band = 0;
  propertyHandler->setProperty(channel);
  assert(controller.sourceState().word04 == 37 &&
         controller.sourceState().processDirty == 1 &&
         controller.sourceState().byte1d == 0);
  struct ValueProperty : Core::Property {
    int channel = 0, tag = 0;
    float value = 16;
    ValueProperty() : Property(1348563553, sizeof(ValueProperty)) {}
  } valueProperty;
  propertyHandler->setProperty(valueProperty);
  assert(controller.getValue(0) == 16);
  controller.sendProperty(channel, true);
  assert(sink.sets == 1 && channel.channel == 37);
  controller.sendProperty(static_cast<Core::Property &>(channel));
  assert(sink.sets == 2);
  controller.setDefaultValues();
  assert(controller.getValue(0) == 12);
  assert(controller.boundValue(0, 100) == 20);
  assert(controller.canConfiguration(2, 2) && controller.canFloatPrecision(1));
  assert(!controller.usedInProcessContext());
  // Actual CCL helper routes through the inherited getProperty. The provider
  // initializes its pointer to null; the native no-effect method leaves it so.
  assert(Core::GetInterface<IController>(propertyHandler, 123) == nullptr);
  unsigned cases = 0;
  int type, size, iid, mode, seed;
  while (std::cin >> type >> size >> iid >> mode >> seed) {
    std::array<unsigned char, 32> payload;
    payload.fill(static_cast<unsigned char>(seed));
    const auto payloadBefore = payload;
    void *value = payload.data();
    Core::InterfaceProperty property(iid, mode ? &value : nullptr);
    property.type = type;
    property.size = size;
    std::array<unsigned char, sizeof property> propertyBefore;
    std::memcpy(propertyBefore.data(), &property, sizeof property);
    std::array<unsigned char, sizeof(presonus::dsp::ControllerSourceState)>
        stateBefore;
    controller.sourceState().word04 = static_cast<unsigned>(seed);
    controller.sourceState().word08 = static_cast<unsigned>(iid);
    controller.sourceState().word10 = 7;
    controller.sourceState().word14 = 9;
    controller.sourceState().processDirty = 173;
    controller.sourceState().word20 = 0xff;
    std::memcpy(stateBefore.data(), &controller.sourceState(),
                stateBefore.size());
    const auto storedValue = controller.getValue(0);
    const auto updates = controller.updates;
    const auto sets = sink.sets;
    propertyHandler->getProperty(property);
    interface->processIdle();
    assert(std::memcmp(propertyBefore.data(), &property, sizeof property) == 0);
    assert(std::memcmp(stateBefore.data(), &controller.sourceState(),
                       stateBefore.size()) == 0);
    assert(payload == payloadBefore && value == payload.data());
    assert(controller.getValue(0) == storedValue &&
           controller.updates == updates && sink.sets == sets);
    ++cases;
  }
  controller.makeTargetOwner();
  interface->setTarget(nullptr);
  assert(sink.releases == 1);
  bool destroyed = false;
  auto *instance = new Values(&list, &destroyed);
  instance->setTarget(&sink);
  instance->makeTargetOwner();
  Core::IPropertyHandler *owned = instance;
  owned->release();
  assert(destroyed && sink.releases == 2);
  assert(descriptor->sourceState().interpolator != nullptr);
  std::cout << "typed interface/provider replay: " << cases
            << " native fixture cases passed\n";
}
