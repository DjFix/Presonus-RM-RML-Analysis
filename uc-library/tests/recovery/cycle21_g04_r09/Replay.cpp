#include "presonus/mixer/GEQComponent.hpp"
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string_view>

namespace {
enum Event {
  Release = 1,
  HandlerDestroyed,
  DspCleanup,
  ObjectDeleted,
  SizedDelete
};
Event events[16]{};
std::size_t count = 0;
std::uintptr_t tracked = 0;
bool live = false;

void record(Event event) {
  if (count == 16)
    std::abort();
  events[count++] = event;
}

void deallocate(void *address, Event kind) noexcept {
  if (address && reinterpret_cast<std::uintptr_t>(address) == tracked) {
    if (!live)
      std::abort();
    live = false;
    record(kind);
  }
  std::free(address);
}

class PropertyOwner final : public Core::IPropertyHandler {
public:
  ~PropertyOwner() { record(HandlerDestroyed); }
  void setProperty(const Core::Property &) override { std::abort(); }
  void getProperty(Core::Property &) override { std::abort(); }
  void release() override {
    record(Release);
    delete this;
  }
};

// Component ownership gives an observation from inside the real Dsp cleanup,
// independent of how GEQ disposes the Dsp instance.
class DspChild final : public Core::Portable::Component {
public:
  ~DspChild() override { record(DspCleanup); }
};

std::unique_ptr<Presonus::DspComponent> makeDsp() {
  auto dsp = std::make_unique<Presonus::DspComponent>("geq-dsp", nullptr);
  dsp->coreComponent().addChild(new DspChild);
  return dsp;
}

void printEvents() {
  for (std::size_t i = 0; i < count; ++i)
    std::cout << events[i] << (i + 1 == count ? '\n' : ' ');
}
} // namespace

void *operator new(std::size_t bytes) {
  if (void *p = std::malloc(bytes ? bytes : 1))
    return p;
  throw std::bad_alloc();
}
void operator delete(void *address) noexcept {
  deallocate(address, ObjectDeleted);
}
void operator delete(void *address, std::size_t) noexcept {
  deallocate(address, SizedDelete);
}

__attribute__((noinline)) void dispose(Core::Portable::Component *object) {
  delete object;
}

int main(int argc, char **argv) {
  using GEQ = Presonus::Mixer::GEQComponent;
  if (argc != 2)
    return 2;
  const std::string_view mode(argv[1]);
  if (mode == "provider-release") {
    Core::IPropertyHandler *handler = new PropertyOwner;
    handler->release();
  } else if (mode == "provider-dsp") {
    makeDsp().reset();
  } else if (mode == "present" || mode == "null") {
    Core::IPropertyHandler *handler =
        mode == "present" ? new PropertyOwner : nullptr;
    auto *geq = new GEQ(GEQ::AdoptLifecycle{}, makeDsp(), handler, "geq");
    tracked = reinterpret_cast<std::uintptr_t>(geq);
    live = true;
    dispose(geq);
    if (live)
      return 3;
  } else if (mode == "legacy") {
    GEQ geq(GEQ::SourcePortConstruction{}, "legacy");
    static const Core::Portable::ParamInfo param =
        PARAM_TOGGLE(0, "band", 0, nullptr, 0);
    geq.addParameters(&param, 1);
    auto *band = geq.getParameterByTag(0);
    band->setValue(1.f);
    geq.flatten();
    if (geq.getParameterByTag(0) != band || band->getValue() != 0.f)
      return 4;
    std::cout << "legacy-ok\n";
    return 0;
  } else {
    return 2;
  }
  printEvents();
}
