#include "presonus/mixer_dsp/Dsp.hpp"
#include "presonus/mixer_dsp/EqParameterLists.hpp"

#include <bit>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string_view>
#include <vector>

using Presonus::Dsp::EQ8Controller;

namespace {
void *receiver = nullptr;
void *bandStorage = nullptr;
std::vector<int> events;

void observeDelete(void *address) {
  if (address == receiver) {
    events.push_back(2);
    receiver = nullptr;
  }
  if (address == bandStorage) {
    events.push_back(3);
    bandStorage = nullptr;
  }
}

class Target final : public Core::IPropertyHandler {
public:
  void setProperty(const Core::Property &) override { std::abort(); }
  void getProperty(Core::Property &) override { std::abort(); }
  void release() override { events.push_back(1); }
};

class Derived final : public EQ8Controller {
public:
  explicit Derived(int id) : EQ8Controller(id) {}
};

[[gnu::noinline]] void deleteController(Presonus::Dsp::Controller *object) {
  delete object;
}

[[gnu::noinline]] void inspect(EQ8Controller &object) {
  const auto &state = object.sourceState();
  const auto *expectedList =
      &presonus::dsp::sourceList(*Presonus::Dsp::Eq8ExtParamList::instance());
  if (state.descriptorList != expectedList)
    std::abort();
  std::cout << state.constructorId << ' ' << object.portableBands().size()
            << ' ' << object.getNumParameters() << ' '
            << object.portableEnabled() << ' ' << +state.processDirty << '\n';
  for (const auto &band : object.portableBands())
    std::cout << band.type << ' '
              << std::bit_cast<std::uint32_t>(band.frequency) << ' '
              << std::bit_cast<std::uint32_t>(band.q) << ' '
              << std::bit_cast<std::uint32_t>(band.gain) << ' ' << +band.enabled
              << ' ' << +band.dirty << ' ' << +band.edgeSelectable << ' '
              << +band.calculator.portableState().byte48 << '\n';
  for (int i = 0; i < object.getNumParameters(); ++i) {
    const int tag = state.descriptors->at(i)->sourceState().tag;
    std::cout << tag << ' '
              << std::bit_cast<std::uint32_t>(object.getValue(tag)) << '\n';
  }
  for (int value = 0; value < 17; ++value)
    std::cout << object.getEQType(static_cast<DSP::BiquadType>(value)) << ' ';
  for (int value : {0x7fffffff, -1})
    std::cout << object.getEQType(static_cast<DSP::BiquadType>(value)) << ' ';
  for (int value = 0; value < 12; ++value)
    std::cout << object.getBiquadType(value) << ' ';
  std::cout << object.getBiquadType(0x7fffffff) << '\n';
}

void observeDestruction(bool deleting, int id) {
  Target target;
  alignas(EQ8Controller) std::byte storage[sizeof(EQ8Controller)];
  auto *object =
      deleting ? new EQ8Controller(id) : ::new (storage) EQ8Controller(id);
  receiver = object;
  bandStorage = object->portableBands().data();
  if (id) {
    object->setTarget(&target);
    if (id == -1)
      object->makeTargetOwner();
  }
  events.clear();
  if (deleting)
    deleteController(object);
  else
    object->EQ8Controller::~EQ8Controller();
  if (bandStorage != nullptr || events.empty() || events.front() != 3)
    std::abort();
  std::cout << (receiver == nullptr);
  receiver = nullptr;
  for (auto event = events.begin() + 1; event != events.end(); ++event)
    std::cout << ' ' << *event;
  std::cout << '\n';
}
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);

extern "C" void __wrap__ZdlPv(void *address) {
  observeDelete(address);
  __real__ZdlPv(address);
}
extern "C" void __wrap__ZdlPvm(void *address, std::size_t size) {
  observeDelete(address);
  __real__ZdlPvm(address, size);
}

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const std::string_view variant = argv[1];
  const int id = std::atoi(argv[2]);
  events.reserve(3);
  if (id == 8 && (variant == "C1" || variant == "C2"))
    Presonus::Dsp::Eq8ExtParamList::instance();
  if (variant == "C1") {
    EQ8Controller object(id);
    inspect(object);
  } else if (variant == "C2") {
    Derived object(id);
    inspect(object);
  } else if (variant == "D0" || variant == "D1") {
    observeDestruction(variant == "D0", id);
  } else {
    return 2;
  }
}
