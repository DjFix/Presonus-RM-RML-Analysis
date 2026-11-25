#include "presonus/mixer_dsp/Dsp.hpp"
#include "presonus/mixer_dsp/FilterControllers.hpp"
#include "presonus/mixer_dsp/FilterParameterLists.hpp"

#include <bit>
#include <fstream>
#include <iostream>
#include <string_view>
#include <type_traits>

extern "C" void __real__ZdlPv(void *) noexcept;
extern "C" void __real__ZdlPvm(void *, std::size_t) noexcept;

using namespace Presonus::Dsp;

namespace {
struct Lifecycle {
  unsigned events = 0;
  unsigned cleanup = 0;
  unsigned deallocation = 0;
  const void *receiver = nullptr;
};

Lifecycle *trace = nullptr;

struct Target final : Core::IPropertyHandler {
  explicit Target(Lifecycle &events) : events(events) {}
  void setProperty(const Core::Property &) override {}
  void getProperty(Core::Property &) override {}
  void release() override { events.cleanup = ++events.events; }

  Lifecycle &events;
};

void observeRelease(void *pointer) {
  if (trace && pointer == trace->receiver)
    trace->deallocation = ++trace->events;
}

template <typename Filter> struct AsBase : Filter {
  explicit AsBase(int index) : Filter(index) {}
};

template <typename Filter>
bool construct(std::istream &fixture, const ParamDescriptorList &singleton) {
  int input, bands, type, enabled, dirty, active, pending, descriptors;
  unsigned word;
  if (!(fixture >> input >> bands >> type >> word >> enabled >> dirty >>
        active >> pending >> descriptors))
    return false;

  Filter receiver(input);
  auto *provider = receiver.portableEQController();
  if (!provider || provider->getNumBands() != bands || bands != 1)
    return false;
  const auto &band = provider->portableBands().front();
  return provider->sourceState().constructorId == input &&
         provider->sourceState().descriptorList == &singleton &&
         provider->getNumParameters() == descriptors && band.type == type &&
         provider->portableEnabled() == static_cast<bool>(enabled) &&
         std::bit_cast<unsigned>(receiver.getValue(0)) == word &&
         std::bit_cast<unsigned>(band.frequency) == word &&
         band.dirty == dirty && band.enabled == active &&
         provider->sourceState().processDirty == pending;
}

template <typename Filter> void attach(Filter &receiver, Target &target) {
  auto *provider = receiver.portableEQController();
  provider->setTarget(&target);
  provider->makeTargetOwner();
}

template <typename Filter> bool destroy(std::istream &fixture, bool deleting) {
  unsigned expectedCleanup, expectedFree;
  if (!(fixture >> expectedCleanup >> expectedFree))
    return false;
  Lifecycle events;
  Target target(events);
  trace = &events;
  if (deleting) {
    auto *receiver = new Filter(3);
    events.receiver = receiver;
    attach(*receiver, target);
    delete receiver;
  } else {
    Filter receiver(3);
    events.receiver = &receiver;
    attach(receiver, target);
  }
  trace = nullptr;
  return events.cleanup == expectedCleanup &&
         events.deallocation == (expectedFree ? expectedCleanup + 1 : 0) &&
         events.events == expectedCleanup + expectedFree;
}

template <typename Filter>
bool replay(std::istream &input, std::string_view variant,
            const ParamDescriptorList &singleton) {
  static_assert(
      std::is_same_v<decltype(std::declval<Filter &>().setValue(0, 0.f)),
                     void>);
  if (variant == "c1e")
    return construct<Filter>(input, singleton);
  if (variant == "c2e")
    return construct<AsBase<Filter>>(input, singleton);
  return destroy<Filter>(input, variant == "d0e");
}
} // namespace

extern "C" void __wrap__ZdlPv(void *pointer) noexcept {
  observeRelease(pointer);
  __real__ZdlPv(pointer);
}

extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) noexcept {
  observeRelease(pointer);
  __real__ZdlPvm(pointer, size);
}

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const std::string_view task(argv[1]);
  const auto variant = task.substr(task.rfind('_') + 1);
  if (variant != "c1e" && variant != "c2e" && variant != "d0e" &&
      variant != "d1e")
    return 2;
  std::ifstream fixture(argv[2]);
  unsigned count;
  if (!(fixture >> count) || !count)
    return 2;
  for (unsigned index = 0; index < count; ++index) {
    const bool ok =
        task.starts_with("dsp_hi")
            ? replay<HiPassController>(
                  fixture, variant,
                  presonus::dsp::sourceList(*HiPassParamList::instance()))
            : replay<LoPassController>(
                  fixture, variant,
                  presonus::dsp::sourceList(*LoPassParamList::instance()));
    if (!ok) {
      std::cerr << task << " mismatch at case " << index << '\n';
      return 1;
    }
  }
  std::cout << task << ' ' << count << " portable cases\n";
}
