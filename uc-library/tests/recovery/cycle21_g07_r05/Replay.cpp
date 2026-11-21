#include "presonus/dsp/Controller.hpp"
#include "presonus/mixer/AudioComponent.hpp"
#include "presonus/mixer/LimiterComponent.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>

using Outer = Presonus::Mixer::LimiterComponent;
using Presonus::Dsp::Controller;
using Presonus::Mixer::AudioComponent;

namespace {
const void *outerObject;
const void *audioObject;
bool outerReleased;
bool audioReleased;

class Property final : public Core::IPropertyHandler {
public:
  void setProperty(const Core::Property &) override {}
  void getProperty(Core::Property &) override {}
  void release() override { std::puts("property release"); }
};

class TracedController final : public Controller {
public:
  TracedController() : Controller(presonus::dsp::ControllerSourceTag{}) {}
  float getValue(int) const override { std::abort(); }
  float setValue(int, float) override { std::abort(); }
  void doUpdates() override { std::abort(); }
  void release() override {
    std::puts("controller release");
    Controller::release();
  }
};

void recordFree(const void *pointer) {
  if (pointer == outerObject) {
    outerReleased = true;
    std::puts("operator delete");
  }
  if (pointer == audioObject)
    audioReleased = true;
}
} // namespace

extern "C" void __real__ZdlPv(void *ptr);
extern "C" void __real__ZdlPvm(void *ptr, std::size_t size);

extern "C" void __wrap__ZdlPv(void *ptr) {
  __real__ZdlPv(ptr);
  recordFree(ptr);
}
extern "C" void __wrap__ZdlPvm(void *ptr, std::size_t size) {
  __real__ZdlPvm(ptr, size);
  recordFree(ptr);
}

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  Property property;
  const char *mode = argv[1];
  if (std::strcmp(mode, "owned") == 0) {
    auto audio = std::make_unique<AudioComponent>("audio", new TracedController,
                                                  &property, 17);
    audioObject = audio.get();
    auto *outer =
        new Outer(Outer::AdoptAudioComponent{}, std::move(audio), "outer");
    outerObject = outer;
    Core::Portable::Component *base = outer;
    delete base;
    if (!outerReleased || !audioReleased)
      return 3;
  } else if (std::strcmp(mode, "audio") == 0) {
    AudioComponent audio("audio", new TracedController, &property, 17);
    if (audioReleased || outerReleased)
      return 3;
    audioObject = &audio;
  } else if (std::strcmp(mode, "default") == 0) {
    auto *outer = new Outer(Outer::SourcePortConstruction{}, "outer");
    outerObject = outer;
    Core::Portable::Component *base = outer;
    delete base;
    if (!outerReleased || audioReleased)
      return 3;
  } else {
    return 2;
  }
  return 0;
}
